import os
import time
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def fetch_market_watch():
    # استفاده از چند روش و لینک جایگزین برای دور زدن محدودیت IP خارج از کشور
    urls = [
        "http://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx",
        "http://www.tsetmc.com/tsev2/data/MarketWatchPlus.aspx"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache'
    }

    for url in urls:
        for attempt in range(2):
            try:
                print(f"Trying to fetch from {url} (Attempt {attempt+1})...")
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and len(r.text) > 500:
                    print("Successfully fetched market data!")
                    return r.text
            except Exception as e:
                print(f"Failed {url}: {e}")
            time.sleep(2)
    return None

def parse_market_data(raw_text):
    try:
        parts = raw_text.split('@')
        if len(parts) < 1:
            return None
        
        overview_part = parts[0]
        rows = overview_part.split(';')
        
        index_val = 0.0
        index_change = 0.0
        
        for row in rows:
            cols = row.split(',')
            if len(cols) >= 3 and cols[0] == '1':
                try:
                    index_val = float(cols[2]) # مقدار شاخص
                    index_change = float(cols[4]) # تغییر شاخص
                except:
                    pass

        return {
            'index_val': index_val,
            'index_change': index_change,
            'trade_val': 14500.0, # مقدار پیش‌فرض یا محاسباتی در صورت نیاز
            'trade_vol': 2100.0,
            'stock_real_flow': -120.0 # نمونه
        }
    except Exception as e:
        print(f"Parsing error: {e}")
        return None

def generate_report():
    raw_data = fetch_market_watch()
    if not raw_data:
        # پیام پیش‌فرض برای اینکه ربات در روزهای تعطیل یا قطع ارتباط خالی نفرستد
        return "📊 گزارش بازار بورس تهران\n📅 " + datetime.now().strftime("%Y/%m/%d - %H:%M") + "\n\n⚠️ در حال حاضر سرور بورس به درخواست‌های خارج از کشور پاسخ نمی‌دهد (محدودیت IP گیت‌هاب).\n\n🆔 پایشگر هوشمند بورس"
        
    data = parse_market_data(raw_data)
    if not data:
        return "⚠️ خطا در پردازش اطلاعات بازار."
        
    date_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
    report = f"📊 گزارش لحظه‌ای بازار بورس تهران\n📅 {date_str}\n\n"
    if data['index_val'] > 0:
        report += f"📈 شاخص کل: {data['index_val']:,.0f}\n"
        report += f"🔹 تغییرات: {data['index_change']:,.0f}\n\n"
    report += "🆔 پایشگر هوشمند بورس"
    return report

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

def send_bale(text):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': BALE_CHANNEL_ID, 'text': text}, timeout=10)
    except Exception as e:
        print("Bale error:", e)

if __name__ == "__main__":
    msg = generate_report()
    print("--- REPORT MESSAGE ---")
    print(msg)
    send_telegram(msg)
    send_bale(msg)
