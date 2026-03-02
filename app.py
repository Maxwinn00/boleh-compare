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

# 3. Search Header
search_query = st.text_input("🔍 What are you looking for today?", placeholder="e.g., Milo, Maggi, Eggs")

if not df.empty:
    if search_query:
        # Filtering logic
        filtered_df = df[df["item_name"].str.contains(search_query, case=False, na=False)]
        
        if not filtered_df.empty:
            # --- NEW: VISUAL METRICS ---
            best_deal = filtered_df.loc[filtered_df['price'].idxmin()]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lowest Price", f"RM {best_deal['price']:.2f}")
            with col2:
                st.metric("Best Retailer", best_deal['retailer'])
            with col3:
                st.metric("Total Deals Found", len(filtered_df))

            st.divider()

            # --- NEW: INTERACTIVE CHART ---
            st.subheader(f"Price Comparison: {search_query}")
            # Prepare data for chart: Group by retailer and get the lowest price there
            chart_data = filtered_df.groupby('retailer')['price'].min().sort_values()
            st.bar_chart(chart_data)

            # --- TABLE VIEW ---
            st.subheader("All Deals")
            display_df = filtered_df[['item_name', 'price', 'remarks', 'retailer', 'location', 'created_at']]
            st.dataframe(display_df.sort_values(by="price"), use_container_width=True, hide_index=True)
            
        else:
            st.warning(f"No deals found for '{search_query}'. Try another item!")
    else:
        st.info("👋 Welcome! Type a product name above to see the magic.")
        st.subheader("Recent Community Submissions")
        st.table(df.sort_values(by="created_at", ascending=False).head(5)[['item_name', 'price', 'retailer']])
else:
    st.error("Could not connect to database. Check your Supabase keys!")