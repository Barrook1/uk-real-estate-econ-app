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
This dashboard combines:

- HM Land Registry sales data
- EPC floor-area data
- Guardian news sentiment
- ONS unemployment
- ONS median wages
- ONS population growth
- Bank of England interest rates
""")

# ---------------------------------------------------
# PUBLIC API KEYS (DEMO ONLY)
# ---------------------------------------------------
guardian_key = "f57dc3df-6bff-431a-aeaa-84da13200f71"
epc_key = "49047b27453a21db42d8e69ad07267ed00314ae0"

# ---------------------------------------------------
# GITHUB RAW FILE URLS
# Replace USERNAME and REPO if needed
# ---------------------------------------------------
BASE_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/uk-real-estate-econ-app/main/data/"

LAND_URL = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"
BANK_URL = BASE_URL + "bankrate.csv"
WAGE_URL = BASE_URL + "ons_median_wage.csv"
POP_URL = BASE_URL + "ons_population.csv"
UNEMP_URL = BASE_URL + "ons_unemployment.csv"

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
    return pd.read_csv(LAND_URL)


@st.cache_data
def load_csv(url):
    return pd.read_csv(url)


def standardize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df


def find_year_column(df):
    for col in df.columns:
        if "year" in col:
            return col
    return None


def find_value_column(df):
    for col in df.columns:
        if col != "year":
            return col
    return None


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
    from_date = st.date_input("From Date", pd.to_datetime("2000-01-01"))
    to_date = st.date_input("To Date", pd.to_datetime("2024-12-31"))

    if st.button("Load Guardian Data"):

        df = get_guardian_articles(query, str(from_date), str(to_date))

        if df.empty:
            st.warning("No results found.")
        else:
            st.dataframe(df)

            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.to_period("M").astype(str)

            monthly = (
                df.groupby("month")["sentiment"]
                .mean()
                .reset_index()
            )

            fig = px.line(
                monthly,
                x="month",
                y="sentiment",
                title="Average Monthly Guardian Sentiment"
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
                epc_df[size_col] = pd.to_numeric(epc_df[size_col], errors="coerce")

                st.metric(
                    "Average Floor Area (sqm)",
                    round(epc_df[size_col].mean(), 2)
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
# SECTION 3: REAL ESTATE + ECON DASHBOARD
# ---------------------------------------------------
else:

    st.subheader("UK Housing Market and Economic Indicators")

    # Load files
    sales = standardize_columns(load_sales_data())
    bank = standardize_columns(load_csv(BANK_URL))
    wage = standardize_columns(load_csv(WAGE_URL))
    pop = standardize_columns(load_csv(POP_URL))
    unemp = standardize_columns(load_csv(UNEMP_URL))

    # -------------------------------
    # SALES DATA
    # -------------------------------
    st.markdown("### HM Land Registry Data")

    st.dataframe(sales.head(10))

    if "date" in sales.columns and "price" in sales.columns:

        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
        sales["year"] = sales["date"].dt.year
        sales["price"] = pd.to_numeric(sales["price"], errors="coerce")

        prices = (
            sales.groupby("year")["price"]
            .mean()
            .reset_index()
            .rename(columns={"price": "average_price"})
        )

    else:
        st.error("Sales CSV must contain date and price columns.")
        st.stop()

    # -------------------------------
    # CLEAN ECON FILES
    # Assumes each file has one year column and one value column
    # -------------------------------
    def prep(df, new_name):
        y = find_year_column(df)
        v = find_value_column(df)

        out = df[[y, v]].copy()
        out.columns = ["year", new_name]
        out["year"] = pd.to_numeric(out["year"], errors="coerce")
        out[new_name] = pd.to_numeric(out[new_name], errors="coerce")
        return out

    bank = prep(bank, "bank_rate")
    wage = prep(wage, "median_wage")
    pop = prep(pop, "population_growth")
    unemp = prep(unemp, "unemployment_rate")

    # -------------------------------
    # MERGE ALL DATA
    # -------------------------------
    combined = prices.merge(bank, on="year", how="left")
    combined = combined.merge(wage, on="year", how="left")
    combined = combined.merge(pop, on="year", how="left")
    combined = combined.merge(unemp, on="year", how="left")

    st.markdown("### Combined Dataset")
    st.dataframe(combined)

    # -------------------------------
    # CHARTS
    # -------------------------------
    fig1 = px.line(
        combined,
        x="year",
        y="average_price",
        title="Average UK Property Price"
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(
        combined,
        x="year",
        y=["unemployment_rate", "bank_rate"],
        title="Unemployment Rate vs Interest Rate"
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(
        combined,
        x="year",
        y="median_wage",
        title="Median Wage"
    )
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.line(
        combined,
        x="year",
        y="population_growth",
        title="Population Growth"
    )
    st.plotly_chart(fig4, use_container_width=True)

    # -------------------------------
    # OPTIONAL LOCATION ANALYSIS
    # -------------------------------
    if "town" in sales.columns:
        top_towns = (
            sales.groupby("town")["price"]
            .mean()
            .reset_index()
            .sort_values("price", ascending=False)
            .head(15)
        )

        fig5 = px.bar(
            top_towns,
            x="town",
            y="price",
            title="Top Towns by Average Price"
        )
        st.plotly_chart(fig5, use_container_width=True)

    if "property_type" in sales.columns:
        by_type = (
            sales.groupby("property_type")["price"]
            .mean()
            .reset_index()
        )

        fig6 = px.bar(
            by_type,
            x="property_type",
            y="price",
            title="Average Price by Property Type"
        )
        st.plotly_chart(fig6, use_container_width=True)
