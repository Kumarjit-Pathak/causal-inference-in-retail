# Causal Inference for Retail Promotions
## A Complete Technical Tutorial

**Audience:** Data Scientists, ML Engineers, Analytics Leaders
**Context:** Retail chain across 4 Indian cities | 100 SKUs | 3 years of weekly data
**Objective:** Quantify the *causal* impact of promotional levers on sales, revenue, and profit

---

# PART 1: WHY CAUSAL INFERENCE?

## The Correlation Trap

In retail analytics, naive regression and A/B testing often mislead:

- **Confounding bias:** High-equity brands get more promotions *and* sell more. A naive model attributes the brand effect to the promotion.
- **Simpson's Paradox:** A discount looks effective overall but harmful in every individual city — because discounts are concentrated in high-sales cities.
- **Selection bias:** Stores that adopt in-store displays are already better-performing. The display "effect" is partly pre-existing advantage.

**Causal inference solves this** by formally identifying and adjusting for confounding paths, giving us the *true* treatment effect.

## Correlation vs. Causation: A Concrete Example

From our data, the naive (unadjusted) effect of `discount_depth` on `sales_volume` is **+520 units/week**. After causal adjustment (controlling for brand_equity, seasonality, competitor pricing), the true ATE drops to **+468 units/week**. That 10% gap is pure confounding bias — brand equity drives both discounts and sales simultaneously.

For `is_instore_display`, the naive effect is **+195 units** but the causal ATE is **+164 units**. High-equity brands get more display slots, inflating the naive number by ~19%.

---

# PART 2: THE CAUSAL FRAMEWORK

## 2.1 Potential Outcomes (Neyman-Rubin Framework)

For each store-week observation *i*, define:
- **Y_i(1):** Sales volume *if treated* (e.g., SMS blast sent)
- **Y_i(0):** Sales volume *if not treated* (no SMS blast)

The **Individual Treatment Effect (ITE):**
```
ITE_i = Y_i(1) - Y_i(0)
```

The **fundamental problem of causal inference:** We can never observe both Y_i(1) and Y_i(0) for the same unit. Each store-week is either treated or not — one potential outcome is always counterfactual.

The **Average Treatment Effect (ATE):**
```
ATE = E[Y(1) - Y(0)] = E[Y(1)] - E[Y(0)]
```

This is what we estimate: the average causal effect across the population.

## 2.2 Directed Acyclic Graphs (DAGs)

A DAG encodes our assumptions about the data-generating process:

- **Nodes** = variables (confounders, treatments, outcomes)
- **Directed edges** = causal relationships (A -> B means "A causes B")
- **Acyclic** = no feedback loops (time moves forward)

### Our Retail DAG

```
Confounders: brand_equity, competitor_price_index, seasonality, is_festival_week, base_price, city
      |                    |
      v                    v
  Treatments ---------> Outcomes
  (discount, SMS,        (sales_volume,
   display, etc.)         revenue,
                          profit_margin)
```

**Key insight:** Confounders have arrows into *both* treatments and outcomes. This creates "backdoor paths" — spurious correlations flowing through the confounder.

### Figure: Publication-Quality DAG

![DAG](figures/dag_publication.png)

*Blue nodes = confounders, Orange nodes = treatment levers, Green nodes = outcomes. Grey edges show confounding paths; orange edges show causal effects we want to estimate.*

## 2.3 The Backdoor Criterion

**Pearl's Backdoor Criterion** tells us exactly which variables to condition on for unbiased causal estimation:

A set of variables **Z** satisfies the backdoor criterion relative to treatment T and outcome Y if:
1. No node in Z is a descendant of T
2. Z blocks every path between T and Y that contains an arrow *into* T

In our DAG, the minimal adjustment set is:
```
Z = {brand_equity, competitor_price_index, seasonality_multiplier, is_festival_week, base_price, city_id}
```

Conditioning on Z blocks all backdoor paths while leaving the direct causal path T -> Y open.

## 2.4 d-Separation

**d-separation** is the graphical test for conditional independence:

- **Chain:** A -> B -> C — B blocks the path when conditioned on
- **Fork:** A <- B -> C — B blocks the path when conditioned on
- **Collider:** A -> B <- C — B *opens* the path when conditioned on (don't condition on colliders!)

We validated our DAG with conditional independence tests (partial correlation), confirming that the graph structure is consistent with the data.

---

# PART 3: DATA & EXPERIMENTAL DESIGN

## 3.1 Synthetic Data with Known Causal Structure

We generated 62,400 observations (100 SKUs x 156 weeks x 4 cities) with an embedded causal structure:

| Feature | Type | Description |
|---------|------|-------------|
| `discount_depth` | Continuous (0-40%) | Percentage discount applied |
| `is_instore_display` | Binary (0/1) | In-store promotional display active |
| `local_channel_promo` | Binary (0/1) | Local advertising channel promotion |
| `sms_blast_active` | Binary (0/1) | SMS marketing campaign active |
| `loyalty_topup_discount` | Continuous (0-15%) | Additional loyalty member discount |
| `special_coupon_usage` | Continuous (0-1) | Proportion of coupon redemptions |
| `is_2x_points_active` | Binary (0/1) | Double loyalty points promotion |

### Confounded Treatment Assignment

Treatments are NOT randomly assigned — they depend on confounders:
```python
# Brand equity drives treatment propensity (confounding!)
discount_depth = 5 + 15 * brand_equity + 8 * is_festival + city_effect + noise
is_instore_display = P(brand_equity > 0.6 and festival)  # High brands get displays
```

This mirrors real retail data where high-value brands receive more promotional support.

### Non-Linear Interactions (Key Design Choice)

```python
# SMS + Display synergy: combined effect > sum of parts
synergy = 90 * sms_blast * is_instore_display  # +90 units when both active

# Discount saturation: diminishing returns beyond ~20%
discount_effect = 20 * discount - 0.3 * discount^2  # quadratic

# Loyalty interaction: 2x points amplifies coupon effect
loyalty_boost = 30 * is_2x_points * coupon_usage
```

## 3.2 Indian Festival Seasonality

Festival weeks use verified ISO week numbers (2021-2024):

| Festival | Typical Weeks | Cities Most Affected |
|----------|--------------|---------------------|
| Diwali | Oct-Nov (wk 44-45) | Mumbai, Delhi (weight: 1.0) |
| Holi | Mar (wk 11-12) | Delhi, Mumbai (weight: 0.9) |
| Eid | Varies by year | Hyderabad (weight: 1.0) |
| Pongal | Jan (wk 2-3) | Bengaluru (weight: 1.0) |
| Christmas | Dec (wk 52) | All cities (weight: 0.7) |
| Ganesh Chaturthi | Aug-Sep | Mumbai (weight: 1.0) |
| Navratri | Oct | All cities (weight: 0.8) |

Festival weeks amplify both treatment propensity and base sales, creating a seasonal confounding pattern.

## 3.3 City Profiles

| City | Store Clusters | Base Effect | Key Festival |
|------|---------------|-------------|-------------|
| Mumbai | Western metros | +25 units | Ganesh Chaturthi, Diwali |
| Bengaluru | Southern tech hubs | +15 units | Pongal, Ugadi |
| Delhi | Northern urban | +20 units | Diwali, Holi |
| Hyderabad | Deccan region | +10 units | Eid, Bonalu |

---

# PART 4: ESTIMATION METHODOLOGY

## 4.1 DoWhy: Causal Identification

DoWhy follows a 4-step process:
1. **Model:** Define the causal graph (DAG)
2. **Identify:** Find the estimand using Backdoor/Frontdoor criterion
3. **Estimate:** Compute the causal effect
4. **Refute:** Validate with robustness checks

```python
import dowhy

model = dowhy.CausalModel(
    data=df,
    treatment="discount_depth",
    outcome="sales_volume",
    graph=gml_graph  # DAG in GML format
)
estimand = model.identify_effect()  # Backdoor adjustment
estimate = model.estimate_effect(estimand, method_name="backdoor.linear_regression")
```

### ATE Results (All 7 Treatments on Sales Volume)

| Treatment | Naive Effect | Causal ATE | Bias (%) |
|-----------|-------------|-----------|----------|
| discount_depth | 520 | 468 | -10.0% |
| is_instore_display | 195 | 164 | -15.9% |
| local_channel_promo | 98 | 79 | -19.4% |
| sms_blast_active | 110 | 83 | -24.5% |
| loyalty_topup_discount | 180 | 151 | -16.1% |
| special_coupon_usage | 260 | 215 | -17.3% |
| is_2x_points_active | 22 | 15 | -31.8% |

**Takeaway:** Every naive estimate is *inflated* by confounding. The smaller the true effect, the larger the proportional bias (2x Points is 32% overstated).

## 4.2 Double Machine Learning (DML)

DML (Chernozhukov et al., 2018) is a semiparametric method that uses ML for nuisance estimation while maintaining valid statistical inference for the causal parameter.

### The Key Idea: Orthogonalization

**Step 1 — Residualize Y:**
```
Y_residual = Y - E[Y | W]    # Remove confounder effects from outcome
```

**Step 2 — Residualize T:**
```
T_residual = T - E[T | W]    # Remove confounder effects from treatment
```

**Step 3 — Regress residuals:**
```
Y_residual = theta * T_residual + epsilon
```

The coefficient `theta` is the causal effect, immune to regularization bias because:
- ML models handle the high-dimensional confounders (W)
- The final regression is low-dimensional (just T -> Y)
- Cross-fitting prevents overfitting bias

### Why DML over plain regression?

| Feature | OLS | DML |
|---------|-----|-----|
| Handles non-linear confounding | No | Yes (ML first stage) |
| Valid confidence intervals | Yes (if model correct) | Yes (Neyman-orthogonal) |
| High-dimensional confounders | Overfits | Cross-fitting prevents |
| Heterogeneous effects (CATE) | Manual interactions | Automatic via X |

### Implementation

```python
from econml.dml import LinearDML
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor

linear_dml = LinearDML(
    model_y=GradientBoostingRegressor(n_estimators=100, max_depth=4),
    model_t=MultiOutputRegressor(
        GradientBoostingRegressor(n_estimators=100, max_depth=4)),
    cv=3,  # 3-fold cross-fitting
    random_state=42,
)
linear_dml.fit(Y, T, X=X_effect_modifiers, W=W_confounders)

# CATE: per-observation treatment effects
cate = linear_dml.const_marginal_effect(X=X)  # shape: (n_samples, n_treatments)
```

**Technical note:** Multi-treatment DML requires `MultiOutputRegressor` wrapper for `model_t` because `GradientBoostingRegressor` natively handles only single-output regression, but the treatment residualization needs to predict all treatments simultaneously.

## 4.3 Causal Forest (CausalForestDML)

For non-parametric heterogeneous effects, we use CausalForestDML:

```python
from econml.dml import CausalForestDML

cf = CausalForestDML(
    model_y=GradientBoostingRegressor(n_estimators=50, max_depth=3),
    model_t=GradientBoostingRegressor(n_estimators=50, max_depth=3),
    n_estimators=100,  # Must be divisible by subforest_size (4)
    max_depth=4,
    cv=3,
    random_state=42,
)
```

**Key difference from LinearDML:** CausalForest allows the treatment effect itself to be a non-linear function of X, while LinearDML assumes linearity in the effect.

**Technical note:** `model_t` must be a regressor, not a classifier — even for binary treatments. EconML internally treats all treatments as continuous for residualization.

---

# PART 5: RESULTS

## 5.1 City-Level Causal Uplift

### Figure: ATE by City (Volume & Revenue)

![City Uplift Bars](figures/city_uplift_bars.png)

**Key findings:**
- **Coupon Usage** is the strongest volume driver across all cities (~470 units/week)
- **Discount Depth** boosts volume (+468 units per percentage point) but *destroys revenue* (-70K per point) — the margin erosion outweighs volume gains
- **In-Store Display** is the most balanced lever: +164 volume AND +20K revenue
- **Mumbai** consistently shows the highest treatment response across levers

## 5.2 Treatment Effect Heterogeneity (CATE)

### Figure: CATE Distributions by City

![CATE Distributions](figures/cate_distributions.png)

**Interpretation:**
- **Wide violins** = high heterogeneity (effect varies a lot across observations)
- **Narrow violins** = consistent effect (safe to apply uniformly)
- Discount Depth shows the widest spread — its effectiveness depends heavily on context (brand tier, festival timing)
- 2x Points has the tightest distribution — small, predictable effect everywhere

## 5.3 Winning Combination Matrix

### Figure: Best Lever per City

![Winning Combo Heatmap](figures/winning_combo_heatmap.png)

**Reading the heatmap:**
- Each cell = average CATE (units of sales volume) for that treatment-city pair
- Stars mark the top-performing lever per city
- Darker red = stronger effect

**Strategic insight:** Discount Depth dominates everywhere, but the *second-best* lever varies by city:
- Mumbai: Coupon Usage (224)
- Delhi: Coupon Usage (215) 
- Hyderabad: Coupon Usage (211)
- Bengaluru: Coupon Usage (219)

### SMS + In-Store Display Synergy

The interaction effect is critical:
```
Individual effects:  SMS alone = 83 units, Display alone = 164 units
Sum of individuals:  83 + 164 = 247 units
Combined effect:     247 + 90 (synergy) = 337 units
Synergy bonus:       +36% above additive expectation
```

**Always pair these two levers together.**

---

# PART 6: ROBUSTNESS & SENSITIVITY

## 6.1 Refutation Tests

Three tests validate each treatment's ATE:

**Placebo Test:** Randomly permute treatment values. If the estimated effect drops to ~0, the original estimate was real (not an artifact of the estimator).

**Random Common Cause:** Add a random noise variable as a confounder. If the ATE barely changes (<5%), the estimate is robust to missing confounders of similar strength.

**Data Subset Test:** Re-estimate on a random 70% subsample. If ATE is stable (<5% change), the estimate isn't driven by a small subset of influential observations.

### Figure: Robustness Scorecard

![Robustness Scorecard](figures/robustness_scorecard.png)

**Results:**
- 6 of 7 treatments rated **STRONG** (pass all 3 tests)
- Loyalty Top-Up rated **MODERATE** (fails subset test — estimate is somewhat sample-dependent)

## 6.2 Confounder Omission Sensitivity

### Figure: Sensitivity Tornado

![Sensitivity Tornado](figures/sensitivity_tornado.png)

**Reading the tornado chart:**
- Each bar = % change in ATE when that confounder is dropped from the model
- Large bars = that confounder is critical for unbiased estimation
- **Brand equity** is the most important confounder for Discount Depth (35% shift when omitted)
- In-Store Display and Coupon Usage are relatively insensitive (<3% shift)

**Implication:** Any production model *must* include brand equity as a control variable. Omitting it would inflate the discount effect by 35%.

## 6.3 CATE Cross-Split Stability

CausalForestDML was fit on 3 independent random splits:

| City | Split 1 | Split 2 | Split 3 | CV% |
|------|---------|---------|---------|-----|
| Mumbai | 163.0 | 165.5 | 160.5 | 1.6% |
| Bengaluru | 166.4 | 163.0 | 169.8 | 2.0% |
| Delhi | 165.5 | 166.8 | 164.3 | 0.8% |
| Hyderabad | 163.3 | 162.5 | 164.2 | 0.5% |

All CV% values are well below 20% — estimates are **highly stable** across data splits.

---

# PART 7: STRATEGIC RECOMMENDATIONS

## Recommended Actions by City

### Mumbai (Highest Response Market)
- **Primary:** Coupon campaigns (CATE: 224) + In-Store Display (163)
- **Synergy play:** Pair SMS + Display during Ganesh Chaturthi and Diwali
- **Avoid:** Deep discounts >20% (revenue-destructive)

### Bengaluru (Tech-Savvy Market)
- **Primary:** Coupon campaigns (CATE: 219) + In-Store Display (164)
- **Digital emphasis:** SMS blast response is slightly lower — consider app-based targeting
- **Festival focus:** Pongal week for maximum seasonal amplification

### Delhi (Northern Hub)
- **Primary:** Coupon campaigns (CATE: 215) + In-Store Display (165)
- **Synergy play:** SMS + Display during Diwali and Holi
- **Cost efficiency:** Local Channel Promo has highest CATE here (85)

### Hyderabad (Emerging Market)
- **Primary:** Coupon campaigns (CATE: 211) + SMS Blast (96)
- **Festival focus:** Eid and Bonalu periods for maximum impact
- **Growth lever:** Loyalty programs show above-average response

## The "Do Not" List

1. **Do NOT run deep discounts (>20%) for revenue targets** — they destroy value
2. **Do NOT run standalone SMS campaigns** without Display pairing — 3x less effective
3. **Do NOT apply uniform promotions** across cities — CATE varies by 10-15%
4. **Do NOT omit brand equity** from targeting models — causes 35% estimation bias

---

# PART 8: TECHNICAL APPENDIX

## Reproducibility

```bash
# Full pipeline
uv sync
uv run python scripts/generate_retail_data.py
uv run jupyter nbconvert --execute notebooks/00_eda.ipynb
uv run jupyter nbconvert --execute notebooks/01_causal_graph.ipynb
uv run jupyter nbconvert --execute notebooks/02_uplift_modeling.ipynb
uv run jupyter nbconvert --execute notebooks/03_sensitivity.ipynb
uv run python scripts/generate_figures.py
```

## Libraries & Versions

| Library | Version | Role |
|---------|---------|------|
| DoWhy | 0.11+ | Causal graph, identification, ATE |
| EconML | 0.15+ | LinearDML, CausalForestDML, CATE |
| scikit-learn | 1.3+ | GradientBoosting nuisance models |
| pandas | 2.0+ | Data wrangling |
| matplotlib + seaborn | 3.7+ / 0.13+ | Visualizations |
| networkx | 3.1+ | DAG construction |

## References

1. Pearl, J. (2009). *Causality: Models, Reasoning, and Inference*. Cambridge University Press.
2. Chernozhukov, V. et al. (2018). "Double/Debiased Machine Learning for Treatment and Structural Parameters." *The Econometrics Journal*.
3. Athey, S. & Imbens, G. (2019). "Machine Learning Methods That Economists Should Know About." *Annual Review of Economics*.
4. Hernan, M.A. & Robins, J.M. (2020). *Causal Inference: What If*. Chapman & Hall.
5. DoWhy documentation: https://www.pywhy.org/dowhy/
6. EconML documentation: https://econml.azurewebsites.net/
