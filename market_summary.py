import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_market_data():
    # تلاش اول: اتصال مستقیم به TSETMC با هدرهای کامل
    urls = [
        "http://cdn.tsetmc.com/api/MarketData/GetMarketWatch",
        "https://cdn.tsetmc.com/api/MarketData/GetMarketWatch",
        # استفاده از پروکسی عمومی رایگان برای دورزدن تحریم/مسدودی آی‌پی گیت‌هاب
        "https://api.allorigins.win/raw?url=http://cdn.tsetmc.com/api/MarketData/GetMarketWatch"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://www.tsetmc.com/"
    }

    for url in urls:
        try:
            print(f"Trying to fetch from: {url[:40]}...")
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                print("Successfully connected!")
                return r.json()
        except Exception as e:
            print(f"Failed with {url[:30]}: {e}")
            continue
            
    return None

def send_to_channels(text):
    if BOT_TOKEN and CHANNEL_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={'chat_id': CHANNEL_ID, 'text': text})
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        requests.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", json={'chat_id': BALE_CHANNEL_ID, 'text': text})

if __name__ == "__main__":
    data = get_market_data()
    
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    if data:
        message = f"📊 گزارش بازار بورس تهران\n📅 {now}\n\n✅ اتصال به سرور بورس برقرار و دیتا دریافت شد."
    else:
        message = f"📊 گزارش بازار بورس تهران\n📅 {now}\n\n⚠️ سرورهای بورس از روی گیت‌هاب در دسترس نیستند (محدودیت آی‌پی)."
        
    send_to_channels(message)
    print(message)
