import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_live_market_data():
    """
    دریافت دیتای زنده و واقعی بازار از API پایدار
    """
    try:
        # استفاده از سرویس دیتای مالی زنده
        url = "https://api.navasan.tech/latest/?api_key=free"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def send_to_channels(text):
    success = False
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
        except Exception as e:
            print(f"Telegram exception: {e}")

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
        except Exception as e:
            print(f"Bale exception: {e}")
            
    return success

if __name__ == "__main__":
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    # دریافت دیتای زنده
    market_data = get_live_market_data()
    
    if market_data:
        # استخراج نرخ‌های کلیدی از پاسخ API
        try:
            usd_price = market_data.get('usd', {}).get('value', 'نامشخص')
            eur_price = market_data.get('eur', {}).get('value', 'نامشخص')
            gbp_price = market_data.get('gbp', {}).get('value', 'نامشخص')
            
            message = (
                f"📊 *گزارش زنده بازار مالی ایران*\n"
                f"📅 تاریخ: `{now}`\n\n"
                f"💵 *نرخ دلار:* `{usd_price}` تومان\n"
                f"💶 *نرخ یورو:* `{eur_price}` تومان\n"
                f"💷 *نرخ پوند:* `{gbp_price}` تومان\n\n"
                f"🟢 _بروزرسانی خودکار از سامانه پایش_"
            )
        except Exception as parse_err:
            print(f"Parsing error: {parse_err}")
            message = f"📊 *گزارش بازار*\n📅 `{now}`\n\n⚠️ خطا در پردازش ساختار دیتای دریافتی."
    else:
        message = (
            f"📊 *گزارش بازار مالی تهران*\n"
            f"📅 `{now}`\n\n"
            f"⚠️ موقتاً دیتایی از سرور دریافت نشد، در حال تلاش مجدد در ران بعدی..."
        )
    
    print("Executing market summary dispatch with live data...")
    send_to_channels(message)
