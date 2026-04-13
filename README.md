# Causal Inference for Retail Promotions: A Step-by-Step Tutorial

A complete, end-to-end **causal inference proof-of-concept** for a retail chain across 4 Indian cities. This project goes beyond correlation to quantify the **true causal impact** of discounts, targeting channels, and loyalty programs on sales volume, revenue, and profitability.

---

## What You Will Learn

By working through this project, you will understand:

1. **Why correlation is not causation** - and how to move from naive regression to proper causal estimation
2. **Directed Acyclic Graphs (DAGs)** - encoding domain knowledge as a causal graph, identifying confounders via the Backdoor Criterion
3. **Average Treatment Effects (ATE)** - estimating the overall impact of each promotional lever
4. **Conditional Average Treatment Effects (CATE)** - discovering *heterogeneous* effects across cities, brands, and seasons using Double Machine Learning
5. **Refutation testing** - validating that your causal estimates aren't spurious (placebo, random common cause, subset tests)
6. **Sensitivity analysis** - understanding how robust your findings are to unobserved confounders and model assumptions
7. **Translating causal estimates into business strategy** - which lever combinations work best in which city

---

## Project Structure

```
Causal inference/
|-- data/
|   |-- retail_data.csv              # 62,400-row synthetic dataset
|-- scripts/
|   |-- generate_retail_data.py      # Data generation with embedded causal structure
|   |-- generate_figures.py          # Publication-quality figure generation
|-- notebooks/
|   |-- 00_eda.ipynb                 # Exploratory Data Analysis
|   |-- 01_causal_graph.ipynb        # DAG construction & causal identification
|   |-- 02_uplift_modeling.ipynb     # ATE & CATE estimation (DoWhy + EconML)
|   |-- 03_sensitivity.ipynb         # Robustness & sensitivity analysis
|-- reports/
|   |-- strategy_recommendation.md   # Final strategy report with embedded visuals
|   |-- figures/                     # All generated charts and diagrams
|-- requirements.txt                 # Pinned Python dependencies
|-- pyproject.toml                   # UV project configuration
|-- TRACKER.md                       # Project progress tracker
|-- CLAUDE.md                        # Project specification
```

---

## Prerequisites

- **Python 3.10+**
- **UV** package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- Basic understanding of regression and probability
- Familiarity with pandas and scikit-learn

---

## Setup Instructions

### 1. Clone or download the project

```bash
cd "Causal inference"
```

### 2. Create the virtual environment and install dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Generate the synthetic dataset

```bash
uv run python scripts/generate_retail_data.py
```

This creates `data/retail_data.csv` with 62,400 rows (100 SKUs x 156 weeks x 4 cities).

### 4. Run the notebooks in order

```bash
# Option A: Open in Jupyter and run interactively
uv run jupyter notebook

# Option B: Execute from command line
uv run jupyter nbconvert --to notebook --execute notebooks/00_eda.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/01_causal_graph.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/02_uplift_modeling.ipynb
uv run jupyter nbconvert --to notebook --execute notebooks/03_sensitivity.ipynb
```

### 5. Generate publication-quality figures

```bash
uv run python scripts/generate_figures.py
```

Figures are saved to `reports/figures/`.

---

## Step-by-Step Guide

### Step 1: Data Generation (`scripts/generate_retail_data.py`)

The synthetic data generator creates a dataset with **known causal structure** — this is critical for validating that our causal methods recover the true effects. Key features:

- **Confounded treatment assignment:** Brand equity, festivals, and city characteristics drive both treatment decisions and outcomes (just like real data)
- **Non-linear interactions:** SMS + In-Store Display synergy (+90 units), discount saturation (quadratic diminishing returns)
- **Indian festival seasonality:** Diwali, Holi, Eid, Pongal, Christmas with city-specific relevance weights
- **7 treatment levers:** discount_depth, is_instore_display, local_channel_promo, sms_blast_active, loyalty_topup_discount, special_coupon_usage, is_2x_points_active

### Step 2: Exploratory Data Analysis (`notebooks/00_eda.ipynb`)

Before causal modeling, we examine the data to understand distributions, detect confounding patterns, and check for multicollinearity. Key sections:

- Outcome distributions (sales_volume, revenue, profit_margin)
- Treatment distributions by city (evidence of confounding)
- Correlation heatmap and Variance Inflation Factor (VIF)
- Seasonality time series
- Naive treatment-outcome relationships (what you'd get without causal adjustment)

### Step 3: Causal Graph (`notebooks/01_causal_graph.ipynb`)

We construct a Directed Acyclic Graph (DAG) encoding our domain knowledge about the causal relationships:

- **Confounders** (brand_equity, seasonality, city, etc.) cause both treatments and outcomes
- **Treatments** cause outcomes (the effects we want to estimate)
- **Backdoor paths** create spurious correlations that must be blocked

The notebook identifies the minimal adjustment set using the Backdoor Criterion and validates the graph structure with conditional independence tests.

### Step 4: Uplift Modeling (`notebooks/02_uplift_modeling.ipynb`)

The core analysis notebook:

- **DoWhy ATE estimation** for all 7 treatments with backdoor adjustment
- **Refutation tests** (placebo treatment, random common cause, data subset) to validate each estimate
- **LinearDML** (EconML) for multi-treatment CATE estimation — how effects vary across cities, brand tiers, and festival periods
- **CausalForestDML** for flexible, non-parametric heterogeneous effect estimation
- **Winning combination matrix** — which lever combinations work best in each city

### Step 5: Sensitivity Analysis (`notebooks/03_sensitivity.ipynb`)

Robustness checks to build confidence in the findings:

- **Confounder omission analysis:** Drop each confounder and measure ATE stability
- **Simulated unobserved confounder:** How strong would a hidden confounder need to be to invalidate results?
- **CATE cross-split stability:** Verify estimates are consistent across independent data splits
- **Robustness scorecard:** Summary rating (STRONG/MODERATE/WEAK/FRAGILE) for each treatment

### Step 6: Strategy Report (`reports/strategy_recommendation.md`)

Translates all causal findings into actionable business recommendations with embedded visualizations.

---

## Key Concepts Covered

| Concept | Where | Why It Matters |
|---------|-------|---------------|
| **DAG (Directed Acyclic Graph)** | Notebook 01 | Encodes causal assumptions; enables formal identification |
| **Backdoor Criterion** | Notebook 01 | Identifies which variables to control for unbiased estimation |
| **d-separation** | Notebook 01 | Tests whether paths in the DAG are blocked by conditioning |
| **ATE (Average Treatment Effect)** | Notebook 02 | The average causal effect of a treatment across the population |
| **CATE (Conditional Average Treatment Effect)** | Notebook 02 | How treatment effects vary across subgroups |
| **Double Machine Learning (DML)** | Notebook 02 | ML-based causal estimation that handles high-dimensional confounders |
| **Neyman-Rubin Framework** | Notebook 02 | Potential outcomes formulation of causal effects |
| **Refutation Tests** | Notebooks 02, 03 | Validation that estimates aren't artifacts of the method |
| **Sensitivity Analysis** | Notebook 03 | Robustness to unobserved confounders and model misspecification |

---

## Expected Outputs

After running the full pipeline, you should see:

| Output | Location | Description |
|--------|----------|-------------|
| Synthetic dataset | `data/retail_data.csv` | 62,400 rows, 24 columns |
| EDA notebook | `notebooks/00_eda.ipynb` | 9 sections with inline visualizations |
| DAG notebook | `notebooks/01_causal_graph.ipynb` | Color-coded DAG, backdoor analysis |
| Uplift notebook | `notebooks/02_uplift_modeling.ipynb` | ATE table, CATE heatmaps, winning combos |
| Sensitivity notebook | `notebooks/03_sensitivity.ipynb` | Tornado chart, scorecard, stability plots |
| City uplift bars | `reports/figures/city_uplift_bars.png` | Volume & revenue ATE by city |
| CATE distributions | `reports/figures/cate_distributions.png` | Violin plots by treatment x city |
| Winning combo heatmap | `reports/figures/winning_combo_heatmap.png` | Best lever per city matrix |
| Sensitivity tornado | `reports/figures/sensitivity_tornado.png` | Confounder omission impact |
| DAG diagram | `reports/figures/dag_publication.png` | Publication-quality causal graph |
| Robustness scorecard | `reports/figures/robustness_scorecard.png` | Pass/fail table for all treatments |
| Strategy report | `reports/strategy_recommendation.md` | Full business recommendations |

---

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| **DoWhy** | >= 0.11 | Causal identification and ATE estimation |
| **EconML** | >= 0.15 | CATE estimation (LinearDML, CausalForestDML) |
| **pandas** | >= 2.0 | Data manipulation |
| **numpy** | >= 1.24 | Numerical computing |
| **scikit-learn** | >= 1.3 | ML models for nuisance estimation |
| **matplotlib** | >= 3.7 | Visualization |
| **seaborn** | >= 0.13 | Statistical visualization |
| **networkx** | >= 3.1 | DAG construction and analysis |
| **statsmodels** | >= 0.14 | Statistical tests (VIF, partial correlation) |

---

## References

- **DoWhy documentation:** https://www.pywhy.org/dowhy/
- **EconML documentation:** https://econml.azurewebsites.net/
- **Chernozhukov et al. (2018):** "Double/Debiased Machine Learning for Treatment and Structural Parameters" - the DML methodology
- **Pearl, J. (2009):** *Causality: Models, Reasoning, and Inference* - DAGs, d-separation, Backdoor Criterion
- **Imbens & Rubin (2015):** *Causal Inference for Statistics, Social, and Biomedical Sciences* - potential outcomes framework
- **Hernan & Robins (2020):** *Causal Inference: What If* - free textbook on causal inference methods

---

*Built as a learning POC for causal inference in retail analytics.*
