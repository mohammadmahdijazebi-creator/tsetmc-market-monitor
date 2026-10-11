import os
import requests
from datetime import datetime

# تنظیمات از GitHub Secrets
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_market_data():
    """
    استفاده از منبع جایگزین ره‌آورد/فای‌پی‌یران که از خارج کشور باز است
    """
    try:
        # این آدرس دیتای کلی بازار را به صورت JSON ارائه می‌دهد
        url = "https://api.tgju.org/v1/market/stock/summary" 
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def generate_report():
    data = get_market_data()
    date_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    # اگر دیتای زنده در دسترس نبود، پیام خطا ندهیم، دیتای ذخیره شده یا پیام جایگزین بفرستیم
    if not data or 'data' not in data:
        return f"📊 گزارش بازار بورس تهران\n📅 {date_str}\n\n⚠️ سرورهای دیتای بورس موقتاً در دسترس نیستند.\n🆔 @MarketSummary"

    # استخراج مقادیر (نام فیلدها در APIهای عمومی معمولاً اینگونه است)
    main_index = data['data'].get('index_last_value', "---")
    index_change = data['data'].get('index_change', "---")
    market_value = data['data'].get('market_value', "---") # ارزش معاملات خرد
    
    report =  f"📊 **گزارش لحظه‌ای بازار بورس**\n"
    report += f"📅 {date_str}\n\n"
    report += f"📈 شاخص کل: {main_index}\n"
    report += f"🔹 تغییرات: {index_change}\n"
    report += f"💰 ارزش معاملات خرد: {market_value} همت\n\n"
    report += f"🆔 پایشگر هوشمند بورس"
    return report

def send_to_telegram(msg):
    if not BOT_TOKEN or not CHANNEL_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # نکته: آیدی کانال باید حتما با -100 شروع شود
    requests.post(url, json={'chat_id': CHANNEL_ID, 'text': msg, 'parse_mode': 'Markdown'})

def send_to_bale(msg):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID: return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': BALE_CHANNEL_ID, 'text': msg})

if __name__ == "__main__":
    report_text = generate_report()
    print(report_text)
    send_to_telegram(report_text)
    send_to_bale(report_text)
