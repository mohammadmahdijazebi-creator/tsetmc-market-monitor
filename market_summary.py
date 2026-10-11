import os
import requests
import json
from datetime import datetime

# تنظیمات مخفی (از محیط GitHub Actions خوانده می‌شود)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def fetch_market_data():
    """
    دریافت دیتای بازار از API پایدار
    این بخش جایگزین مهندسی معکوس‌های پیچیده است و در گیت‌هاب بلاک نمی‌شود.
    """
    try:
        # استفاده از API عمومی و سریع بازار
        url = "https://api.tgju.org/_/market/data/live-price-client"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def format_message(data):
    """
    تبدیل دیتای خام به گزارش زیبا و ایموجی‌دار
    """
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    if not data:
        return f"⚠️ گزارش بازار بورس تهران\n📅 {now}\n\nنکته: سرورهای دیتای بورس موقتاً در دسترس نیستند، در حال تلاش مجدد در ران بعدی..."

    # در اینجا می‌توانید پارس کردن دیتای JSON را اضافه کنید
    # مثال ساده برای نمایش وضعیت کلی
    msg = f"📊 گزارش لحظه‌ای بازار بورس تهران\n📅 {now}\n\n"
    msg += "✅ وضعیت: سرورها متصل هستند.\n"
    msg += "📈 شاخص کل و نمادهای پربازدید در حال تحلیل...\n\n"
    msg += "🆔 پایشگر هوشمند بورس"
    return msg

def send_to_telegram(msg):
    if not BOT_TOKEN or not CHANNEL_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_ID, 'text': msg}
    requests.post(url, json=payload)

def send_to_bale(msg):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID: return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': BALE_CHANNEL_ID, 'text': msg}
    requests.post(url, json=payload)

if __name__ == "__main__":
    # ۱. دریافت دیتا
    market_data = fetch_market_data()
    
    # ۲. فرمت کردن پیام
    report_text = format_message(market_data)
    
    # ۳. ارسال
    print(report_text)
    send_to_telegram(report_text)
    send_to_bale(report_text)
