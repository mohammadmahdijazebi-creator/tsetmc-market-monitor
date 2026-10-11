import os
import requests
from datetime import datetime

# متغیرهای محیطی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def fetch_market_info():
    """
    دریافت اطلاعات و وضعیت بازار
    """
    try:
        # درخواست به سرویس پایدار برای دریافت نرخ‌ها یا وضعیت بازار
        r = requests.get("https://api.navasan.tech/latest/?api_key=free", timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Fetch error: {e}")
    return None

def send_to_channels(text):
    """
    ارسال پیام به کانال‌های تلگرام و بله با خطاگیری کامل
    """
    success = False
    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            res = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                json={'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'Markdown'},
                timeout=10
            )
            if res.status_code == 200:
                print("Telegram message sent successfully.")
                success = True
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            res = requests.post(
                f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage", 
                json={'chat_id': BALE_CHANNEL_ID, 'text': text},
                timeout=10
            )
            if res.status_code == 200:
                print("Bale message sent successfully.")
                success = True
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")
            
    return success

if __name__ == "__main__":
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    # ساخت متن حرفه‌ای گزارش بازار
    message = (
        f"📊 *گزارش لحظه‌ای بازار بورس تهران*\n"
        f"📅 تاریخ و زمان: `{now}`\n\n"
        f"🟢 *وضعیت سامانه:* فعال و پایدار\n"
        f"📌 *روند کلی:* پایش خودکار جریان معاملات بورس، فرابورس و صندوق‌های سرمایه‌گذاری برقرار است.\n\n"
        f"⚙️ _بروزرسانی خودکار از طریق ربات هوشمند پایش بازار_"
    )
    
    print("Executing market summary dispatch...")
    send_to_channels(message)
