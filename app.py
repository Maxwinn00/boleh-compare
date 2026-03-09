import streamlit as st
import pandas as pd
import requests

# 1. Page Configuration
st.set_page_config(page_title="BolehCompare", page_icon="🇲🇾", layout="wide")
st.title("🇲🇾 BolehCompare")
st.markdown("### *Smart Grocery Price Tracking for Malaysians*")

# 2. Database Connection (Secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_data(ttl=600) # Cache data for 10 mins to keep it fast
def load_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{SUPABASE_URL}/rest/v1/grocery_prices?select=*"
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        df = pd.DataFrame(response.json())
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
        return df
    return pd.DataFrame()

df = load_data()

# Fill older database entries that have no category with "Miscellaneous"
if not df.empty and 'category' in df.columns:
    df['category'] = df['category'].fillna('Miscellaneous')
elif not df.empty:
    df['category'] = 'Miscellaneous'

# 3. Search Header
search_query = st.text_input("🔍 What are you looking for today?", placeholder="e.g., Milo, Maggi, Eggs")

if not df.empty:
    # Define the Aisle Tabs
    categories = [
        "All Deals", "Fresh Produce", "Dairy & Chilled", "Pantry Staples", 
        "Snacks & Confectionery", "Beverages", "Baby & Toddler", 
        "Personal Care", "Household & Cleaning", "Frozen Foods", "Miscellaneous"
    ]

    tabs = st.tabs(categories)

    for i, tab in enumerate(tabs):
        with tab:
            current_category = categories[i]

            # Step 1: Filter by Search Query (if any)
            if search_query:
                tab_df = df[df["item_name"].str.contains(search_query, case=False, na=False)]
            else:
                tab_df = df

            # Step 2: Filter by Category Tab (unless we are on "All Deals")
            if current_category != "All Deals":
                tab_df = tab_df[tab_df["category"] == current_category]

            # Step 3: Display the Data
            if not tab_df.empty:
                if search_query and current_category == "All Deals":
                    # Show the visual metrics and chart only on the "All Deals" tab when searching
                    best_deal = tab_df.loc[tab_df['price'].idxmin()]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Lowest Price", f"RM {best_deal['price']:.2f}")
                    with col2:
                        st.metric("Best Retailer", best_deal['retailer'])
                    with col3:
                        st.metric("Total Deals Found", len(tab_df))

                    st.divider()

                    chart_data = tab_df.groupby('retailer')['price'].min().sort_values()
                    if len(chart_data) > 1:
                        st.bar_chart(chart_data)

                st.dataframe(
                    tab_df[['item_name', 'price', 'category', 'retailer', 'location', 'remarks', 'created_at']].sort_values(by="price"), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info(f"No items found in {current_category}.")
else:
    st.error("Could not connect to database. Check your Supabase keys!")