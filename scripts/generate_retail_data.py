"""
Synthetic Retail Data Generator for Causal Inference POC
=========================================================
Generates 3 years of weekly data for 100 SKUs across 4 Indian cities.
Embeds realistic causal structure with non-linear interactions for
downstream causal discovery and effect estimation.

Usage:
    python scripts/generate_retail_data.py
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
from itertools import product

np.random.seed(42)

# ─────────────────────────────────────────────
# 1. CONSTANTS & CONFIGURATION
# ─────────────────────────────────────────────

NUM_WEEKS = 156  # 3 years
NUM_SKUS = 100
START_DATE = date(2021, 1, 4)  # Monday of ISO week 1, 2021

CITIES = {
    1: {"name": "Mumbai",     "base_demand": 1.20, "price_sensitivity": 1.1, "sms_reach": 0.9},
    2: {"name": "Bengaluru",  "base_demand": 1.00, "price_sensitivity": 0.9, "sms_reach": 1.2},
    3: {"name": "Delhi",      "base_demand": 1.15, "price_sensitivity": 1.0, "sms_reach": 1.0},
    4: {"name": "Hyderabad",  "base_demand": 0.95, "price_sensitivity": 1.05, "sms_reach": 1.1},
}

# Verified ISO week numbers for Indian festivals (2021-2024)
# Where two festivals share a week, both are listed with "|"
FESTIVAL_WEEKS = {
    # 2021
    (2021, 2): "Pongal",
    (2021, 13): "Holi",
    (2021, 19): "Eid ul-Fitr",
    (2021, 33): "Onam",
    (2021, 36): "Ganesh Chaturthi",
    (2021, 40): "Navratri",
    (2021, 41): "Durga Puja",
    (2021, 44): "Diwali",
    (2021, 51): "Christmas",
    # 2022
    (2022, 2): "Pongal",
    (2022, 11): "Holi",
    (2022, 18): "Eid ul-Fitr",
    (2022, 35): "Ganesh Chaturthi",
    (2022, 36): "Onam",  # Note: week 36 also has Ganesh Chaturthi spillover
    (2022, 39): "Navratri",
    (2022, 40): "Durga Puja",
    (2022, 43): "Diwali",
    (2022, 51): "Christmas",
    # 2023
    (2023, 2): "Pongal",
    (2023, 10): "Holi",
    (2023, 16): "Eid ul-Fitr",
    (2023, 35): "Onam",
    (2023, 38): "Ganesh Chaturthi",
    (2023, 41): "Navratri",
    (2023, 42): "Durga Puja",
    (2023, 45): "Diwali",
    (2023, 52): "Christmas",
    # 2024 (partial — only first 52 weeks needed if data ends mid-2024)
    (2024, 2): "Pongal",
    (2024, 13): "Holi",
    (2024, 15): "Eid ul-Fitr",
    (2024, 36): "Ganesh Chaturthi",
    (2024, 37): "Onam",
    (2024, 40): "Navratri",
    (2024, 41): "Durga Puja",
    (2024, 44): "Diwali",
    (2024, 52): "Christmas",
}

# Regional festival relevance multipliers
# (how much a festival boosts demand in each city)
FESTIVAL_CITY_RELEVANCE = {
    "Diwali":             {1: 1.5, 2: 1.3, 3: 1.5, 4: 1.3},  # nationwide, huge
    "Holi":               {1: 1.3, 2: 1.0, 3: 1.4, 4: 1.1},  # stronger in North
    "Eid ul-Fitr":        {1: 1.2, 2: 1.0, 3: 1.3, 4: 1.2},  # stronger in Hyd/Mum/Del
    "Pongal":             {1: 1.0, 2: 1.3, 3: 1.0, 4: 1.2},  # South India
    "Christmas":          {1: 1.1, 2: 1.1, 3: 1.0, 4: 1.0},  # moderate everywhere
    "Ganesh Chaturthi":   {1: 1.4, 2: 1.1, 3: 1.0, 4: 1.2},  # big in Mumbai
    "Navratri":           {1: 1.3, 2: 1.1, 3: 1.2, 4: 1.1},  # Gujarat/North
    "Durga Puja":         {1: 1.1, 2: 1.1, 3: 1.2, 4: 1.0},  # Kolkata influence
    "Onam":               {1: 1.0, 2: 1.2, 3: 1.0, 4: 1.0},  # Kerala, Bengaluru diaspora
}


# ─────────────────────────────────────────────
# 2. SKU / BRAND SETUP
# ─────────────────────────────────────────────

BRANDS = [
    "Parle", "Britannia", "ITC", "Haldirams", "Bikaji",
    "MTR", "Nestle", "Amul", "Balaji", "PepsiCo_Lays",
    "Bingo", "Kurkure", "Too_Yumm", "Act_II", "Sunfeast",
    "Priya", "Lijjat", "Patanjali", "Dabur", "Godrej",
]

def generate_skus(num_skus=NUM_SKUS):
    """Generate SKU metadata with brand assignment and base attributes."""
    skus = []
    for i in range(num_skus):
        brand = BRANDS[i % len(BRANDS)]
        skus.append({
            "sku_id": f"SKU_{i+1:03d}",
            "brand": brand,
            "brand_equity": np.clip(np.random.normal(0.5, 0.15), 0.1, 1.0),
            "base_price": np.round(np.random.uniform(20, 300), 0),
            "category": np.random.choice(
                ["Biscuits", "Chips", "Namkeen", "Instant_Noodles", "Sweets"],
                p=[0.25, 0.20, 0.20, 0.15, 0.20]
            ),
        })
    return pd.DataFrame(skus)


# ─────────────────────────────────────────────
# 3. SEASONALITY & FESTIVAL BOOST
# ─────────────────────────────────────────────

def get_seasonality(week_date, city_id):
    """
    Returns a seasonality multiplier combining:
    - Festival boost (city-specific)
    - Mild annual cycle (summer dip, winter lift for snacks)
    """
    iso_year, iso_week, _ = week_date.isocalendar()
    festival = FESTIVAL_WEEKS.get((iso_year, iso_week))

    # Festival boost
    if festival:
        relevance = FESTIVAL_CITY_RELEVANCE.get(festival, {}).get(city_id, 1.0)
        festival_boost = relevance
    else:
        festival_boost = 1.0

    # Annual cycle: slight dip in monsoon (weeks 26-35), lift in winter (weeks 44-8)
    annual_cycle = 1.0 + 0.08 * np.cos(2 * np.pi * (iso_week - 1) / 52)

    return festival_boost * annual_cycle


# ─────────────────────────────────────────────
# 4. TREATMENT ASSIGNMENT (confounded)
# ─────────────────────────────────────────────

def assign_treatments(row_data):
    """
    Assign treatment levers with realistic confounding:
    - Higher brand_equity SKUs get more promotions
    - Festival weeks trigger more in-store displays and SMS blasts
    - City characteristics influence channel choices
    """
    brand_eq = row_data["brand_equity"]
    is_festival = row_data["is_festival_week"]
    city_info = CITIES[row_data["city_id"]]

    # discount_depth: 0-40%, higher for lower brand equity (price competition)
    # and during festivals
    discount_base = 0.05 + 0.15 * (1 - brand_eq) + 0.10 * is_festival
    discount_depth = np.clip(
        discount_base + np.random.normal(0, 0.05), 0, 0.40
    )

    # is_instore_display: binary, more likely for high equity + festivals
    display_prob = 0.15 + 0.25 * brand_eq + 0.20 * is_festival
    is_instore_display = int(np.random.random() < np.clip(display_prob, 0, 0.85))

    # local_channel_promo: binary, city-dependent + brand equity
    promo_prob = 0.10 + 0.15 * brand_eq + 0.10 * is_festival
    local_channel_promo = int(np.random.random() < np.clip(promo_prob, 0, 0.70))

    # sms_blast_active: binary, more in tech-savvy cities (Bengaluru)
    sms_prob = (0.10 + 0.15 * brand_eq + 0.15 * is_festival) * city_info["sms_reach"]
    sms_blast_active = int(np.random.random() < np.clip(sms_prob, 0, 0.75))

    # Loyalty levers
    loyalty_topup = np.clip(np.random.normal(0.03, 0.02) + 0.02 * brand_eq, 0, 0.10)
    coupon_usage = np.clip(np.random.normal(0.15, 0.08) + 0.05 * is_festival, 0, 0.50)
    is_2x_points = int(np.random.random() < (0.10 + 0.15 * is_festival))

    return {
        "discount_depth": np.round(discount_depth, 4),
        "is_instore_display": is_instore_display,
        "local_channel_promo": local_channel_promo,
        "sms_blast_active": sms_blast_active,
        "loyalty_topup_discount": np.round(loyalty_topup, 4),
        "special_coupon_usage": np.round(coupon_usage, 4),
        "is_2x_points_active": is_2x_points,
    }


# ─────────────────────────────────────────────
# 5. COMPETITOR PRICE INDEX (confounder)
# ─────────────────────────────────────────────

def generate_competitor_price_index(num_weeks, city_id):
    """
    AR(1) process for competitor pricing — slow-moving, city-specific.
    Values around 1.0 (parity), <1 means competitors are cheaper.
    """
    cpi = np.zeros(num_weeks)
    cpi[0] = np.random.normal(1.0, 0.05)
    city_drift = {1: 0.001, 2: -0.001, 3: 0.0005, 4: -0.0005}
    for t in range(1, num_weeks):
        cpi[t] = 0.92 * cpi[t-1] + 0.08 * 1.0 + city_drift[city_id] + np.random.normal(0, 0.02)
    return np.clip(cpi, 0.7, 1.3)


# ─────────────────────────────────────────────
# 6. OUTCOME GENERATION (with causal structure)
# ─────────────────────────────────────────────

def compute_outcomes(row):
    """
    Generate outcomes with an explicit causal data generating process (DGP):

    sales_volume = f(base_demand, seasonality, treatments, confounders, interactions)

    Key non-linear interactions embedded:
    1. SMS + in-store display synergy: combined effect > sum of parts
    2. Discount saturation: diminishing returns beyond 25%
    3. Loyalty 2x points amplifies coupon usage
    4. Brand equity moderates treatment effectiveness
    """
    city_info = CITIES[row["city_id"]]

    # Base demand
    base = 500 * city_info["base_demand"]

    # Confounder effects
    brand_effect = 200 * row["brand_equity"]
    competitor_effect = -150 * (row["competitor_price_index"] - 1.0)
    seasonal_effect = base * (row["seasonality_multiplier"] - 1.0)

    # --- Treatment effects (the causal effects we want to recover) ---

    # Discount effect: diminishing returns (quadratic saturation)
    disc = row["discount_depth"]
    discount_effect = (800 * disc - 1200 * disc**2) * city_info["price_sensitivity"]

    # In-store display: direct lift
    display_effect = 120 * row["is_instore_display"]

    # Local channel promo: moderate lift
    promo_effect = 80 * row["local_channel_promo"]

    # SMS blast: city-dependent effectiveness
    sms_effect = 60 * row["sms_blast_active"] * city_info["sms_reach"]

    # --- NON-LINEAR INTERACTIONS ---

    # 1. SMS + Display synergy: extra 90 units when both active
    sms_display_synergy = 90 * row["sms_blast_active"] * row["is_instore_display"]

    # 2. Brand equity moderates display effectiveness
    brand_display_interaction = 50 * row["brand_equity"] * row["is_instore_display"]

    # 3. Loyalty: 2x points amplifies coupon usage effect
    loyalty_effect = (
        200 * row["special_coupon_usage"]
        + 150 * row["loyalty_topup_discount"]
        + 100 * row["is_2x_points_active"] * row["special_coupon_usage"]  # interaction
    )

    # Total sales volume
    sales_volume = (
        base
        + brand_effect
        + competitor_effect
        + seasonal_effect
        + discount_effect
        + display_effect
        + promo_effect
        + sms_effect
        + sms_display_synergy
        + brand_display_interaction
        + loyalty_effect
        + np.random.normal(0, 40)  # noise
    )
    sales_volume = max(sales_volume, 10)  # floor

    # Revenue: volume * price * (1 - discount)
    effective_price = row["base_price"] * (1 - row["discount_depth"])
    revenue = sales_volume * effective_price

    # Profit margin: base margin eroded by discounts & promos, boosted by volume
    base_margin = 0.25 + 0.10 * row["brand_equity"]  # premium brands have better margins
    discount_erosion = 0.6 * row["discount_depth"]
    promo_cost = 0.02 * row["local_channel_promo"] + 0.01 * row["sms_blast_active"]
    loyalty_cost = 0.5 * row["loyalty_topup_discount"] + 0.03 * row["is_2x_points_active"]
    # Scale economies: higher volume slightly improves margin
    scale_bonus = 0.01 * np.log1p(sales_volume / 500)

    profit_margin = np.clip(
        base_margin - discount_erosion - promo_cost - loyalty_cost + scale_bonus
        + np.random.normal(0, 0.02),
        0.02, 0.45
    )

    return pd.Series({
        "sales_volume": np.round(sales_volume, 1),
        "revenue": np.round(revenue, 2),
        "profit_margin": np.round(profit_margin, 4),
    })


# ─────────────────────────────────────────────
# 7. MAIN DATA GENERATION PIPELINE
# ─────────────────────────────────────────────

def generate_data():
    """Main pipeline: builds the full dataset row by row."""
    print("Generating SKU metadata...")
    skus = generate_skus()

    print("Generating competitor price indices...")
    cpi_by_city = {
        city_id: generate_competitor_price_index(NUM_WEEKS, city_id)
        for city_id in CITIES
    }

    print("Building weekly records...")
    records = []

    for week_idx in range(NUM_WEEKS):
        week_date = START_DATE + timedelta(weeks=week_idx)
        iso_year, iso_week, _ = week_date.isocalendar()

        for city_id in CITIES:
            seasonality = get_seasonality(week_date, city_id)
            festival = FESTIVAL_WEEKS.get((iso_year, iso_week), "None")
            cpi = cpi_by_city[city_id][week_idx]

            for _, sku in skus.iterrows():
                row_data = {
                    "week_date": week_date.isoformat(),
                    "iso_year": iso_year,
                    "iso_week": iso_week,
                    "city_id": city_id,
                    "city_name": CITIES[city_id]["name"],
                    "sku_id": sku["sku_id"],
                    "brand": sku["brand"],
                    "category": sku["category"],
                    "brand_equity": sku["brand_equity"],
                    "base_price": sku["base_price"],
                    "competitor_price_index": np.round(cpi, 4),
                    "seasonality_multiplier": np.round(seasonality, 4),
                    "festival": festival,
                    "is_festival_week": int(festival != "None"),
                }

                # Assign treatments (confounded by brand_equity, festivals, city)
                treatments = assign_treatments(row_data)
                row_data.update(treatments)

                records.append(row_data)

    print(f"Generated {len(records):,} raw records. Computing outcomes...")
    df = pd.DataFrame(records)

    # Compute outcomes using the causal DGP
    outcomes = df.apply(compute_outcomes, axis=1)
    df = pd.concat([df, outcomes], axis=1)

    # Sort for readability
    df = df.sort_values(["week_date", "city_id", "sku_id"]).reset_index(drop=True)

    return df


# ─────────────────────────────────────────────
# 8. ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    df = generate_data()

    output_path = "data/retail_data.csv"
    df.to_csv(output_path, index=False)
    print(f"\nDataset saved to {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nDate range: {df['week_date'].min()} to {df['week_date'].max()}")
    print(f"Cities: {df['city_name'].unique().tolist()}")
    print(f"SKUs: {df['sku_id'].nunique()}")
    print(f"\nOutcome summaries:")
    print(df[['sales_volume', 'revenue', 'profit_margin']].describe().round(2))
