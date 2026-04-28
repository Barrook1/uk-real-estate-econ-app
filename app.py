import streamlit as st
import os
from datetime import date

import numpy as np
import pandas as pd
import requests
import plotly.express as px
import requests
import streamlit as st
from textblob import TextBlob

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="UK Real Estate & Economy Dashboard",
    layout="wide"
)

st.title("UK Real Estate Price Changes and Economic Indicators")
st.set_page_config(page_title="England Real Estate Driver Model", layout="wide")
st.title("England Real Estate Value vs Macro Drivers")
st.write(
    """
This dashboard explores UK housing prices using:
- HM Land Registry
- EPC floor-area data
- Guardian news sentiment
- Economic indicators
Builds a modeling table where the dependent variable is England real-estate value,
with independent variables:
- Bank of England Bank Rate
- ONS median wage
- ONS England population
- ONS unemployment rate
- EPC property size (postcode level)
- Guardian sentiment (TextBlob)
"""
)

# ---------------------------------------------------
# -----------------------------------------------------------------------------
# API KEYS
# ---------------------------------------------------
guardian_key = "f57dc3df-6bff-431a-aeaa-84da13200f71"
epc_key = "49047b27453a21db42d8e69ad07267ed00314ae0"

# ---------------------------------------------------
# GUARDIAN API FUNCTION
# ---------------------------------------------------
def get_guardian_articles(query, from_date, to_date):
    url = "https://content.guardianapis.com/search"
# -----------------------------------------------------------------------------
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "57dc3df-6bff-431a-aeaa-84da13200f71")
EPC_API_KEY = os.getenv("EPC_API_KEY", "49047b27453a21db42d8e69ad07267ed00314ae0")
ONS_BASE_URL = "https://api.beta.ons.gov.uk/v1"
BOE_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def safe_get_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    """GET helper that returns {} if request fails."""
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def monthly_average(df: pd.DataFrame, date_col: str, value_col: str, name: str) -> pd.DataFrame:
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.dropna(subset=[date_col, value_col])
    out["month"] = out[date_col].dt.to_period("M").dt.to_timestamp()
    out = out.groupby("month", as_index=False)[value_col].mean().rename(columns={value_col: name})
    return out


def fit_ols_numpy(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> pd.DataFrame:
    """Simple OLS fit using numpy.linalg.lstsq (no extra dependency)."""
    model_df = df.dropna(subset=[y_col] + x_cols).copy()
    if model_df.empty:
        return pd.DataFrame({"term": [], "coefficient": []})

    X = model_df[x_cols].astype(float).to_numpy()
    y = model_df[y_col].astype(float).to_numpy()

    X = np.column_stack([np.ones(len(X)), X])  # intercept
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    terms = ["intercept"] + x_cols
    return pd.DataFrame({"term": terms, "coefficient": beta})


# -----------------------------------------------------------------------------
# DATA COLLECTORS
# -----------------------------------------------------------------------------
def get_guardian_sentiment(query: str, from_date: str, to_date: str) -> pd.DataFrame:
    url = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": guardian_key,
        "api-key": GUARDIAN_API_KEY,
        "show-fields": "headline,trailText",
        "page-size": 50,
        "page-size": 200,
    }

    response = requests.get(url, params=params)
    data = safe_get_json(url, params=params)
    rows = data.get("response", {}).get("results", [])

    if response.status_code != 200:
        st.error(f"Guardian API error: {response.status_code}")
        return pd.DataFrame()
    parsed = []
    for item in rows:
        headline = item.get("webTitle", "")
        trail = item.get("fields", {}).get("trailText", "")
        pub_date = item.get("webPublicationDate", "")
        polarity = TextBlob(f"{headline} {trail}").sentiment.polarity
        parsed.append({"date": pub_date, "sentiment": polarity})

    data = response.json()
    results = data["response"]["results"]
    if not parsed:
        return pd.DataFrame(columns=["month", "guardian_sentiment"])

    return monthly_average(pd.DataFrame(parsed), "date", "sentiment", "guardian_sentiment")


def get_epc_size_for_postcode(postcode: str) -> float:
    """Returns average floor area for postcode using EPC API."""
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"
    headers = {"Authorization": EPC_API_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        rows = r.json().get("rows", [])
    except Exception:
        rows = []

    if not rows:
        return np.nan

    epc_df = pd.DataFrame(rows)
    for col in ["total-floor-area", "floor-area", "floorArea", "floors-area"]:
        if col in epc_df.columns:
            return pd.to_numeric(epc_df[col], errors="coerce").mean()
    return np.nan


def load_csv_fallback(path: str, date_col: str, value_col: str, out_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return monthly_average(df, date_col, value_col, out_name)


def get_ons_series(dataset_id: str, edition: str, version: str, timeseries: str, out_name: str) -> pd.DataFrame:
    """
    Generic ONS time-series pull.
    Example endpoint pattern:
    /datasets/{id}/editions/{edition}/versions/{version}/observations/{timeseries}
    """
    url = (
        f"{ONS_BASE_URL}/datasets/{dataset_id}/editions/{edition}"
        f"/versions/{version}/observations/{timeseries}"
    )
    data = safe_get_json(url, params={"time": "*"})

    obs = data.get("observations", [])
    rows = []
    for o in obs:
        month = o.get("dimensions", {}).get("time", {}).get("id")
        val = o.get("observation")
        if month and val is not None:
            rows.append({"month": month, out_name: val})

    for item in results:
        headline = item["webTitle"]
        text = item.get("fields", {}).get("trailText", "")
        date = item["webPublicationDate"][:10]
        url_link = item["webUrl"]
    if not rows:
        return pd.DataFrame(columns=["month", out_name])

        sentiment = TextBlob(headline + " " + text).sentiment.polarity
    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df[out_name] = pd.to_numeric(df[out_name], errors="coerce")
    return df.dropna(subset=["month"])

    rows.append({
            "date": date,
            "headline": headline,
            "sentiment": sentiment,
            "url": url_link
        })

    return pd.DataFrame(rows)
def get_bank_rate() -> pd.DataFrame:
    """
    Uses local fallback CSV already in this repo because BOE endpoint is an HTML page.
    CSV columns expected: Date, Bank Rate
    """
    return load_csv_fallback("bankrate.csv", "Date", "Bank Rate", "bank_rate")

# ---------------------------------------------------
# EPC API FUNCTION
# ---------------------------------------------------
def get_epc_data(postcode):
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"

    headers = {
        "Authorization": epc_key
    }
def get_house_price_england() -> pd.DataFrame:
    """
    England real-estate value (dependent variable).
    Uses a local file if present, otherwise synthesizes a monthly trend from available demo data.
    """
    path = "england_real_estate_value.csv"
    if os.path.exists(path):
        return load_csv_fallback(path, "date", "real_estate_value", "real_estate_value")

    # Fallback to a simple deterministic series for structure demonstration.
    months = pd.date_range("2020-01-01", date.today(), freq="MS")
    base = 250_000
    trend = np.linspace(0, 65_000, len(months))
    return pd.DataFrame({"month": months, "real_estate_value": base + trend})


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.sidebar.header("Inputs")
postcode = st.sidebar.text_input("EPC postcode", "SW1A 1AA")
query = st.sidebar.text_input("Guardian query", "England house prices")
from_date = st.sidebar.date_input("Guardian from", pd.to_datetime("2021-01-01"))
to_date = st.sidebar.date_input("Guardian to", pd.to_datetime("today"))

st.sidebar.markdown("### ONS Series (optional)")
use_ons_api = st.sidebar.checkbox("Use ONS API instead of local CSV files", value=False)

if use_ons_api:
    st.sidebar.caption("Fill with your ONS dataset metadata. If blank/invalid, local CSV fallback is used.")
    wage_cfg = {
        "dataset_id": st.sidebar.text_input("Wage dataset id", ""),
        "edition": st.sidebar.text_input("Wage edition", ""),
        "version": st.sidebar.text_input("Wage version", ""),
        "timeseries": st.sidebar.text_input("Wage timeseries", ""),
    }
    pop_cfg = {
        "dataset_id": st.sidebar.text_input("Population dataset id", ""),
        "edition": st.sidebar.text_input("Population edition", ""),
        "version": st.sidebar.text_input("Population version", ""),
        "timeseries": st.sidebar.text_input("Population timeseries", ""),
    }
    unemp_cfg = {
        "dataset_id": st.sidebar.text_input("Unemployment dataset id", ""),
        "edition": st.sidebar.text_input("Unemployment edition", ""),
        "version": st.sidebar.text_input("Unemployment version", ""),
        "timeseries": st.sidebar.text_input("Unemployment timeseries", ""),
    }

    response = requests.get(url, headers=headers)
run = st.sidebar.button("Build Modeling Table")

if response.status_code != 200:
        st.error(f"EPC API error: {response.status_code}")
        return pd.DataFrame()
if run:
    st.info("Pulling and preparing data...")

    try:
        data = response.json()
    house = get_house_price_england()
    bank = get_bank_rate()
    guard = get_guardian_sentiment(query, str(from_date), str(to_date))

        rows = data.get("rows", [])
    epc_size = get_epc_size_for_postcode(postcode)

        if not rows:
            return pd.DataFrame()
    if use_ons_api and all(wage_cfg.values()):
        wage = get_ons_series(**wage_cfg, out_name="median_wage")
    else:
        wage = load_csv_fallback("ons_median_wage.csv", "date", "median_wage", "median_wage")

        return pd.DataFrame(rows)
    if use_ons_api and all(pop_cfg.values()):
        pop = get_ons_series(**pop_cfg, out_name="population_total")
    else:
        pop = load_csv_fallback("ons_population.csv", "date", "population_total", "population_total")

    except:
        st.error("Could not read EPC response.")
        return pd.DataFrame()
    if use_ons_api and all(unemp_cfg.values()):
        unemp = get_ons_series(**unemp_cfg, out_name="unemployment_rate")
    else:
        unemp = load_csv_fallback("ons_unemployment.csv", "date", "unemployment_rate", "unemployment_rate")

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
st.sidebar.header("Controls")
    model_df = house.merge(bank, on="month", how="left")
    model_df = model_df.merge(wage, on="month", how="left")
    model_df = model_df.merge(pop, on="month", how="left")
    model_df = model_df.merge(unemp, on="month", how="left")
    model_df = model_df.merge(guard, on="month", how="left")
    model_df["avg_property_size_sqm"] = epc_size
    model_df = model_df.sort_values("month")

section = st.sidebar.radio(
    "Choose Section",
    ["Guardian Sentiment", "EPC Property Size", "Combined Demo"]
)
    st.subheader("Modeling Table")
    st.dataframe(model_df, use_container_width=True)

# ---------------------------------------------------
# GUARDIAN SECTION
# ---------------------------------------------------
if section == "Guardian Sentiment":
    x_cols = [
        "bank_rate",
        "median_wage",
        "population_total",
        "avg_property_size_sqm",
        "unemployment_rate",
        "guardian_sentiment",
    ]

    st.subheader("Guardian Housing News Sentiment")

    query = st.text_input("Search term", "UK house prices")
    from_date = st.date_input("From date", pd.to_datetime("2023-01-01"))
    to_date = st.date_input("To date", pd.to_datetime("2024-12-31"))

    if st.button("Load Guardian Data"):
    coef_df = fit_ols_numpy(model_df, "real_estate_value", x_cols)
    st.subheader("Linear Model Coefficients")
    st.dataframe(coef_df, use_container_width=True)

        df = get_guardian_articles(
            query,
            str(from_date),
            str(to_date)
        )

        if df.empty:
            st.warning("No data found.")
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
# EPC SECTION
# ---------------------------------------------------
elif section == "EPC Property Size":

    st.subheader("EPC Property Size Data")

    postcode = st.text_input("Enter postcode", "SW1A 1AA")

    if st.button("Load EPC Data"):

        epc_df = get_epc_data(postcode)

        if epc_df.empty:
            st.warning("No EPC records found.")
        else:
            st.dataframe(epc_df)

            possible_size_cols = [
                "total-floor-area",
                "floor-area",
                "floorArea",
                "floors-area"
            ]

            size_col = None
            for col in possible_size_cols:
                if col in epc_df.columns:
                    size_col = col
                    break

            if size_col:
                epc_df[size_col] = pd.to_numeric(
                    epc_df[size_col],
                    errors="coerce"
                )

                avg_size = epc_df[size_col].mean()

                st.metric("Average Floor Area (sqm)", round(avg_size, 2))

                fig = px.histogram(
                    epc_df,
                    x=size_col,
                    nbins=20,
                    title="Distribution of Property Size"
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Floor area column not found in returned data.")

# ---------------------------------------------------
# COMBINED DEMO SECTION
# ---------------------------------------------------
else:
    st.subheader("Combined Example Dashboard")

    demo = pd.DataFrame({
        "year": [2020, 2021, 2022, 2023, 2024],
        "average_price": [250000, 270000, 292000, 285000, 300000],
        "unemployment_rate": [4.5, 4.6, 3.8, 4.1, 4.4],
        "median_wage": [29000, 30000, 32000, 33500, 35000],
        "bank_rate": [0.1, 0.1, 3.5, 5.25, 5.0],
        "population_growth": [0.4, 0.5, 0.6, 0.3, 0.2]
    })

    st.dataframe(demo)

    fig1 = px.line(
        demo,
        x="year",
        y="average_price",
        title="Average Property Price"
    )
    st.plotly_chart(fig1, use_container_width=True)
    fig = px.line(model_df, x="month", y="real_estate_value", title="England Real Estate Value (Dependent Variable)")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.line(
        demo,
        x="year",
        y=["unemployment_rate", "bank_rate"],
        title="Unemployment vs Interest Rates"
        model_df,
        x="month",
        y=["bank_rate", "unemployment_rate", "guardian_sentiment"],
        title="Selected Independent Variables Over Time",
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(
        demo,
        x="year",
        y="median_wage",
        title="Median Wage Growth"
    )
    st.plotly_chart(fig3, use_container_width=True)

st.caption("Beginner version. Next step: replace demo data with real HM Land Registry and ONS datasets.")
st.caption(f"BOE source: {BOE_RATE_URL} | ONS base URL: {ONS_BASE_URL}")
