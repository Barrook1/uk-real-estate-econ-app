
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
BASE_URL = "https://raw.githubusercontent.com/Barrook1/uk-real-estate-econ-app/main/data/"

LAND_URL = "https://drive.google.com/uc?export=download&id=1fuUW5ZrT72KA1uvBMhBiAO1h1dvQACaE"
BANK_URL = "data/bankrate.csv"
WAGE_URL = "data/ons_median_wage.csv"
POP_URL = "data/ons_population.csv"
UNEMP_URL = "data/ons_unemployment.csv
BANK_URL = "bankrate.csv"
WAGE_URL = "ons_median_wage.csv"
POP_URL = "ons_population.csv"
UNEMP_URL = "ons_unemployment.csv"

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
