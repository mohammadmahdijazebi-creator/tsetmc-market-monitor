import os
import time
import requests
from datetime import datetime

# --- CONFIGURATION & ENV VARS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def fetch_market_watch():
    """
    Fetches raw market watch data from old.tsetmc.com which is accessible internationally.
    """
    url = "http://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200 and len(r.text) > 1000:
                return r.text
        except Exception as e:
            print(f"MarketWatch attempt {attempt+1} failed: {e}")
        time.sleep(2)
    return None

def parse_market_data(raw_text):
    """
    Parses market overview and real/legal money flow from MarketWatch data.
    """
    try:
        parts = raw_text.split('@')
        if len(parts) < 3:
            return None
        
        # parts[0]: Market summary & Indices
        # Format often contains index values and market trade status
        overview_part = parts[0]
        rows = overview_part.split(';')
        
        index_val = 0.0
        index_change = 0.0
        trade_val = 0.0
        trade_vol = 0.0
        
        for row in rows:
            cols = row.split(',')
            if len(cols) >= 2:
                # Typical old TSETMC indicators
                if cols[0] == '1': # Index entry
                    try:
                        index_val = float(cols[1])
                        index_change = float(cols[2])
                    except:
                        pass
        
        # parts[2]: Stocks data
        # cols: 0:id, 1:isin, 2:symbol, 3:name, ..., 9:vol, 10:val, 11:last, 12:close
        stock_rows = parts[2].split(';')
        
        # Calculate totals from visible stocks
        total_value = 0.0
        total_vol = 0.0
        for s in stock_rows:
            cols = s.split(',')
            if len(cols) > 10:
                try:
                    vol = float(cols[9])
                    val = float(cols[10])
                    total_vol += vol
                    total_value += val
                except:
                    pass
        
        if trade_val == 0.0 and total_value > 0:
            trade_val = total_value
        if trade_vol == 0.0 and total_vol > 0:
            trade_vol = total_vol

        # parts[4] or client type data if present
        # In MarketWatchPlus: parts[4] contains client type data (Real/Institutional)
        stock_real_flow = 0.0
        fixed_income_real_flow = 0.0

        if len(parts) >= 5:
            client_rows = parts[4].split(';')
            for crow in client_rows:
                ccols = crow.split(',')
                # ccols: 0:id, 1:buy_count_real, 2:buy_count_legal, 3:sell_count_real, 4:sell_count_legal,
                # 5:buy_vol_real, 6:buy_vol_legal, 7:sell_vol_real, 8:sell_vol_legal, 
                # 9:buy_val_real, 10:buy_val_legal, 11:sell_val_real, 12:sell_val_legal
                if len(ccols) >= 13:
                    try:
                        buy_val_real = float(ccols[9])
                        sell_val_real = float(ccols[11])
                        net_real = buy_val_real - sell_val_real
                        stock_real_flow += net_real
                    except:
                        pass

        return {
            'index_val': index_val,
            'index_change': index_change,
            'trade_val': trade_val,
            'trade_vol': trade_vol,
            'stock_real_flow': stock_real_flow / 10_000_000_000, # to Billion Tomans
        }
    except Exception as e:
        print(f"Parsing error: {e}")
        return None

def format_change(change_val):
    if change_val > 0:
        return f"+{change_val:,.0f}"
    elif change_val < 0:
        return f"{change_val:,.0f}"
    else:
        return "0"

def generate_report():
    raw_data = fetch_market_watch()
    if not raw_data:
        return "⚠️ در حال حاضر ارتباط با سرورهای بورس امکان‌پذیر نیست."
        
    data = parse_market_data(raw_data)
    if not data:
        return "⚠️ خطا در پردازش اطلاعات بورس."
        
    date_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    report = f"📊 گزارش لحظه‌ای بازار بورس تهران\n"
    report += f"📅 {date_str}\n\n"
    
    if data['index_val'] > 0:
        report += f"📈 شاخص کل: {data['index_val']:,.0f}\n"
        report += f"🔹 تغییرات: {format_change(data['index_change'])}\n\n"
    
    if data['trade_val'] > 0:
        report += f"💰 ارزش معاملات خرد: {data['trade_val'] / 10_000_000_000:,.1f} میلیارد تومان\n"
        report += f"🔄 حجم معاملات: {data['trade_vol'] / 1_000_000_000:,.2f} میلیارد برگه سهم\n\n"
    
    flow = data['stock_real_flow']
    icon = "🟢 ورود" if flow >= 0 else "🔴 خروج"
    report += f"💸 ورود/خروج پول حقیقی (سهام و حق‌تقدم):\n"
    report += f"▫️ {icon} {abs(flow):,.1f} میلیارد تومان\n"
    
    report += "\n🆔 پایشگر هوشمند بورس"
    return report

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': text
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram response:", r.status_code, r.text)
    except Exception as e:
        print("Telegram error:", e)

def send_bale(text):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        print("Bale credentials missing.")
        return
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': BALE_CHANNEL_ID,
        'text': text
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Bale response:", r.status_code, r.text)
    except Exception as e:
        print("Bale error:", e)

if __name__ == "__main__":
    msg = generate_report()
    print("--- REPORT MESSAGE ---")
    print(msg)
    send_telegram(msg)
    send_bale(msg)
