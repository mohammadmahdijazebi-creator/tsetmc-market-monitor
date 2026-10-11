import os
import requests
import json
from datetime import datetime

# متغیرها
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_tsetmc_data():
    """
    دریافت دیتای زنده از API اصلی سایت بورس (MarketWatch)
    این همان منبعی است که ربات‌های معتبر از آن استفاده می‌کنند.
    """
    try:
        # این آدرس API رسمی TSETMC است که دیتای لحظه‌ای را به صورت JSON می‌دهد
        url = "http://cdn.tsetmc.com/api/MarketData/GetMarketWatch"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://www.tsetmc.com/"
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Error: Received {r.status_code}")
    except Exception as e:
        print(f"Fetch exception: {e}")
    return None

def send_to_channels(text):
    if BOT_TOKEN and CHANNEL_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={'chat_id': CHANNEL_ID, 'text': text})
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        requests.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", json={'chat_id': BALE_CHANNEL_ID, 'text': text})

if __name__ == "__main__":
    data = get_tsetmc_data()
    
    if data:
        # اینجا می‌توانید دیتای شاخص یا نمادها را از دیکشنری data استخراج کنید
        # برای تست فقط اعلام می‌کنیم که دیتا دریافت شد
        message = "✅ وضعیت بازار: دیتا با موفقیت از سرور TSETMC دریافت شد."
    else:
        message = "⚠️ وضعیت: سرور TSETMC در حال حاضر پاسخگو نیست یا آی‌پی مسدود است."
        
    send_to_channels(message)
    print(message)
