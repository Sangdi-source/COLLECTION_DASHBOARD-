import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="E-commerce Dashboard Analysis",
    layout="wide"
)

#LOAD DATA YANG DIPAKAI
@st.cache_data
def load_data():
    revenue = pd.read_csv("revenue_clean.csv")
    geo = pd.read_csv("geo_clean.csv")

    #DATETIME
    revenue["shipping_limit_date"] = pd.to_datetime(
        revenue["shipping_limit_date"], errors="coerce"
    )
    geo["order_purchase_timestamp"] = pd.to_datetime(
        geo["order_purchase_timestamp"], errors="coerce"
    )
    
    revenue["total_revenue"] = revenue["price"] + revenue["freight_value"]
    geo["total_revenue"] = geo["price"] + geo["freight_value"]

    geo["month"] = geo["order_purchase_timestamp"].dt.to_period("M").astype(str)
    geo["day"] = geo["order_purchase_timestamp"].dt.date
    geo["year"] = geo["order_purchase_timestamp"].dt.year

    #FILL MISSING CATEGORICAL VALUES
    revenue["product_category_name_english"] = revenue[
        "product_category_name_english"
    ].fillna("unknown")

    revenue["seller_id"] = revenue["seller_id"].fillna("unknown")
    geo["customer_city"] = geo["customer_city"].fillna("unknown")
    geo["customer_state"] = geo["customer_state"].fillna("unknown")

    return revenue, geo


revenue_df, geo_df = load_data()

st.title("Dashboard Penjualan dan Geolokasi")
st.markdown("Analisis performa penjualan berdasarkan waktu, kategori produk, dan persebaran geografis.")

#NAME OF STATE FULL
state_map = {
    "SP": "São Paulo",
    "RJ": "Rio de Janeiro",
    "MG": "Minas Gerais",
    "BA": "Bahia",
    "PR": "Paraná", 
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "PE": "Pernambuco",
    "CE": "Ceará",
    "PA": "Pará",
    "GO": "Goiás",
    "MA": "Maranhão",
    "PB": "Paraíba",
    "ES": "Espírito Santo",
    "MT": "Mato Grosso",
    "RN": "Rio Grande do Norte",
    "AL": "Alagoas",
    "PI": "Piauí",
    "DF": "Distrito Federal",
    "MS": "Mato Grosso do Sul",
    "SE": "Sergipe",
    "RO": "Rondônia",
    "TO": "Tocantins",
    "AC": "Acre",
    "AP": "Amapá",
    "RR": "Roraima"
}

#SIDEBAR FILTERS
st.sidebar.header("Filter")

geo_df["state_full"] = geo_df["customer_state"].map(state_map)
state_options = sorted(geo_df["state_full"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect(
    "Pilih State",
    options=state_options,
    default=state_options
)

date_min = geo_df["order_purchase_timestamp"].min()
date_max = geo_df["order_purchase_timestamp"].max()

selected_dates = st.sidebar.date_input(
    "Rentang Tanggal",
    value=(date_min.date(), date_max.date()),
    min_value=date_min.date(),
    max_value=date_max.date()
)

if len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = date_min.date()
    end_date = date_max.date()

top_n = st.sidebar.slider("Top N Kategori / Seller", min_value=5, max_value=20, value=10)

#FILTER GEO DATA
geo_filtered = geo_df[
    (geo_df["order_purchase_timestamp"].dt.date >= start_date) &
    (geo_df["order_purchase_timestamp"].dt.date <= end_date)
].copy()

if selected_states:
    geo_filtered = geo_filtered[geo_filtered["state_full"].isin(selected_states)]

valid_order_ids = geo_filtered["order_id"].unique()

#FILTER REVENUE DATA
revenue_filtered = revenue_df[revenue_df["order_id"].isin(valid_order_ids)].copy()



#KEY PERFORMANCE INDICATORS
total_orders = geo_filtered["order_id"].nunique()
total_revenue = geo_filtered["total_revenue"].sum()
avg_order_value = geo_filtered.groupby("order_id")["total_revenue"].sum().mean()
total_sellers = revenue_filtered["seller_id"].nunique()
total_categories = revenue_filtered["product_category_name_english"].nunique()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Orders", f"{total_orders:,}")
col2.metric("Total Revenue", f"${total_revenue:,.2f}")
col3.metric("Average Order Value", f"${avg_order_value:,.2f}" if pd.notna(avg_order_value) else "$0.00")
col4.metric("Total Sellers", f"{total_sellers:,}")
col5.metric("Total Categories", f"{total_categories:,}")

st.divider()

#TAB LAYOUT
tab1, tab2, tab3, = st.tabs([
    "Tren Waktu",
    "Kategori Produk",
    "Geografis"
])


#TAB1 : TREN WAKTU
with tab1:
    st.subheader("Tren Revenue Bulanan")

    monthly_revenue = (
        geo_filtered.groupby("month", as_index=False)["total_revenue"]
        .sum()
        .sort_values("month")
    )

    fig_month = px.line(
        monthly_revenue,
        x="month",
        y="total_revenue",
        markers=True,
        title="Revenue per Bulan"
    )

    fig_month.update_layout(xaxis_title="Month", yaxis_title="Revenue")
    st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("Tren Order Harian")

    daily_orders = (
        geo_filtered.groupby("day", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "total_order"})
        .sort_values("day")
    )

    fig_day = px.bar(
        daily_orders,
        x="day",
        y="total_order",
        title="Jumlah Order per Hari"
    )
    fig_day.update_layout(xaxis_title="Date", yaxis_title="Orders")
    st.plotly_chart(fig_day, use_container_width=True)

#TAB2 : KATEGORI PRODUK
with tab2:
    st.subheader("Top Kategori berdasarkan Revenue")

    category_perf = (
        revenue_filtered.groupby("product_category_name_english", as_index=False)
        .agg(
            total_revenue=("price", "sum"),
            total_items=("order_item_id", "count"),
            avg_price=("price", "mean")
        )
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
    )

    fig_cat = px.bar(
        category_perf,
        x="total_revenue",
        y="product_category_name_english",
        orientation="h",
        title="Top Kategori Produk",
        text_auto=".2s"
    )

    fig_cat.update_layout(
        xaxis_title="Revenue",
        yaxis_title="Category",
        yaxis={"categoryorder": "total ascending"}
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    st.dataframe(category_perf, use_container_width=True)

    #TOP SELLER
    seller_perf = (
    revenue_filtered.groupby("seller_id", as_index=False)
    .agg(total_revenue=("price", "sum"))
    .sort_values("total_revenue", ascending=False)
)

    top_10_revenue = seller_perf.head(10)["total_revenue"].sum()
    total_revenue_all = seller_perf["total_revenue"].sum()

    top_10_share = top_10_revenue / total_revenue_all

    st.markdown("### Revenue Seller")
    st.metric("TOP 10 SELLER CONTRIBUTION", f"{top_10_share:.2%}")



#TAB3 : GEOGRAFIS
with tab3:
    st.subheader("Revenue per State")

    state_perf = (
        geo_filtered.groupby("state_full", as_index=False)
        .agg(
            total_revenue=("price", "sum"),
            total_orders=("order_id", "nunique")
        )
        .sort_values("total_revenue", ascending=False)
    )

    fig_state = px.bar(
        state_perf,
        x="state_full",
        y="total_revenue",
        title="Revenue per State",
        text_auto=".2s"
    )
    fig_state.update_layout(xaxis_title="State", yaxis_title="Revenue")
    st.plotly_chart(fig_state, use_container_width=True)

    st.subheader("Top Kota berdasarkan Revenue")

    city_perf = (
        geo_filtered.groupby(["state_full", "customer_city"], as_index=False)
        .agg(
            total_revenue=("price", "sum"),
            total_orders=("order_id", "nunique"),
            lat=("geolocation_lat", "mean"),
            lng=("geolocation_lng", "mean")
        )
        .sort_values("total_revenue", ascending=False)
    )

    fig_map = px.scatter_mapbox(
        city_perf,
        lat="lat",
        lon="lng",
        size="total_revenue",
        color="state_full",
        hover_name="customer_city",
        hover_data={
            "state_full": True,
            "total_revenue": ":.2f",
            "total_orders": True,
            "lat": False,
            "lng": False
        },
        zoom=3,
        height=600,
        title="Peta Persebaran Revenue"
    )
    fig_map.update_layout(mapbox_style="open-street-map")
    fig_map.update_layout(margin={"r":0, "t":50, "l":0, "b":0})

    st.plotly_chart(fig_map, use_container_width=True)
    st.dataframe(city_perf.head(20), use_container_width=True)

#RAW DATA PREVIEW
with st.expander("Lihat Sampel Data"):
    st.write("Revenue Data")
    st.dataframe(revenue_filtered.head(20), use_container_width=True)

    st.write("Geo Data")
    st.dataframe(geo_filtered.head(20), use_container_width=True)



