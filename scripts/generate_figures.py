"""
Generate publication-quality figures for the Causal Inference Retail POC.
Saves all figures to reports/figures/.

Figures produced:
  1. city_uplift_bars.png        – City-level ATE uplift bars (volume & revenue)
  2. cate_distributions.png      – CATE distribution violin plots by treatment × city
  3. winning_combo_heatmap.png   – Lever combination effectiveness per city
  4. sensitivity_tornado.png     – Confounder omission tornado chart
  5. dag_publication.png         – Publication-quality DAG diagram
  6. robustness_scorecard.png    – Visual robustness scorecard table
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
import networkx as nx

# ── Setup ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.3,
})

OUT = "reports/figures"
df = pd.read_csv("data/retail_data.csv")

treatments = [
    "discount_depth", "is_instore_display", "local_channel_promo",
    "sms_blast_active", "loyalty_topup_discount", "special_coupon_usage",
    "is_2x_points_active",
]
confounders = ["brand_equity", "competitor_price_index", "seasonality_multiplier",
               "is_festival_week", "base_price"]
cities = sorted(df["city_name"].unique())

pretty = {
    "discount_depth": "Discount Depth",
    "is_instore_display": "In-Store Display",
    "local_channel_promo": "Local Channel Promo",
    "sms_blast_active": "SMS Blast",
    "loyalty_topup_discount": "Loyalty Top-Up",
    "special_coupon_usage": "Coupon Usage",
    "is_2x_points_active": "2× Points",
}

print("Data loaded:", df.shape)

# ══════════════════════════════════════════════════════════════════════════════
# 1. City-level ATE uplift bars (volume & revenue)
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 1: City-level ATE uplift bars...")

ate_records = []
for city in cities:
    dfc = df[df["city_name"] == city]
    X_c = dfc[confounders + treatments]
    for outcome in ["sales_volume", "revenue"]:
        reg = LinearRegression().fit(X_c, dfc[outcome])
        for t in treatments:
            idx = X_c.columns.get_loc(t)
            ate_records.append({
                "city": city, "treatment": pretty[t],
                "outcome": outcome, "ate": reg.coef_[idx],
            })

ate_df = pd.DataFrame(ate_records)

fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
for ax, outcome, title in zip(axes, ["sales_volume", "revenue"],
                               ["Sales Volume Uplift (units/week)", "Revenue Uplift (₹/week)"]):
    sub = ate_df[ate_df["outcome"] == outcome].pivot(
        index="treatment", columns="city", values="ate")
    sub = sub.loc[sub.mean(axis=1).sort_values(ascending=True).index]
    sub.plot.barh(ax=ax, width=0.75, edgecolor="white", linewidth=0.5)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Average Treatment Effect")
    ax.set_ylabel("")
    ax.axvline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.legend(title="City", fontsize=9)

fig.suptitle("City-Level Causal Uplift by Treatment Lever", fontsize=15, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/city_uplift_bars.png")
plt.close(fig)
print("  Saved city_uplift_bars.png")

# ══════════════════════════════════════════════════════════════════════════════
# 2. CATE distribution violin plots by treatment × city
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 2: CATE distributions...")

from econml.dml import LinearDML

np.random.seed(42)
sample = df.sample(n=10000, random_state=42).copy()
T = sample[treatments].values
Y = sample["sales_volume"].values
X = sample[["city_id"]].values  # effect modifiers
W = sample[confounders].values

linear_dml = LinearDML(
    model_y=GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42),
    model_t=MultiOutputRegressor(
        GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)),
    cv=3, random_state=42,
)
linear_dml.fit(Y, T, X=X, W=W)
cme = linear_dml.const_marginal_effect(X=X)  # (10000, 7)

cate_records = []
city_map = {1: "Mumbai", 2: "Bengaluru", 3: "Delhi", 4: "Hyderabad"}
for i, t in enumerate(treatments):
    for j in range(len(sample)):
        cate_records.append({
            "treatment": pretty[t],
            "city": city_map[sample.iloc[j]["city_id"]],
            "cate": cme[j, i],
        })
cate_df = pd.DataFrame(cate_records)

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()
for i, t in enumerate(treatments):
    ax = axes[i]
    sub = cate_df[cate_df["treatment"] == pretty[t]]
    sns.violinplot(data=sub, x="city", y="cate", ax=ax, palette="Set2",
                   inner="quartile", cut=0)
    ax.set_title(pretty[t], fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("CATE" if i % 4 == 0 else "")
    ax.axhline(0, color="red", linewidth=0.8, linestyle="--", alpha=0.5)

# Remove unused subplot
axes[7].set_visible(False)
fig.suptitle("CATE Distributions by City (LinearDML)", fontsize=15, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(f"{OUT}/cate_distributions.png")
plt.close(fig)
print("  Saved cate_distributions.png")

# ══════════════════════════════════════════════════════════════════════════════
# 3. Winning combination heatmap per city
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 3: Winning combination heatmap...")

# Average CATE per treatment per city
heatmap_data = cate_df.groupby(["city", "treatment"])["cate"].mean().unstack("treatment")
# Reorder treatments by overall mean
order = heatmap_data.mean().sort_values(ascending=False).index
heatmap_data = heatmap_data[order]

fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlOrRd", linewidths=1,
            linecolor="white", ax=ax, cbar_kws={"label": "Avg CATE (sales volume)"})
ax.set_title("Winning Combination Matrix: Treatment Effectiveness by City",
             fontsize=14, fontweight="bold")
ax.set_ylabel("")
ax.set_xlabel("")

# Mark the best lever per city with a star
for i, city in enumerate(heatmap_data.index):
    best_col = heatmap_data.loc[city].idxmax()
    j = list(heatmap_data.columns).index(best_col)
    ax.text(j + 0.5, i + 0.78, "★", ha="center", va="center", fontsize=16, color="black")

fig.tight_layout()
fig.savefig(f"{OUT}/winning_combo_heatmap.png")
plt.close(fig)
print("  Saved winning_combo_heatmap.png")

# ══════════════════════════════════════════════════════════════════════════════
# 4. Sensitivity tornado chart (confounder omission)
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 4: Sensitivity tornado chart...")

# Estimate ATE with all confounders, then drop each one
sample2 = df.sample(n=10000, random_state=42)
X_full = sample2[confounders + treatments]
y_vol = sample2["sales_volume"]
reg_full = LinearRegression().fit(X_full, y_vol)

# Baseline ATEs
baseline_ate = {}
for t in treatments:
    baseline_ate[t] = reg_full.coef_[X_full.columns.get_loc(t)]

# Drop each confounder
tornado_records = []
for drop in confounders:
    kept = [c for c in confounders if c != drop]
    X_drop = sample2[kept + treatments]
    reg_drop = LinearRegression().fit(X_drop, y_vol)
    for t in treatments:
        new_ate = reg_drop.coef_[X_drop.columns.get_loc(t)]
        pct_change = 100 * (new_ate - baseline_ate[t]) / (abs(baseline_ate[t]) + 1e-9)
        tornado_records.append({
            "confounder_dropped": drop, "treatment": pretty[t], "pct_change": pct_change
        })

tornado_df = pd.DataFrame(tornado_records)

# Show tornado for the top 3 most impactful treatments
top3 = ["discount_depth", "is_instore_display", "special_coupon_usage"]
fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
for ax, t in zip(axes, top3):
    sub = tornado_df[tornado_df["treatment"] == pretty[t]].sort_values("pct_change")
    colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in sub["pct_change"]]
    ax.barh(sub["confounder_dropped"], sub["pct_change"], color=colors, edgecolor="white")
    ax.set_title(pretty[t], fontweight="bold")
    ax.set_xlabel("% Change in ATE\n(when confounder is omitted)")
    ax.axvline(0, color="grey", linewidth=0.8)

fig.suptitle("Sensitivity Tornado: Impact of Omitting Each Confounder on ATE",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(f"{OUT}/sensitivity_tornado.png")
plt.close(fig)
print("  Saved sensitivity_tornado.png")

# ══════════════════════════════════════════════════════════════════════════════
# 5. Publication-quality DAG diagram
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 5: DAG diagram...")

G = nx.DiGraph()

# Node categories
confounder_nodes = ["brand_equity", "competitor_price_idx", "seasonality",
                    "is_festival_week", "base_price", "city"]
treatment_nodes = ["discount_depth", "in_store_display", "local_channel_promo",
                   "sms_blast", "loyalty_topup", "coupon_usage", "2x_points"]
outcome_nodes = ["sales_volume", "revenue", "profit_margin"]

G.add_nodes_from(confounder_nodes + treatment_nodes + outcome_nodes)

# Confounder → treatment edges
for c in confounder_nodes:
    for t in treatment_nodes:
        G.add_edge(c, t)
# Confounder → outcome edges
for c in confounder_nodes:
    for o in outcome_nodes:
        G.add_edge(c, o)
# Treatment → outcome edges
for t in treatment_nodes:
    for o in outcome_nodes:
        G.add_edge(t, o)
# Interactions
G.add_edge("sms_blast", "in_store_display")  # synergy

fig, ax = plt.subplots(figsize=(16, 10))

# Layered layout
pos = {}
# Top row: confounders
for i, n in enumerate(confounder_nodes):
    pos[n] = (i * 2.2, 4)
# Middle row: treatments
for i, n in enumerate(treatment_nodes):
    pos[n] = (i * 1.9, 2)
# Bottom row: outcomes
for i, n in enumerate(outcome_nodes):
    pos[n] = (2 + i * 4, 0)

node_colors = []
for n in G.nodes():
    if n in confounder_nodes:
        node_colors.append("#3498db")
    elif n in treatment_nodes:
        node_colors.append("#e67e22")
    else:
        node_colors.append("#27ae60")

nx.draw_networkx_nodes(G, pos, ax=ax, node_size=2200, node_color=node_colors,
                       edgecolors="white", linewidths=2, alpha=0.9)

# Nicer labels
label_map = {n: n.replace("_", "\n") for n in G.nodes()}
nx.draw_networkx_labels(G, pos, labels=label_map, ax=ax, font_size=8,
                        font_weight="bold", font_color="white")

# Edge styles
confounder_edges = [(u, v) for u, v in G.edges() if u in confounder_nodes]
treatment_edges = [(u, v) for u, v in G.edges()
                   if u in treatment_nodes and v in outcome_nodes]
interaction_edges = [(u, v) for u, v in G.edges()
                     if u in treatment_nodes and v in treatment_nodes]

nx.draw_networkx_edges(G, pos, edgelist=confounder_edges, ax=ax,
                       edge_color="#95a5a6", alpha=0.4, arrows=True,
                       arrowsize=12, connectionstyle="arc3,rad=0.05")
nx.draw_networkx_edges(G, pos, edgelist=treatment_edges, ax=ax,
                       edge_color="#e67e22", alpha=0.7, arrows=True,
                       arrowsize=15, width=2, connectionstyle="arc3,rad=0.05")
nx.draw_networkx_edges(G, pos, edgelist=interaction_edges, ax=ax,
                       edge_color="#e74c3c", alpha=0.8, arrows=True,
                       arrowsize=15, width=2.5, style="dashed")

# Legend
legend_handles = [
    mpatches.Patch(color="#3498db", label="Confounders"),
    mpatches.Patch(color="#e67e22", label="Treatment Levers"),
    mpatches.Patch(color="#27ae60", label="Outcomes"),
]
ax.legend(handles=legend_handles, loc="upper right", fontsize=11,
          frameon=True, fancybox=True)

ax.set_title("Causal DAG: Retail Promotion Impact on Sales Outcomes",
             fontsize=15, fontweight="bold", pad=20)
ax.axis("off")
fig.tight_layout()
fig.savefig(f"{OUT}/dag_publication.png")
plt.close(fig)
print("  Saved dag_publication.png")

# ══════════════════════════════════════════════════════════════════════════════
# 6. Robustness scorecard visual
# ══════════════════════════════════════════════════════════════════════════════
print("Figure 6: Robustness scorecard...")

# Re-run the OLS-based refutation from notebook 03
np.random.seed(42)
samp = df.sample(n=10000, random_state=42)
X_all = samp[confounders + treatments]
y = samp["sales_volume"]
reg = LinearRegression().fit(X_all, y)

scorecard = []
for t in treatments:
    ate = reg.coef_[X_all.columns.get_loc(t)]

    # Placebo
    df_p = samp.copy()
    df_p[t] = np.random.permutation(df_p[t].values)
    X_p = df_p[confounders + treatments]
    reg_p = LinearRegression().fit(X_p, df_p["sales_volume"])
    placebo = reg_p.coef_[X_p.columns.get_loc(t)]
    p_pass = abs(placebo) < 0.1 * abs(ate)

    # Random common cause
    df_r = samp.copy()
    df_r["rand_cc"] = np.random.normal(0, 1, len(df_r))
    X_r = df_r[confounders + treatments + ["rand_cc"]]
    reg_r = LinearRegression().fit(X_r, df_r["sales_volume"])
    rcc_ate = reg_r.coef_[X_r.columns.get_loc(t)]
    r_pass = abs(rcc_ate - ate) / (abs(ate) + 1e-9) < 0.05

    # Subset
    sub70 = samp.sample(frac=0.7, random_state=42)
    X_s = sub70[confounders + treatments]
    reg_s = LinearRegression().fit(X_s, sub70["sales_volume"])
    sub_ate = reg_s.coef_[X_s.columns.get_loc(t)]
    s_pass = abs(sub_ate - ate) / (abs(ate) + 1e-9) < 0.05

    passes = sum([p_pass, r_pass, s_pass])
    rating = ["FRAGILE", "WEAK", "MODERATE", "STRONG"][passes]

    scorecard.append({
        "Treatment": pretty[t], "ATE": round(ate, 1),
        "Placebo": "PASS" if p_pass else "FAIL",
        "Random CC": "PASS" if r_pass else "FAIL",
        "Subset": "PASS" if s_pass else "FAIL",
        "Rating": rating,
    })

sc_df = pd.DataFrame(scorecard)

fig, ax = plt.subplots(figsize=(12, 4))
ax.axis("off")

colors_map = {"PASS": "#27ae60", "FAIL": "#e74c3c",
              "STRONG": "#27ae60", "MODERATE": "#f39c12",
              "WEAK": "#e74c3c", "FRAGILE": "#c0392b"}

table = ax.table(
    cellText=sc_df.values,
    colLabels=sc_df.columns,
    cellLoc="center",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.8)

# Color header
for j in range(len(sc_df.columns)):
    table[0, j].set_facecolor("#2c3e50")
    table[0, j].set_text_props(color="white", fontweight="bold")

# Color cells
for i in range(len(sc_df)):
    for j, col in enumerate(sc_df.columns):
        val = str(sc_df.iloc[i, j])
        if val in colors_map:
            table[i + 1, j].set_facecolor(colors_map[val])
            table[i + 1, j].set_text_props(color="white", fontweight="bold")
        # ATE column
        if col == "ATE":
            table[i + 1, j].set_text_props(fontweight="bold")

ax.set_title("Robustness Scorecard: Treatment Effect Validation",
             fontsize=14, fontweight="bold", pad=20)
fig.tight_layout()
fig.savefig(f"{OUT}/robustness_scorecard.png")
plt.close(fig)
print("  Saved robustness_scorecard.png")

print("\nAll 6 figures saved to reports/figures/")
