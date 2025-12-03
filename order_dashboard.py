# order_delay_dashboard.py
# Polished Streamlit dashboard for Order Delay Analysis
# Assumes dataset file name: Delay_Model.csv (repo root) OR will attempt GitHub raw URL fallback.

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import re

st.set_page_config(page_title="Order Delay Analysis Dashboard", layout="wide")

# ----------------------
# Helpers
# ----------------------
def normalize_cols(df):
    """Return df with an internal map of normalized -> actual column names and a normalized-copy columns."""
    mapping = {}
    for c in df.columns:
        norm = re.sub(r'[^a-z0-9]+', '_', c.strip().lower())
        mapping[norm] = c
    # create a view copy with normalized column labels for safe access
    df_norm = df.copy()
    df_norm.columns = [re.sub(r'[^a-z0-9]+', '_', c.strip().lower()) for c in df.columns]
    return df_norm, mapping

def find_col(mapping, candidates):
    """Find first candidate present in normalized->actual mapping keys; return actual column name or None."""
    for cand in candidates:
        cand_norm = re.sub(r'[^a-z0-9]+', '_', cand.strip().lower())
        if cand_norm in mapping:
            return mapping[cand_norm]
    return None

def try_load(path_or_url):
    try:
        if path_or_url.startswith("http"):
            return pd.read_csv(path_or_url)
        if os.path.exists(path_or_url):
            return pd.read_csv(path_or_url)
    except Exception:
        return None
    return None

# ----------------------
# Auto-load file (local first, then GitHub raw)
# ----------------------
LOCAL_NAME = "Delay_Model.csv"
GITHUB_RAW = "https://raw.githubusercontent.com/dravya1311/Delay-Model-2/main/Delay_Model.csv"

df = try_load(LOCAL_NAME)
if df is None:
    df = try_load(GITHUB_RAW)

if df is None:
    st.error("Unable to load data. Place 'Delay_Model.csv' in repo root or ensure the GitHub raw URL is reachable.")
    st.stop()

# ----------------------
# Normalize and map actual columns
# ----------------------
df_norm, col_map = normalize_cols(df)

# Expected logical columns and candidate names (based on provided header)
candidates = {
    "order_id": ["order_id","order id","orderid"],
    "order_region": ["order_region","order region","region"],
    "order_country": ["order_country","order country","country"],
    "shipping_mode": ["shipping_mode","shipping mode","shipping_mode","shippingmode"],
    "category_name": ["category_name","category name","category"],
    "product_name": ["product_name","product name","product"],
    "sales": ["sales","sales_per_customer","sales_per_order","sales_total"],
    "profit_per_order": ["profit_per_order","profit_per_order","order_profit_per_order","profit"],
    "quantity": ["order_item_quantity","quantity","order_item_qty","qty"],
    "label": ["label","order_status","delay_flag","delay_status"]
}

found = {}
for std, cand_list in candidates.items():
    actual = find_col(col_map, cand_list)
    found[std] = actual

missing_critical = [k for k,v in found.items() if v is None and k in ("label","order_region","shipping_mode")]
if missing_critical:
    st.error(f"Critical columns missing from dataset: {missing_critical}. Column names detected: {list(df.columns)}")
    st.stop()

# For convenience, create a working df with standardized column names (use actual names where found)
work = df.copy()
# rename actual -> standardized short names
rename_map = {found[k]: k for k in found if found[k] is not None}
work = work.rename(columns=rename_map)

# Ensure numeric where needed
work["label"] = pd.to_numeric(work["label"], errors="coerce")
for col in ("sales","profit_per_order","quantity"):
    if col in work.columns:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)

# ----------------------
# Dashboard header & top KPIs
# ----------------------
st.title("📊 Order Delay Analysis Dashboard")
st.markdown("**Delay labeling:** `-1 = delayed`, `0 = on-time`, `1 = early`")

total_orders = len(work)
delayed_count = int((work["label"] == -1).sum()) if "label" in work.columns else 0
ontime_count = int((work["label"] == 0).sum()) if "label" in work.columns else 0
early_count = int((work["label"] == 1).sum()) if "label" in work.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total orders", f"{total_orders:,}")
k2.metric("Delayed orders (label=-1)", f"{delayed_count:,}")
k3.metric("On-time orders (label=0)", f"{ontime_count:,}")
k4.metric("Early deliveries (label=1)", f"{early_count:,}")

st.markdown("---")

# ----------------------
# Filters
# ----------------------
st.sidebar.header("Filters")
regions = sorted(work["order_region"].dropna().unique()) if "order_region" in work.columns else []
ships = sorted(work["shipping_mode"].dropna().unique()) if "shipping_mode" in work.columns else []
sel_regions = st.sidebar.multiselect("Filter: Order Region", options=regions, default=regions)
sel_shipping = st.sidebar.multiselect("Filter: Shipping Mode", options=ships, default=ships)

filtered = work.copy()
if "order_region" in filtered.columns and sel_regions:
    filtered = filtered[filtered["order_region"].isin(sel_regions)]
if "shipping_mode" in filtered.columns and sel_shipping:
    filtered = filtered[filtered["shipping_mode"].isin(sel_shipping)]
    # ------------------------------


# ----------------------
# KPI panels by region (avg sales, avg profit)
# ----------------------
st.header("Region KPIs")
cols = st.columns(2)

if "sales" in filtered.columns:
    avg_sales = filtered.groupby("order_region", dropna=False)["sales"].mean().reset_index().rename(columns={"sales":"avg_sales"})
else:
    avg_sales = pd.DataFrame(columns=["order_region","avg_sales"])

if "profit_per_order" in filtered.columns:
    avg_profit = filtered.groupby("order_region", dropna=False)["profit_per_order"].mean().reset_index().rename(columns={"profit_per_order":"avg_profit"})
else:
    avg_profit = pd.DataFrame(columns=["order_region","avg_profit"])

cols[0].subheader("Average Sales per Customer in US dollars (by Region)")
cols[0].dataframe(avg_sales.sort_values("avg_sales", ascending=False), use_container_width=True)

cols[1].subheader("Average Profit per Order in US dollars (by Region)")
cols[1].dataframe(avg_profit.sort_values("avg_profit", ascending=False), use_container_width=True)

st.markdown("---")

# ----------------------
# Top 5 countries and regions
# ----------------------
st.header("Top Markets")
left, right = st.columns(2)
if "order_country" in filtered.columns:
    top_countries = filtered["order_country"].value_counts().head(5).reset_index()
    top_countries.columns = ["order_country","orders"]
    left.subheader("Top 5 Countries by Order Count")
    left.dataframe(top_countries, use_container_width=True)
else:
    left.info("order_country not available")

if "order_region" in filtered.columns:
    top_regions = filtered["order_region"].value_counts().head(5).reset_index()
    top_regions.columns = ["order_region","orders"]
    right.subheader("Top 5 Regions by Order Count")
    right.dataframe(top_regions, use_container_width=True)
else:
    right.info("order_region not available")

st.markdown("---")

# ----------------------
# Top 8 profitable categories
# ----------------------
st.header("Top Categories & Products")
if "category_name" in filtered.columns and "profit_per_order" in filtered.columns:
    top8_cat = filtered.groupby("category_name", dropna=False)["profit_per_order"].sum().nlargest(8).reset_index()
    st.subheader("Top 8 Most Profitable Categories")
    st.plotly_chart(px.bar(top8_cat, x="category_name", y="profit_per_order", text_auto=True, title="Top 8 Profitable Categories"), use_container_width=True)
else:
    st.info("category_name or profit_per_order missing; skipping top category chart")

# ----------------------
# Most profitable product per region
# ----------------------
if all(c in filtered.columns for c in ("order_region","product_name","profit_per_order")):
    prof_prod = filtered.groupby(["order_region","product_name"], dropna=False)["profit_per_order"].sum().reset_index()
    idx = prof_prod.groupby("order_region")["profit_per_order"].idxmax()
    best_prod = prof_prod.loc[idx].reset_index(drop=True)
    st.subheader("Most Profitable Product per Region")
    st.dataframe(best_prod, use_container_width=True)
else:
    st.info("Required columns for most profitable product per region missing; skipping")

st.markdown("---")

# ----------------------
# Top sold categories by quantity & revenue
# ----------------------
st.header("Top Selling Categories")
if "category_name" in filtered.columns:
    if "quantity" in filtered.columns:
        top_qty = filtered.groupby("category_name", dropna=False)["quantity"].sum().sort_values(ascending=False).head(5).reset_index()
        st.subheader("Top 5 Categories by Quantity")
        st.plotly_chart(px.bar(top_qty, x="category_name", y="quantity", text_auto=True), use_container_width=True)
    else:
        st.info("quantity column missing; skipping quantity ranking")

    if "sales" in filtered.columns:
        top_rev = filtered.groupby("category_name", dropna=False)["sales"].sum().sort_values(ascending=False).head(5).reset_index()
        st.subheader("Top 5 Categories by Revenue")
        st.plotly_chart(px.bar(top_rev, x="category_name", y="sales", text_auto=True), use_container_width=True)
    else:
        st.info("sales column missing; skipping revenue ranking")
else:
    st.info("category_name missing; skipping top selling categories section")

st.markdown("---")

# ----------------------
# Preferred shipping mode by region
# ----------------------
st.header("Shipping Mode Preference")
if all(c in filtered.columns for c in ("order_region","shipping_mode")):
    pref = filtered.groupby(["order_region","shipping_mode"], dropna=False).size().reset_index(name="count")
    st.plotly_chart(px.bar(pref, x="order_region", y="count", color="shipping_mode", barmode="group", title="Preferred Shipping Mode by Region"), use_container_width=True)
else:
    st.info("order_region or shipping_mode missing; skipping shipping preference chart")

st.markdown("---")

# ----------------------
# Delay analysis: counts and percentages
# ----------------------
st.header("Delay Analysis (label = -1 → delayed)")

# Delay by shipping_mode
if "shipping_mode" in filtered.columns and "label" in filtered.columns:
    delay_by_ship = filtered[filtered["label"] == 1].groupby("shipping_mode", dropna=False)["label"].count().reset_index(name="delay_count")
    total_by_ship = filtered.groupby("shipping_mode", dropna=False)["label"].count().reset_index(name="total_count")
    delay_summary_ship = total_by_ship.merge(delay_by_ship, on="shipping_mode", how="left").fillna(0)
    delay_summary_ship["delay_pct"] = (delay_summary_ship["delay_count"] / delay_summary_ship["total_count"]) * 100
    delay_summary_ship = delay_summary_ship.sort_values("delay_count", ascending=False)
    st.subheader("Delayed orders by Shipping Mode")
    st.dataframe(delay_summary_ship[["shipping_mode","delay_count","total_count","delay_pct"]], use_container_width=True)
    # most delayed shipping mode
    if not delay_summary_ship.empty:
        worst = delay_summary_ship.loc[delay_summary_ship["delay_count"].idxmax()]
        st.warning(f"Most delayed shipping mode: **{worst['shipping_mode']}** — {int(worst['delay_count'])} delays ({worst['delay_pct']:.2f}% of its orders)")
    # chart
    st.plotly_chart(px.bar(delay_summary_ship, x="shipping_mode", y="delay_count", title="Delay Count by Shipping Mode", text_auto=True), use_container_width=True)
else:
    st.info("shipping_mode or label missing; skipping delay by shipping mode")

# Delay by order_region + percentage
if "order_region" in filtered.columns and "label" in filtered.columns:
    total_by_region = filtered.groupby("order_region", dropna=False)["label"].count().reset_index(name="total_count")
    delayed_by_region = filtered[filtered["label"] == -1].groupby("order_region", dropna=False)["label"].count().reset_index(name="delay_count")
    delay_summary_region = total_by_region.merge(delayed_by_region, on="order_region", how="left").fillna(0)
    delay_summary_region["delay_pct"] = (delay_summary_region["delay_count"] / delay_summary_region["total_count"]) * 100
    delay_summary_region = delay_summary_region.sort_values("delay_count", ascending=False)
    st.subheader("Delayed orders by Region (counts & %)")
    st.dataframe(delay_summary_region[["order_region","delay_count","total_count","delay_pct"]], use_container_width=True)
    st.plotly_chart(px.bar(delay_summary_region, x="order_region", y="delay_pct", title="Delay % by Region", text_auto=True), use_container_width=True)
else:
    st.info("order_region or label missing; skipping delay by region")

# --------------------------------------------
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# KPI: Delay breakup by order-region for STANDARD CLASS only
# ---------------------------------------------------------------
st.subheader("Delay Breakup by Order-Region (Standard Class)")

# Use filtered dataframe instead of df_view
std_df = filtered[filtered["shipping_mode"] == "Standard Class"].copy()

# Identify delayed orders (label = -1)
std_df["is_delayed"] = std_df["label"] == -1

# Group by region
delay_region_std = (
    std_df.groupby("order_region")["is_delayed"]
    .mean()
    .reset_index()
    .rename(columns={"is_delayed": "delay_rate"})
)

# Graph
fig_std_delay = px.bar(
    delay_region_std,
    x="order_region",
    y="delay_rate",
    text=delay_region_std["delay_rate"].round(2),
    title="Delay % by Order-Region — Standard Class",
    color="delay_rate"
)

fig_std_delay.update_traces(textposition="outside")
fig_std_delay.update_layout(
    yaxis_title="Delay Rate (0 = none, 1 = fully delayed)",
    xaxis_title="Order Region"
)

st.plotly_chart(fig_std_delay, use_container_width=True)
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# KPI: Top 10 Most Delayed Routes (Delay Percentage)
# ---------------------------------------------------------------
st.subheader("Top 10 Most Delayed Routes (by Delay %)")

# Map correct column names
req_cols = ["Order city", "Order Country", "Customer city",
            "Customer Country", "label"]

for c in req_cols:
    if c not in filtered.columns:
        st.error(f"Missing required column: {c}")
        st.stop()

# Build origin & destination
filtered["origin"] = (
    filtered["Order city"].astype(str) + ", " + filtered["Order Country"].astype(str)
)

filtered["destination"] = (
    filtered["Customer city"].astype(str) + ", " + filtered["Customer Country"].astype(str)
)

# Identify delayed orders (-1 = delayed)
filtered["is_delayed"] = filtered["label"] == -1

# Group by route
route_grp = (
    filtered.groupby(["origin", "destination"])
    .agg(
        total_orders=("label", "count"),
        delayed_orders=("is_delayed", "sum")
    )
    .reset_index()
)

# Compute delay %
route_grp["delay_pct"] = (route_grp["delayed_orders"] /
                          route_grp["total_orders"]) * 100

# Top 10 delayed
top10_routes = route_grp.nlargest(10, "delay_pct")

# Plot
fig_routes = px.bar(
    top10_routes,
    x="delay_pct",
    y="origin",
    color="delay_pct",
    orientation="h",
    text=top10_routes["delay_pct"].round(2),
    title="Top 10 Most Delayed Routes (by Delay %)",
)

fig_routes.update_traces(textposition="outside")
fig_routes.update_layout(
    xaxis_title="Delay % (Higher means worse delay)",
    yaxis_title="Origin"
)

st.plotly_chart(fig_routes, use_container_width=True)
