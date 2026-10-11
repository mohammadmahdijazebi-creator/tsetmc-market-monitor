import os
import requests
import json
from datetime import datetime

# تنظیمات مخفی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def fetch_market_data():
    """
    دریافت دیتا با لاگ‌گیری دقیق برای پیدا کردن مشکل
    """
    try:
        # آدرس API (می‌توانیم در مرحله بعد این را با منابع دیگر عوض کنیم)
        url = "https://api.tgju.org/_/market/data/live-price-client"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=15)
        
        # اگر پاسخ ۲۰۲ نبود، کدهای خطا را پرینت کن تا در GitHub Actions ببینیم
        if r.status_code != 200:
            print(f"DEBUG: API returned status code {r.status_code}")
            return None
        
        data = r.json()
        if not data:
            print("DEBUG: API returned empty JSON.")
            return None
            
        return data

    except Exception as e:
        print(f"DEBUG: Exception during fetch: {e}")
        return None

def format_message(data):
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    if not data:
        # در صورت خطا، لاگ نشان می‌دهد چرا دریافت نکردیم
        return f"⚠️ هشدار: دیتای بورس دریافت نشد.\n📅 {now}\n\nبررسی کنید: خطای سرور یا تغییر آدرس API."

    # اگر دیتا وجود داشت، نمایش بده (ساختار دیتای دریافتی را در لاگ ببینید)
    return f"📊 گزارش بازار: دیتا با موفقیت دریافت شد.\n📅 {now}\n\nاطلاعات: {str(data)[:100]}..."

def send_message(msg):
    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': CHANNEL_ID, 'text': msg})
    
    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': BALE_CHANNEL_ID, 'text': msg})

if __name__ == "__main__":
    print("--- STARTING FETCH ---")
    market_data = fetch_market_data()
    report_text = format_message(market_data)
    print("--- FINAL REPORT ---")
    print(report_text)
    send_message(report_text)
