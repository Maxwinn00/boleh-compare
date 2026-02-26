import streamlit as st
import pandas as pd
import requests # We use this built-in tool instead of the supabase library!

# 1. Page Configuration
st.set_page_config(page_title="BolehCompare", page_icon="🇲🇾")
st.title("🇲🇾 BolehCompare: Grocery Price Tracker")
st.write("Find the cheapest groceries tracked by the community.")

# 2. Database Connection (Using Streamlit Secrets Vault)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# 3. Fetch Data from Supabase directly via its API
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
        
        # --- THE FIX ---
        # Convert the timestamp string into a clean Date format
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
        
        return df
    else:
        return pd.DataFrame() # Return empty dataframe if no data

df = load_data()

# 4. The Search Interface
search_query = st.text_input("🔍 What are you looking for?", placeholder="e.g., Milo, Maggi, Milk")

if not df.empty:
    if search_query:
        # Filter the dataframe (case-insensitive)
        filtered_df = df[df["item_name"].str.contains(search_query, case=False, na=False)]
        
        if not filtered_df.empty:
            filtered_df = filtered_df.sort_values(by="price", ascending=True)
            st.success(f"Found {len(filtered_df)} deals for '{search_query}'!")
            
            # Select specific columns to show to the user cleanly
            display_df = filtered_df[['item_name', 'price', 'remarks', 'retailer', 'location', 'created_at']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No deals found! Time to snap some photos.")
    else:
        st.subheader("Latest Deals")
        display_df = df[['item_name', 'price', 'remarks', 'retailer', 'location', 'created_at']]
        st.dataframe(display_df.sort_values(by="created_at", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("The database is currently empty. Start submitting deals via the bot!")