from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from textblob import TextBlob

# -----------------------------------------------------------------------------
# Page configuration: Streamlit allows this only once and it must be near top.
# -----------------------------------------------------------------------------
st.set_page_config(page_title="England Real Estate Driver Model", layout="wide")

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
ONS_BASE_URL = "https://api.beta.ons.gov.uk/v1"
BOE_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"

# These are filled from sidebar input boxes below.
GUARDIAN_API_KEY = "f57dc3df-6bff-431a-aeaa-84da13200f71"
EPC_API_KEY = "49047b27453a21db42d8e69ad07267ed00314ae0"

DATA_DIR = Path(__file__).resolve().parent


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def safe_get_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    """Return JSON from a GET request. If the request fails, return an empty dict."""
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"Request failed: {exc}")
        return {}


def monthly_average(df: pd.DataFrame, date_col: str, value_col: str, out_name: str) -> pd.DataFrame:
    """Convert a date/value DataFrame into monthly averages."""
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=["month", out_name])

    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.dropna(subset=[date_col, value_col])

    if out.empty:
        return pd.DataFrame(columns=["month", out_name])

    out["month"] = out[date_col].dt.to_period("M").dt.to_timestamp()
    return out.groupby("month", as_index=False)[value_col].mean().rename(columns={value_col: out_name})


def read_csv_or_demo(path: str, date_col: str, value_col: str, out_name: str, demo_value: float) -> pd.DataFrame:
    """Read local CSV if available; otherwise return a simple monthly demo series."""
    full_path = DATA_DIR / path
    if full_path.exists():
        df = pd.read_csv(full_path)
        return monthly_average(df, date_col, value_col, out_name)

    months = pd.date_range("2020-01-01", date.today(), freq="MS")
    values = demo_value + np.linspace(0, demo_value * 0.10, len(months))
    return pd.DataFrame({"month": months, out_name: values})


def fit_ols_numpy(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> pd.DataFrame:
    """Simple OLS fit using numpy.linalg.lstsq."""
    available_x = [c for c in x_cols if c in df.columns]
    model_df = df.dropna(subset=[y_col] + available_x).copy()

    if model_df.empty or len(model_df) <= len(available_x):
        return pd.DataFrame(columns=["term", "coefficient"])

    X = model_df[available_x].astype(float).to_numpy()
    y = model_df[y_col].astype(float).to_numpy()
    X = np.column_stack([np.ones(len(X)), X])

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return pd.DataFrame({"term": ["intercept"] + available_x, "coefficient": beta})


# -----------------------------------------------------------------------------
# Data collectors
# -----------------------------------------------------------------------------
def get_guardian_articles(query: str, from_date: str, to_date: str) -> pd.DataFrame:
    """Return individual Guardian articles with TextBlob sentiment."""
    if not GUARDIAN_API_KEY:
        st.warning("Enter your Guardian API key in the sidebar to load Guardian articles.")
        return pd.DataFrame(columns=["date", "headline", "sentiment", "url"])

    url = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": GUARDIAN_API_KEY,
        "show-fields": "headline,trailText",
        "page-size": 100,
    }
    data = safe_get_json(url, params=params)
    results = data.get("response", {}).get("results", [])

    rows = []
    for item in results:
        headline = item.get("webTitle", "")
        trail_text = item.get("fields", {}).get("trailText", "")
        article_date = item.get("webPublicationDate", "")
        article_url = item.get("webUrl", "")
        sentiment = TextBlob(f"{headline} {trail_text}").sentiment.polarity
        rows.append(
            {
                "date": article_date,
                "headline": headline,
                "sentiment": sentiment,
                "url": article_url,
            }
        )
    return pd.DataFrame(rows)


def get_guardian_sentiment(query: str, from_date: str, to_date: str) -> pd.DataFrame:
    """Return monthly average Guardian sentiment."""
    articles = get_guardian_articles(query, from_date, to_date)
    return monthly_average(articles, "date", "sentiment", "guardian_sentiment")


def get_epc_rows(postcode: str) -> pd.DataFrame:
    """Return EPC rows for a postcode."""
    if not EPC_API_KEY:
        st.warning("Enter your EPC API key in the sidebar to load EPC data.")
        return pd.DataFrame()

    url = "https://epc.opendatacommunities.org/api/v1/domestic/search"
    headers = {"Authorization": EPC_API_KEY, "Accept": "application/json"}
    params = {"postcode": postcode}
    data = safe_get_json(url, params=params, headers=headers)
    return pd.DataFrame(data.get("rows", []))


def get_epc_size_for_postcode(postcode: str) -> float:
    """Return average total floor area for a postcode from EPC data."""
    epc_df = get_epc_rows(postcode)
    if epc_df.empty:
        return np.nan

    possible_cols = ["total-floor-area", "floor-area", "floorArea", "floors-area"]
    for col in possible_cols:
        if col in epc_df.columns:
            return pd.to_numeric(epc_df[col], errors="coerce").mean()
    return np.nan


def get_ons_series(dataset_id: str, edition: str, version: str, timeseries: str, out_name: str) -> pd.DataFrame:
    """Generic ONS time-series pull."""
    url = f"{ONS_BASE_URL}/datasets/{dataset_id}/editions/{edition}/versions/{version}/observations/{timeseries}"
    data = safe_get_json(url, params={"time": "*"})

    rows = []
    for observation in data.get("observations", []):
        month = observation.get("dimensions", {}).get("time", {}).get("id")
        value = observation.get("observation")
        if month and value is not None:
            rows.append({"month": month, out_name: value})

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["month", out_name])

    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df[out_name] = pd.to_numeric(df[out_name], errors="coerce")
    return df.dropna(subset=["month"])


def get_bank_rate() -> pd.DataFrame:
    return read_csv_or_demo("bankrate.csv", "Date", "Bank Rate", "bank_rate", 1.5)


def get_house_price_england() -> pd.DataFrame:
    path = DATA_DIR / "england_real_estate_value.csv"
    if path.exists():
        return monthly_average(pd.read_csv(path), "date", "real_estate_value", "real_estate_value")

    months = pd.date_range("2020-01-01", date.today(), freq="MS")
    base = 250_000
    trend = np.linspace(0, 65_000, len(months))
    cycle = 8_000 * np.sin(np.linspace(0, 4 * np.pi, len(months)))
    return pd.DataFrame({"month": months, "real_estate_value": base + trend + cycle})


def build_modeling_table(
    postcode: str,
    guardian_query: str,
    from_date: date,
    to_date: date,
    use_ons_api: bool,
    wage_cfg: dict,
    pop_cfg: dict,
    unemp_cfg: dict,
) -> pd.DataFrame:
    house = get_house_price_england()
    bank = get_bank_rate()
    guard = get_guardian_sentiment(guardian_query, str(from_date), str(to_date))
    epc_size = get_epc_size_for_postcode(postcode)

    if use_ons_api and all(wage_cfg.values()):
        wage = get_ons_series(**wage_cfg, out_name="median_wage")
    else:
        wage = read_csv_or_demo("ons_median_wage.csv", "date", "median_wage", "median_wage", 30_000)

    if use_ons_api and all(pop_cfg.values()):
        pop = get_ons_series(**pop_cfg, out_name="population_total")
    else:
        pop = read_csv_or_demo("ons_population.csv", "date", "population_total", "population_total", 56_000_000)

    if use_ons_api and all(unemp_cfg.values()):
        unemp = get_ons_series(**unemp_cfg, out_name="unemployment_rate")
    else:
        unemp = read_csv_or_demo("ons_unemployment.csv", "date", "unemployment_rate", "unemployment_rate", 4.5)

    model_df = house.merge(bank, on="month", how="left")
    model_df = model_df.merge(wage, on="month", how="left")
    model_df = model_df.merge(pop, on="month", how="left")
    model_df = model_df.merge(unemp, on="month", how="left")
    model_df = model_df.merge(guard, on="month", how="left")
    model_df["avg_property_size_sqm"] = epc_size
    return model_df.sort_values("month")


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
st.title("England Real Estate Value vs Macro Drivers")
st.write(
    """
This dashboard combines a monthly England real-estate value series with Bank Rate, wage,
population, unemployment, EPC floor-area data, and Guardian news sentiment. Local CSV files
are used when available; otherwise the app creates simple demo series so the dashboard still runs.
"""
)

st.sidebar.header("Inputs")

st.sidebar.markdown("### API keys")
GUARDIAN_API_KEY = st.sidebar.text_input(
    "Guardian API key",
    value="",
    type="password",
    help="Paste your Guardian Open Platform API key here. It is used only during this Streamlit session.",
)
EPC_API_KEY = st.sidebar.text_input(
    "EPC API key",
    value="",
    type="password",
    help="Paste your EPC Open Data Communities API key here. It is used only during this Streamlit session.",
)

st.sidebar.markdown("### Data inputs")
postcode = st.sidebar.text_input("EPC postcode", "SW1A 1AA")
guardian_query = st.sidebar.text_input("Guardian query", "England house prices")
from_date = st.sidebar.date_input("Guardian from", pd.to_datetime("2021-01-01"))
to_date = st.sidebar.date_input("Guardian to", pd.to_datetime("today"))

st.sidebar.markdown("### ONS Series optional")
use_ons_api = st.sidebar.checkbox("Use ONS API instead of local CSV/demo series", value=False)

wage_cfg = {"dataset_id": "", "edition": "", "version": "", "timeseries": ""}
pop_cfg = {"dataset_id": "", "edition": "", "version": "", "timeseries": ""}
unemp_cfg = {"dataset_id": "", "edition": "", "version": "", "timeseries": ""}

if use_ons_api:
    st.sidebar.caption("Leave blank to fall back to local CSV/demo series.")
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

section = st.sidebar.radio(
    "Choose section",
    ["Modeling Table", "Guardian Sentiment", "EPC Property Size", "Combined Demo"],
)

run = st.sidebar.button("Build Modeling Table")

if run:
    with st.spinner("Pulling and preparing data..."):
        st.session_state["model_df"] = build_modeling_table(
            postcode=postcode,
            guardian_query=guardian_query,
            from_date=from_date,
            to_date=to_date,
            use_ons_api=use_ons_api,
            wage_cfg=wage_cfg,
            pop_cfg=pop_cfg,
            unemp_cfg=unemp_cfg,
        )

model_df = st.session_state.get("model_df", pd.DataFrame())

if section == "Modeling Table":
    st.subheader("Modeling Table")
    if model_df.empty:
        st.info("Click 'Build Modeling Table' in the sidebar.")
    else:
        st.dataframe(model_df, use_container_width=True)

        x_cols = [
            "bank_rate",
            "median_wage",
            "population_total",
            "avg_property_size_sqm",
            "unemployment_rate",
            "guardian_sentiment",
        ]
        coef_df = fit_ols_numpy(model_df, "real_estate_value", x_cols)
        st.subheader("Linear Model Coefficients")
        if coef_df.empty:
            st.warning("Not enough complete rows to estimate the model.")
        else:
            st.dataframe(coef_df, use_container_width=True)

        fig = px.line(model_df, x="month", y="real_estate_value", title="England Real Estate Value")
        st.plotly_chart(fig, use_container_width=True)

elif section == "Guardian Sentiment":
    st.subheader("Guardian Housing News Sentiment")
    articles = get_guardian_articles(guardian_query, str(from_date), str(to_date))
    if articles.empty:
        st.warning("No Guardian articles returned. Check your API key, query, or date range.")
    else:
        st.dataframe(articles, use_container_width=True)
        monthly = monthly_average(articles, "date", "sentiment", "guardian_sentiment")
        fig = px.line(monthly, x="month", y="guardian_sentiment", title="Monthly Guardian Sentiment")
        st.plotly_chart(fig, use_container_width=True)

elif section == "EPC Property Size":
    st.subheader("EPC Property Size")
    epc_df = get_epc_rows(postcode)
    if epc_df.empty:
        st.warning("No EPC rows returned. Check the postcode or EPC API key.")
    else:
        st.dataframe(epc_df, use_container_width=True)
        avg_size = get_epc_size_for_postcode(postcode)
        st.metric("Average property size, square metres", f"{avg_size:,.1f}" if pd.notna(avg_size) else "Not available")

else:
    st.subheader("Combined Demo")
    demo = pd.DataFrame(
        {
            "year": [2020, 2021, 2022, 2023, 2024],
            "average_price": [250000, 270000, 292000, 285000, 300000],
            "unemployment_rate": [4.5, 4.6, 3.8, 4.1, 4.4],
            "median_wage": [29000, 30000, 32000, 33500, 35000],
            "bank_rate": [0.1, 0.1, 3.5, 5.25, 5.0],
            "population_growth": [0.4, 0.5, 0.6, 0.3, 0.2],
        }
    )
    st.dataframe(demo, use_container_width=True)
    fig1 = px.line(demo, x="year", y="average_price", title="Average Property Price")
    st.plotly_chart(fig1, use_container_width=True)
    fig2 = px.line(demo, x="year", y=["unemployment_rate", "bank_rate"], title="Unemployment vs Bank Rate")
    st.plotly_chart(fig2, use_container_width=True)
    fig3 = px.line(demo, x="year", y="median_wage", title="Median Wage Growth")
    st.plotly_chart(fig3, use_container_width=True)

st.caption("CSV fallback file names: bankrate.csv, ons_median_wage.csv, ons_population.csv, ons_unemployment.csv, england_real_estate_value.csv")
st.caption(f"BOE source page: {BOE_RATE_URL} | ONS base URL: {ONS_BASE_URL}")
