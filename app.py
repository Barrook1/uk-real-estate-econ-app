import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from textblob import TextBlob

st.set_page_config(page_title="UK Real Estate & Economy Dashboard", layout="wide")

st.title("UK Real Estate Price Changes and Economic Indicators")

st.write("""
This app explores how UK property prices change over time and compares them with
unemployment, wages, interest rates, population growth, and housing news sentiment.
""")

guardian_key = st.secrets["f57dc3df-6bff-431a-aeaa-84da13200f71"]
epc_key = st.secrets["49047b27453a21db42d8e69ad07267ed00314ae0"]

# ----------------------------
# Example: Guardian API
# ----------------------------

def get_guardian_articles(query, from_date, to_date):
    url = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "from-date": from_date,
        "to-date": to_date,
        "api-key": guardian_key,
        "show-fields": "headline,trailText",
        "page-size": 50,
    }

    response = requests.get(url, params=params)
    data = response.json()

    articles = []
    for item in data["response"]["results"]:
        headline = item["webTitle"]
        text = item.get("fields", {}).get("trailText", "")
        sentiment = TextBlob(headline + " " + text).sentiment.polarity

        articles.append({
            "date": item["webPublicationDate"][:10],
            "headline": headline,
            "sentiment": sentiment,
            "url": item["webUrl"]
        })

    return pd.DataFrame(articles)

st.sidebar.header("Controls")

query = st.sidebar.text_input("Guardian search term", "UK house prices")
from_date = st.sidebar.date_input("From date", pd.to_datetime("2023-01-01"))
to_date = st.sidebar.date_input("To date", pd.to_datetime("2024-12-31"))

if st.sidebar.button("Load Guardian Sentiment"):
    guardian_df = get_guardian_articles(str(query), str(from_date), str(to_date))

    st.subheader("Guardian Housing News Sentiment")
    st.dataframe(guardian_df)

    if not guardian_df.empty:
        guardian_df["date"] = pd.to_datetime(guardian_df["date"])
        monthly_sentiment = guardian_df.groupby(
            guardian_df["date"].dt.to_period("M")
        )["sentiment"].mean().reset_index()

        monthly_sentiment["date"] = monthly_sentiment["date"].astype(str)

        fig = px.line(
            monthly_sentiment,
            x="date",
            y="sentiment",
            title="Average Monthly Guardian Sentiment on UK House Prices"
        )
        st.plotly_chart(fig, use_container_width=True)
# ----------------------------
# EPC API Section
# ----------------------------

st.subheader("EPC Property Size Data")

postcode = st.text_input("Enter a UK postcode", "SW1A 1AA")

def get_epc_data(postcode):
    url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={postcode}"

    headers = {
        "Authorization": epc_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error: {response.status_code}")
        return None

if st.button("Load EPC Data"):
    epc_data = get_epc_data(postcode)

    if epc_data:
        st.write(epc_data)
# ----------------------------
# Placeholder: property data
# ----------------------------
st.subheader("EPC API Connection Test")

if st.button("Test EPC Key"):
    st.success("EPC key loaded successfully.")
    st.write("First 4 characters:", epc_key[:4] + "****")


st.subheader("Property Price Data")

st.info("""
Next step: import HM Land Registry Price Paid Data, clean it, group it by month and location,
then calculate average sale price.
""")

example_data = pd.DataFrame({
    "year": [2020, 2021, 2022, 2023, 2024],
    "average_price": [250000, 270000, 292000, 285000, 300000],
    "unemployment_rate": [4.5, 4.6, 3.8, 4.1, 4.4],
    "bank_rate": [0.1, 0.1, 3.5, 5.25, 5.0]
})

fig = px.line(
    example_data,
    x="year",
    y="average_price",
    title="Example: Average UK Property Sale Price"
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Economic Indicators")
st.dataframe(example_data)
