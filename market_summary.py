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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_with_retry(url, retries=3, delay=3):
    """Fetches URL with retry logic for network instability."""
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {url}: {e}")
        time.sleep(delay)
    return None

def fetch_tsetmc_overview():
    """Fetches general market overview from TSETMC with retry."""
    url = "https://cdn.tsetmc.com/api/MarketData/GetMarketOverview"
    data = fetch_with_retry(url)
    if data:
        overview = data.get('marketOverview', {})
        return {
            'index_val': overview.get('indexLastValue', 0),
            'index_change': overview.get('indexChange', 0),
            'equal_index_val': overview.get('indexEqualWeightLastValue', 0),
            'equal_index_change': overview.get('indexEqualWeightChange', 0),
            'market_val': overview.get('marketValue', 0),
            'trade_vol': overview.get('marketActivityVolume', 0),
            'trade_val': overview.get('marketActivityValue', 0)
        }
    return None

def fetch_client_type_summary():
    """Fetches real/institutional money flow from TSETMC with retry."""
    url = "https://cdn.tsetmc.com/api/ClientType/GetClientTypeAll"
    data = fetch_with_retry(url)
    if data:
        items = data.get('clientType', [])
        stock_real_money = 0.0
        fixed_income_real_money = 0.0
        
        for item in items:
            rec_real_buy = item.get('recValBuyReal', 0)
            rec_real_sell = item.get('recValSellReal', 0)
            net_flow = rec_real_buy - rec_real_sell
            
            market_type = item.get('marketType', '')
            if 'درآمد ثابت' in market_type or 'صندوق' in market_type:
                fixed_income_real_money += net_flow
            else:
                stock_real_money += net_flow
                
        return {
            'stock_real_money': stock_real_money / 10_000_000_000,
            'fixed_income_real_money': fixed_income_real_money / 10_000_000_000
        }
    return None

def format_change(change_val):
    if change_val > 0:
        return f"+{change_val:,.0f}"
    elif change_val < 0:
        return f"{change_val:,.0f}"
    else:
        return "0"

def generate_report():
    overview = fetch_tsetmc_overview()
    client_flow = fetch_client_type_summary()
    
    if not overview:
        return "⚠️ در حال حاضر ارتباط با سرور بورس برقرار نشد (تلاش‌های مجدد موفق نبود)."
        
    date_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    idx_val = overview['index_val']
    idx_chg = overview['index_change']
    eq_val = overview['equal_index_val']
    eq_chg = overview['equal_index_change']
    
    report = f"📊 گزارش لحظه‌ای بازار بورس تهران\n"
    report += f"📅 {date_str}\n\n"
    
    report += f"📈 شاخص کل: {idx_val:,.0f}\n"
    report += f"🔹 تغییرات: {format_change(idx_chg)}\n\n"
    
    report += f"📊 شاخص هم‌وزن: {eq_val:,.0f}\n"
    report += f"🔹 تغییرات: {format_change(eq_chg)}\n\n"
    
    report += f"💰 ارزش معاملات: {overview['trade_val'] / 10_000_000_000:,.1f} میلیارد تومان\n"
    report += f"🔄 حجم معاملات: {overview['trade_vol'] / 1_000_000_000:,.2f} میلیارد برگه سهم\n\n"
    
    if client_flow:
        stk_flow = client_flow['stock_real_money']
        fi_flow = client_flow['fixed_income_real_money']
        
        stk_icon = "🟢 ورود" if stk_flow >= 0 else "🔴 خروج"
        fi_icon = "🟢 ورود" if fi_flow >= 0 else "🔴 خروج"
        
        report += f"💸 ورود/خروج پول حقیقی:\n"
        report += f"▫️ سهام و حق تقدم: {stk_icon} {abs(stk_flow):,.1f} میلیارد تومان\n"
        report += f"▫️ صندوق‌های درآمد ثابت: {fi_icon} {abs(fi_flow):,.1f} میلیارد تومان\n"

    report += "\n🆔 @bourse_monitor"
    return report

def send_telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': text
        # بدون parse_mode برای جلوگیری از خطای کاراکترهای خاص
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
