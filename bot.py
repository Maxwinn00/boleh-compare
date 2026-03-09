import os
import io
import requests
import threading 
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer 
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from pydantic import BaseModel

# ==========================================
# 1. YOUR CREDENTIALS
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ==========================================
# 2. THE GEMINI "BRAIN" SETUP (UPGRADED)
# ==========================================
client = genai.Client(api_key=GEMINI_API_KEY)

# NEW: Define the 10 fixed categories
class CategoryEnum(str, Enum):
    PRODUCE = "Fresh Produce"
    DAIRY = "Dairy & Chilled"
    PANTRY = "Pantry Staples"
    SNACKS = "Snacks & Confectionery"
    BEVERAGES = "Beverages"
    BABY = "Baby & Toddler"
    PERSONAL_CARE = "Personal Care"
    HOUSEHOLD = "Household & Cleaning"
    FROZEN = "Frozen Foods"
    MISC = "Miscellaneous"

class GroceryDeal(BaseModel):
    item_name: str
    price: float
    retailer: str
    location: str
    remarks: str  
    category: CategoryEnum  # NEW: Instructs Gemini to categorize the item

def extract_grocery_data(ai_inputs):
    # UPGRADED PROMPT: Added categorization instruction
    prompt = """
    You are a data extraction bot for a Malaysian grocery app. 
    Extract ALL the grocery deals you can find in the provided image or text.
    - Format item_name simply (e.g., 'Milo UHT 1L'). 
    - If location isn't specified, output 'Unknown'. 
    - If there is no price, output 0.0.
    - Use the 'remarks' field for promos like 'Buy 1 Free 1', 'Valid till Friday', or 'Must buy 2'. If none, output 'None'.
    - Categorize each item strictly into one of the provided categories.
    """
    
    final_contents = [prompt] + ai_inputs
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=final_contents,
        config={
            'response_mime_type': 'application/json',
            'response_schema': list[GroceryDeal], 
        }
    )
    return response.text

# ==========================================
# 3. THE SUPABASE DATABASE INJECTOR
# ==========================================
def save_to_supabase(deals_json_list):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/grocery_prices"
    
    # Because Gemini's JSON keys now match your DB columns perfectly (including 'category'),
    # we can push the raw JSON list directly to Supabase.
    response = requests.post(url, headers=headers, data=deals_json_list)
    return response.status_code in [200, 201]

# ==========================================
# 4. TELEGRAM MESSAGE HANDLER
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🇲🇾 BolehCompare Bot is awake! Send me a flyer, and I'll extract and categorize ALL the deals.")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👀 Scanning for deals and categorizing...")
    
    try:
        ai_inputs = []
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            byte_array = await photo_file.download_as_bytearray()
            image = Image.open(io.BytesIO(byte_array))
            ai_inputs.append(image)
            if update.message.caption:
                ai_inputs.append(f"Context from user: {update.message.caption}")
        else:
            ai_inputs.append(update.message.text)

        # 1. Extract the list of deals
        clean_json_list = extract_grocery_data(ai_inputs)
        
        # 2. Bulk save to Supabase
        success = save_to_supabase(clean_json_list)
        
        if success:
            await update.message.reply_text(f"✅ Extracted, categorized, and saved!\n{clean_json_list}")
        else:
            await update.message.reply_text("❌ Failed to save to database.")
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ Oops, something went wrong: {e}")

# ==========================================
# 4.5 THE "DUMMY SERVER" HACK FOR RENDER
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is awake and listening!")

def keep_alive():
    # Render assigns a PORT dynamically, or we default to 8080
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# ==========================================
# 5. START THE BOT
# ==========================================
if __name__ == '__main__':
    print("Starting BolehCompare Bot (Multi-Item Vision & Categorization Enabled)...")
    
    # Start the dummy server in the background
    threading.Thread(target=keep_alive, daemon=True).start()
    
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_input))
    
    print("Bot is listening! Send it a photo or a text on Telegram.")
    app.run_polling()