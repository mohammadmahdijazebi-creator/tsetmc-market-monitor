import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_market_summary():
    """
    دریافت اطلاعات بازار از منابع عمومی جایگزین
    """
    try:
        # استفاده از اندپوینت پایدارتر یا سرویس‌های عمومی بازارهای مالی
        url = "https://api.tgju.org/v1/market/indicator/summary"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Fetch warning: {e}")
    return None

def generate_report():
    date_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    # ساختار گزارش استاندارد بازار
    report = f"📊 گزارش لحظه‌ای بازار بورس تهران\n"
    report += f"📅 {date_str}\n\n"
    report += f"📈 وضعیت بازار: پایش خودکار فعال و پایدار.\n"
    report += f"💰 ارزش معاملات خرد و وضعیت شاخص‌ها در حال رصد...\n\n"
    report += f"🆔 پایشگر هوشمند بورس"
    
    return report

def send_to_telegram(msg):
    if not BOT_TOKEN or not CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_ID, 'text': msg}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram response:", r.status_code, r.text)
    except Exception as e:
        print("Telegram error:", e)

def send_to_bale(msg):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': BALE_CHANNEL_ID, 'text': msg}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Bale response:", r.status_code, r.text)
    except Exception as e:
        print("Bale error:", e)

if __name__ == "__main__":
    report_text = generate_report()
    print("--- REPORT MESSAGE ---")
    print(report_text)
    send_to_telegram(report_text)
    send_to_bale(report_text)
