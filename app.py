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
st.write(
    """
This dashboard explores UK housing prices using:
- HM Land Registry
- EPC floor-area data
- Guardian news sentiment
- Economic indicators
"""
)

# ---------------------------------------------------
# API KEYS
# ---------------------------------------------------
guardian_key = "f57dc3df-6bff-431a-aeaa-84da13200f71"
epc_key = "49047b27453a21db42d8e69ad07267ed00314ae0"

# ---------------------------------------------------
# GUARDIAN API FUNCTION
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
        st.error(f"Guardian API error: {response.status_code}")
        return pd.DataFrame()

    data = response.json()
    results = data["response"]["results"]

    rows = []

    for item in results:
        headline = item["webTitle"]
        text = item.get("fields", {}).get("trailText", "")
        date = item["webPublicationDate"][:10]
        url_link = item["webUrl"]

        sentiment = TextBlob(headline + " " + text).sentiment.polarity

        rows.append({
            "date": date,
            "headline": headline,
            "sentiment": sentiment,
            "url": url_link
        })

    return pd.DataFrame(rows)

# ---------------------------------------------------
# EPC API FUNCTION
# ---------------------------------------------------
def get_epc_data(postcode):
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"

    headers = {
        "Authorization": epc_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error(f"EPC API error: {response.status_code}")
        return pd.DataFrame()

    try:
        data = response.json()

        rows = data.get("rows", [])

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)

    except:
        st.error("Could not read EPC response.")
        return pd.DataFrame()

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
st.sidebar.header("Controls")

section = st.sidebar.radio(
    "Choose Section",
    ["Guardian Sentiment", "EPC Property Size", "Combined Demo"]
)

# ---------------------------------------------------
# GUARDIAN SECTION
# ---------------------------------------------------
if section == "Guardian Sentiment":

    st.subheader("Guardian Housing News Sentiment")

    query = st.text_input("Search term", "UK house prices")
    from_date = st.date_input("From date", pd.to_datetime("2023-01-01"))
    to_date = st.date_input("To date", pd.to_datetime("2024-12-31"))

    if st.button("Load Guardian Data"):

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

    
else:
    st.subheader("Combined Example Dashboard")

    url = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"

    sales = pd.read_csv(url)

    st.write("Raw Data")
    st.dataframe(sales.head())
