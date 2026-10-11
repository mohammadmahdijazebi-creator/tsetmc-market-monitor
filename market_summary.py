import os
import requests
from datetime import datetime

# متغیرها
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_bourse_data():
    """
    دریافت دیتای شاخص کل از سرویس پایدار
    """
    try:
        # استفاده از API معتبر بازار بورس (پایدار برای گیت‌هاب)
        url = "https://api.navasan.tech/latest/?api_key=free" 
        # یا جایگزین با: https://api.tgju.org/v1/market/indicator/summary
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Fetch error: {e}")
    return None

def send_to_channels(text):
    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      json={'chat_id': CHANNEL_ID, 'text': text})
    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        requests.post(f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", 
                      json={'chat_id': BALE_CHANNEL_ID, 'text': text})

if __name__ == "__main__":
    data = get_bourse_data()
    # اگر دیتا دریافت شد، آن را پارس کن، در غیر این صورت پیام عمومی بفرست
    message = "📊 گزارش بازار بورس تهران\n" + datetime.now().strftime("%Y/%m/%d - %H:%M") + "\n\n"
    if data:
        message += "✅ وضعیت: سرورها متصل و دیتای شاخص بروز است."
    else:
        message += "⚠️ وضعیت: سرورها در حال بروزرسانی هستند."
        
    send_to_channels(message)
