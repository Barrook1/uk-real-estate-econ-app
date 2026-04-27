import streamlit as st
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import plotly.express as px
import requests
import streamlit as st
from textblob import TextBlob

# ---------------------------------------------------
# PAGE CONFIG
# CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="UK Real Estate & Economy Dashboard",
    layout="wide"
)
st.set_page_config(page_title="UK Real Estate & Economy Dashboard", layout="wide")

st.title("UK Real Estate Price Changes and Economic Indicators")
# Keep API keys as requested
GUARDIAN_KEY = "f57dc3df-6bff-431a-aeaa-84da13200f71"
EPC_KEY = "49047b27453a21db42d8e69ad07267ed00314ae0"

st.write("""
This dashboard combines:
# Keep the Land Registry URL as requested
LAND_URL = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"

- HM Land Registry sales data
- EPC floor-area data
- Guardian news sentiment
- ONS unemployment
- ONS median wages
- ONS population growth
- Bank of England interest rates
""")
LOCAL_CSV_CANDIDATES = {
    "bank": ["data/bankrate.csv", "bankrate.csv"],
    "wage": ["data/ons_median_wage.csv", "ons_median_wage.csv"],
    "population": ["data/ons_population.csv", "ons_population.csv"],
    "unemployment": ["data/ons_unemployment.csv", "ons_unemployment.csv"],
}

# ---------------------------------------------------
# PUBLIC API KEYS (DEMO ONLY)
# ---------------------------------------------------
guardian_key = "f57dc3df-6bff-431a-aeaa-84da13200f71"
epc_key = "49047b27453a21db42d8e69ad07267ed00314ae0"

# ---------------------------------------------------
# GITHUB RAW FILE URLS
# Replace USERNAME and REPO if needed
# ---------------------------------------------------
BASE_URL = "https://raw.githubusercontent.com/Barrook1/uk-real-estate-econ-app/main/data/"
def resolve_local_csv(paths: list[str]) -> str:
    """Return the first existing file path from candidates, otherwise first candidate."""
    for candidate in paths:
        if Path(candidate).exists():
            return candidate
    return paths[0]


BANK_URL = resolve_local_csv(LOCAL_CSV_CANDIDATES["bank"])
WAGE_URL = resolve_local_csv(LOCAL_CSV_CANDIDATES["wage"])
POP_URL = resolve_local_csv(LOCAL_CSV_CANDIDATES["population"])
UNEMP_URL = resolve_local_csv(LOCAL_CSV_CANDIDATES["unemployment"])

LAND_URL = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"
BANK_URL = "data/bankrate.csv"
WAGE_URL = "data/ons_median_wage.csv"
POP_URL = "data/ons_population.csv"
UNEMP_URL = "data/ons_unemployment.csv"

# ---------------------------------------------------
# FUNCTIONS
# DATA HELPERS
# ---------------------------------------------------
def get_guardian_articles(query, from_date, to_date):
    url = "https://content.guardianapis.com/search"
@st.cache_data(show_spinner=False)
def load_csv(path_or_url: str) -> pd.DataFrame:
    return pd.read_csv(path_or_url)

    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": guardian_key,
        "show-fields": "headline,trailText",
        "page-size": 50
    }

    response = requests.get(url, params=params)
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    return out

    if response.status_code != 200:
        st.error(f"Guardian API Error: {response.status_code}")
        return pd.DataFrame()

    data = response.json()
    results = data["response"]["results"]
def find_year_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if "year" in col:
            return col
    return None

    rows = []

    for item in results:
        headline = item["webTitle"]
        text = item.get("fields", {}).get("trailText", "")
        pub_date = item["webPublicationDate"][:10]
        article_url = item["webUrl"]
def find_value_column(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if "year" not in col:
            return col
    return None

        sentiment = TextBlob(headline + " " + text).sentiment.polarity

        rows.append({
            "date": pub_date,
            "headline": headline,
            "sentiment": sentiment,
            "url": article_url
        })
def to_year_value(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
    year_col = find_year_column(df)
    value_col = find_value_column(df)

    return pd.DataFrame(rows)
    if year_col is None or value_col is None:
        return pd.DataFrame(columns=["year", value_name])

    out = df[[year_col, value_col]].copy()
    out.columns = ["year", value_name]
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out[value_name] = pd.to_numeric(out[value_name], errors="coerce")
    return out.dropna(subset=["year"]).astype({"year": int})

def get_epc_data(postcode):
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"

    headers = {
        "Authorization": epc_key
# ---------------------------------------------------
# API HELPERS
# ---------------------------------------------------
def get_guardian_articles(query: str, from_date: str, to_date: str) -> pd.DataFrame:
    endpoint = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": GUARDIAN_KEY,
        "show-fields": "headline,trailText",
        "page-size": 50,
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
        res = requests.get(endpoint, params=params, timeout=20)
        res.raise_for_status()
        payload = res.json()
    except Exception as exc:
        st.error(f"Guardian API request failed: {exc}")
        return pd.DataFrame()

    rows = []
    for item in payload.get("response", {}).get("results", []):
        headline = item.get("webTitle", "")
        trail = item.get("fields", {}).get("trailText", "")
        date = item.get("webPublicationDate", "")[:10]
        url = item.get("webUrl", "")
        sentiment = TextBlob(f"{headline} {trail}").sentiment.polarity

@st.cache_data
def load_sales_data():
    return pd.read_csv(LAND_URL)


@st.cache_data
def load_csv(url):
    return pd.read_csv(url)
        rows.append({"date": date, "headline": headline, "sentiment": sentiment, "url": url})

    return pd.DataFrame(rows)

def standardize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df

def get_epc_data(postcode: str) -> pd.DataFrame:
    endpoint = "https://epc.opendatacommunities.org/api/v1/domestic/search"
    headers = {"Authorization": EPC_KEY}

def find_year_column(df):
    for col in df.columns:
        if "year" in col:
            return col
    return None

    try:
        res = requests.get(endpoint, headers=headers, params={"postcode": postcode}, timeout=20)
        res.raise_for_status()
        payload = res.json()
    except Exception as exc:
        st.error(f"EPC API request failed: {exc}")
        return pd.DataFrame()

def find_value_column(df):
    for col in df.columns:
        if col != "year":
            return col
    return None
    return pd.DataFrame(payload.get("rows", []))


# ---------------------------------------------------
# SIDEBAR
# UI
# ---------------------------------------------------
st.sidebar.header("Navigation")
st.title("UK Real Estate Price Changes and Economic Indicators")
st.write(
    """
This dashboard combines:
- HM Land Registry sales data
- EPC floor-area data
- Guardian news sentiment
- ONS unemployment
- ONS median wages
- ONS population growth
- Bank of England interest rates
"""
)

section = st.sidebar.radio(
    "Choose Section",
    [
        "Guardian Sentiment",
        "EPC Property Size",
        "Real Estate Dashboard"
    ]
    ["Real Estate Dashboard", "Guardian Sentiment", "EPC Property Size"],
)

# ---------------------------------------------------
# SECTION 1: GUARDIAN
# ---------------------------------------------------
if section == "Guardian Sentiment":

    st.subheader("Guardian Housing News Sentiment")

    query = st.text_input("Search Term", "UK house prices")
    from_date = st.date_input("From Date", pd.to_datetime("2000-01-01"))
    to_date = st.date_input("To Date", pd.to_datetime("2024-12-31"))
    query = st.text_input("Search Term", value="UK house prices")
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From Date", value=pd.Timestamp("2000-01-01"))
    with col2:
        to_date = st.date_input("To Date", value=pd.Timestamp.today().normalize())

    if st.button("Load Guardian Data"):

        df = get_guardian_articles(query, str(from_date), str(to_date))

        if df.empty:
            st.warning("No results found.")
            st.warning("No Guardian results found for the selected date range.")
        else:
            st.dataframe(df)

            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.to_period("M").astype(str)

            st.dataframe(df, use_container_width=True)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            monthly = (
                df.groupby("month")["sentiment"]
                df.dropna(subset=["date"])
                .assign(month=lambda x: x["date"].dt.to_period("M").astype(str))
                .groupby("month", as_index=False)["sentiment"]
                .mean()
                .reset_index()
            )

            fig = px.line(
                monthly,
                x="month",
                y="sentiment",
                title="Average Monthly Guardian Sentiment"
            )

            fig = px.line(monthly, x="month", y="sentiment", title="Average Monthly Guardian Sentiment")
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# SECTION 2: EPC
# ---------------------------------------------------
elif section == "EPC Property Size":

    st.subheader("EPC Floor Area by Postcode")

    postcode = st.text_input("Enter UK Postcode", "SW1A 1AA")
    postcode = st.text_input("Enter UK Postcode", value="SW1A 1AA")

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
            st.dataframe(epc_df, use_container_width=True)

            size_col = None

            for col in possible_cols:
                if col in epc_df.columns:
                    size_col = col
                    break
            size_col = next(
                (c for c in ["total-floor-area", "floor-area", "floorarea", "total_floor_area"] if c in epc_df.columns),
                None,
            )

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

                st.metric("Average Floor Area (sqm)", round(epc_df[size_col].mean(skipna=True), 2))
                fig = px.histogram(epc_df, x=size_col, nbins=25, title="Distribution of Floor Area")
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No floor-area column found.")
                st.info("No floor-area column found in EPC response.")

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
    sales = normalize_columns(load_csv(LAND_URL))
    bank = normalize_columns(load_csv(BANK_URL))
    wage = normalize_columns(load_csv(WAGE_URL))
    population = normalize_columns(load_csv(POP_URL))
    unemployment = normalize_columns(load_csv(UNEMP_URL))

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
    if not {"date", "price"}.issubset(sales.columns):
        st.error("Sales data must include 'date' and 'price' columns.")
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
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales["year"] = sales["date"].dt.year
    sales["price"] = pd.to_numeric(sales["price"], errors="coerce")

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
    prices = (
        sales.dropna(subset=["year", "price"])
        .groupby("year", as_index=False)["price"]
        .mean()
        .rename(columns={"price": "average_price"})
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(
        combined,
        x="year",
        y=["unemployment_rate", "bank_rate"],
        title="Unemployment Rate vs Interest Rate"
    bank_clean = to_year_value(bank, "bank_rate")
    wage_clean = to_year_value(wage, "median_wage")
    pop_clean = to_year_value(population, "population_growth")
    unemp_clean = to_year_value(unemployment, "unemployment_rate")

    combined = (
        prices.merge(bank_clean, on="year", how="left")
        .merge(wage_clean, on="year", how="left")
        .merge(pop_clean, on="year", how="left")
        .merge(unemp_clean, on="year", how="left")
        .sort_values("year")
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(
        combined,
        x="year",
        y="median_wage",
        title="Median Wage"
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("### Combined Dataset")
    st.dataframe(combined, use_container_width=True)

    fig4 = px.line(
        combined,
        x="year",
        y="population_growth",
        title="Population Growth"
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.plotly_chart(px.line(combined, x="year", y="average_price", title="Average UK Property Price"), use_container_width=True)
    st.plotly_chart(px.line(combined, x="year", y=["unemployment_rate", "bank_rate"], title="Unemployment Rate vs Interest Rate"), use_container_width=True)
    st.plotly_chart(px.line(combined, x="year", y="median_wage", title="Median Wage"), use_container_width=True)
    st.plotly_chart(px.line(combined, x="year", y="population_growth", title="Population Growth"), use_container_width=True)

    # -------------------------------
    # OPTIONAL LOCATION ANALYSIS
    # -------------------------------
    if "town" in sales.columns:
        top_towns = (
            sales.groupby("town")["price"]
            sales.dropna(subset=["town", "price"])
            .groupby("town", as_index=False)["price"]
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
        st.plotly_chart(px.bar(top_towns, x="town", y="price", title="Top Towns by Average Price"), use_container_width=True)

    if "property_type" in sales.columns:
        by_type = (
            sales.groupby("property_type")["price"]
            sales.dropna(subset=["property_type", "price"])
            .groupby("property_type", as_index=False)["price"]
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
        st.plotly_chart(px.bar(by_type, x="property_type", y="price", title="Average Price by Property Type"), use_container_width=True)
