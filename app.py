import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from textblob import TextBlob

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="UK Real Estate & Economy Dashboard",
    layout="wide"
)

st.title("UK Real Estate Price Changes and Economic Indicators")

st.write("""
This dashboard explores UK housing prices using:
- HM Land Registry sales data
- EPC floor-area data
- Guardian news sentiment
- Google Drive hosted property data
""")

# ---------------------------------------------------
# PUBLIC API KEYS (DEMO ONLY)
# ---------------------------------------------------
guardian_key = "f57dc3df-6bff-431a-aeaa-84da13200f71"
epc_key = "49047b27453a21db42d8e69ad07267ed00314ae0"

# ---------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------
def get_guardian_articles(query, from_date, to_date):
    url = "https://content.guardianapis.com/search"

    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": guardian_key,
        "show-fields": "headline,trailText",
        "page-size": 50
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        st.error(f"Guardian API Error: {response.status_code}")
        return pd.DataFrame()

    data = response.json()
    results = data["response"]["results"]

    rows = []

    for item in results:
        headline = item["webTitle"]
        text = item.get("fields", {}).get("trailText", "")
        pub_date = item["webPublicationDate"][:10]
        article_url = item["webUrl"]

        sentiment = TextBlob(headline + " " + text).sentiment.polarity

        rows.append({
            "date": pub_date,
            "headline": headline,
            "sentiment": sentiment,
            "url": article_url
        })

    return pd.DataFrame(rows)


def get_epc_data(postcode):
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"

    headers = {
        "Authorization": epc_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error(f"EPC API Error: {response.status_code}")
        return pd.DataFrame()

    try:
        data = response.json()
        rows = data.get("rows", [])
        return pd.DataFrame(rows)

    except Exception:
        st.error("Failed to parse EPC response.")
        return pd.DataFrame()


@st.cache_data
def load_sales_data():
    url = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"
    return pd.read_csv(url)


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
st.sidebar.header("Navigation")

section = st.sidebar.radio(
    "Choose Section",
    [
        "Guardian Sentiment",
        "EPC Property Size",
        "Real Estate Dashboard"
    ]
)

# ---------------------------------------------------
# SECTION 1: GUARDIAN
# ---------------------------------------------------
if section == "Guardian Sentiment":

    st.subheader("Guardian Housing News Sentiment")

    query = st.text_input("Search Term", "UK house prices")
    from_date = st.date_input("From Date", pd.to_datetime("2023-01-01"))
    to_date = st.date_input("To Date", pd.to_datetime("2024-12-31"))

    if st.button("Load Guardian Data"):

        df = get_guardian_articles(
            query,
            str(from_date),
            str(to_date)
        )

        if df.empty:
            st.warning("No results found.")
        else:
            st.dataframe(df)

            df["date"] = pd.to_datetime(df["date"])

            monthly = (
                df.groupby(df["date"].dt.to_period("M"))["sentiment"]
                .mean()
                .reset_index()
            )

            monthly["date"] = monthly["date"].astype(str)

            fig = px.line(
                monthly,
                x="date",
                y="sentiment",
                title="Average Monthly News Sentiment"
            )

            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# SECTION 2: EPC
# ---------------------------------------------------
elif section == "EPC Property Size":

    st.subheader("EPC Floor Area by Postcode")

    postcode = st.text_input("Enter UK Postcode", "SW1A 1AA")

    if st.button("Load EPC Data"):

        epc_df = get_epc_data(postcode)

        if epc_df.empty:
            st.warning("No EPC records found.")
        else:
            st.dataframe(epc_df)

            possible_cols = [
                "total-floor-area",
                "floor-area",
                "floorarea",
                "total_floor_area"
            ]

            size_col = None

            for col in possible_cols:
                if col in epc_df.columns:
                    size_col = col
                    break

            if size_col:
                epc_df[size_col] = pd.to_numeric(
                    epc_df[size_col],
                    errors="coerce"
                )

                avg_size = epc_df[size_col].mean()

                st.metric(
                    "Average Floor Area (sqm)",
                    round(avg_size, 2)
                )

                fig = px.histogram(
                    epc_df,
                    x=size_col,
                    nbins=20,
                    title="Distribution of Floor Area"
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No floor-area column found.")

# ---------------------------------------------------
# SECTION 3: REAL ESTATE DASHBOARD
# ---------------------------------------------------
else:

    st.subheader("HM Land Registry Dashboard")

    sales = load_sales_data()

    sales.columns = sales.columns.str.strip().str.lower()

    st.write("Raw Data Preview")
    st.dataframe(sales.head(20))

    if "date" in sales.columns and "price" in sales.columns:

        sales["date"] = pd.to_datetime(
            sales["date"],
            errors="coerce"
        )

        sales["year"] = sales["date"].dt.year

        sales["price"] = pd.to_numeric(
            sales["price"],
            errors="coerce"
        )

        yearly = (
            sales.groupby("year")["price"]
            .mean()
            .reset_index()
        )

        yearly.rename(
            columns={"price": "average_price"},
            inplace=True
        )

        st.write("Average Sale Price by Year")
        st.dataframe(yearly)

        fig1 = px.line(
            yearly,
            x="year",
            y="average_price",
            title="Average UK Property Price by Year"
        )
        st.plotly_chart(fig1, use_container_width=True)

        if "town" in sales.columns:
            location_avg = (
                sales.groupby("town")["price"]
                .mean()
                .reset_index()
                .sort_values("price", ascending=False)
                .head(15)
            )

            fig2 = px.bar(
                location_avg,
                x="town",
                y="price",
                title="Top Locations by Average Price"
            )
            st.plotly_chart(fig2, use_container_width=True)

        if "property_type" in sales.columns:
            type_avg = (
                sales.groupby("property_type")["price"]
                .mean()
                .reset_index()
            )

            fig3 = px.bar(
                type_avg,
                x="property_type",
                y="price",
                title="Average Price by Property Type"
            )
            st.plotly_chart(fig3, use_container_width=True)

    else:
        st.error("CSV must contain at least 'date' and 'price' columns.")
