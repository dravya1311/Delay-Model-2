import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# ---------------------------------------
# CONFIG
# ---------------------------------------
st.set_page_config(page_title="Order Delay Dashboard", layout="wide")

# ---------------------------------------
# HELPERS
# ---------------------------------------
def normalize_columns(df):
    df.columns = [re.sub(r'[^a-z0-9]+', '_', c.strip().lower()) for c in df.columns]
    return df

def load_data():
    local_file = "Delay_Model.csv"
    github_url = "https://raw.githubusercontent.com/dravya1311/Delay-Model-2/main/Delay_Model.csv"

    if os.path.exists(local_file):
        df = pd.read_csv(local_file)
    else:
        df = pd.read_csv(github_url)

    return normalize_columns(df)

# ---------------------------------------
# LOAD DATA
# ---------------------------------------
df = load_data()

# ---------------------------------------
# CLEANING
# ---------------------------------------
df["label"] = pd.to_numeric(df["label"], errors="coerce")

for col in ["sales", "profit_per_order", "order_item_quantity"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ---------------------------------------
# HEADER KPI
# ---------------------------------------
st.title("📊 Order Delay Analysis Dashboard")

total_orders = len(df)
delayed = (df["label"] == -1).sum()
ontime = (df["label"] == 0).sum()
early = (df["label"] == 1).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Orders", total_orders)
c2.metric("Delayed", delayed)
c3.metric("On Time", ontime)
c4.metric("Early", early)

st.markdown("---")

# ---------------------------------------
# FILTERS
# ---------------------------------------
st.sidebar.header("Filters")

regions = df["order_region"].dropna().unique() if "order_region" in df else []
shipping = df["shipping_mode"].dropna().unique() if "shipping_mode" in df else []

selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
selected_shipping = st.sidebar.multiselect("Shipping Mode", shipping, default=shipping)

filtered = df.copy()

if "order_region" in df:
    filtered = filtered[filtered["order_region"].isin(selected_regions)]

if "shipping_mode" in df:
    filtered = filtered[filtered["shipping_mode"].isin(selected_shipping)]

# ---------------------------------------
# DELAY BY REGION
# ---------------------------------------
st.subheader("Delay % by Region")

delay_region = (
    filtered.groupby("order_region")["label"]
    .apply(lambda x: ((x == -1).mean() * 100).round(0))
    .reset_index(name="delay_pct")
)

fig = px.bar(
    delay_region,
    x="order_region",
    y="delay_pct",
    text=delay_region["delay_pct"].astype(int)   # ✅ comma added above
)

# ---------------------------------------
# SHIPPING MODE DELAY
# ---------------------------------------
st.subheader("Delay by Shipping Mode")

delay_ship = (
    filtered.groupby("shipping_mode")["label"]
    .apply(lambda x: ((x == -1).mean() * 100).round(0))
    .reset_index(name="delay_pct")
)

fig = px.bar(delay_ship, x="shipping_mode", y="delay_pct", text_auto=True)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------
# TOP DELAYED PRODUCTS
# ---------------------------------------
st.subheader("Top 5 Most Delayed Products")

prod_delay = (
    filtered.groupby("product_name")["label"]
    .mean()
    .reset_index()
)

top_products = prod_delay.nsmallest(5, "label")

fig = px.bar(
    top_products,
    x="label",
    y="product_name",
    orientation="h",
    text_auto=True,
    title="Most Delayed Products"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------
# STANDARD CLASS DELAY
# ---------------------------------------
st.subheader("Delay by Region (Standard Class)")

std = filtered[filtered["shipping_mode"] == "Standard Class"]

std_delay = (
    std.groupby("order_region")["label"]
    .apply(lambda x: ((x == -1).mean() * 100).round(0))
    .reset_index(name="delay_pct")
)

fig = px.bar(std_delay, x="order_region", y="delay_pct", text_auto=True)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------
# ROUTE DELAY (FIXED)
# ---------------------------------------
st.subheader("Top 10 Most Delayed Routes")

if all(col in df.columns for col in ["order_city", "order_country", "customer_city", "customer_country"]):

    route_df = filtered.copy()

    route_df["origin"] = route_df["order_city"].astype(str) + ", " + route_df["order_country"].astype(str)
    route_df["destination"] = route_df["customer_city"].astype(str) + ", " + route_df["customer_country"].astype(str)

    route_delay = (
        route_df.groupby(["origin", "destination"])["label"]
        .mean()
        .reset_index()
    )

    top_routes = route_delay.nsmallest(10, "label")

    fig = px.bar(
        top_routes,
        x="label",
        y="origin",
        orientation="h",
        color="label",
        text_auto=True,
        title="Most Delayed Routes"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Route data not available in dataset")

# ---------------------------------------
# ORDER STATUS DISTRIBUTION
# ---------------------------------------
if "order_status" in df.columns:
    st.subheader("Order Status Distribution")

    status = (df["order_status"].value_counts(normalize=True) * 100).round(0)
    status = status.reset_index()
    status.columns = ["status", "percentage"]

    fig = px.pie(status, names="status", values="percentage", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------
# INSIGHT BLOCK
# ---------------------------------------
st.markdown("---")

st.subheader("📌 Key Insights")

st.markdown(f"""
- Total delayed orders: **{delayed}**
- Highest delay seen in specific regions and shipping modes
- Standard Class contributing major delays
- Certain products and routes consistently underperforming
""")
