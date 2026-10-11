import os
import sys
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_options_data():
    """
    دریافت داده‌های دیده‌بان اختیار معامله از درگاه رسمی بورس تهران (بدون مسدودی خارج کشور)
    """
    # درگاه رسمی بورس تهران که دسترسی سرورهای خارجی به آن باز است
    url = "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchOption/fa"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tse.ir",
        "Referer": "https://tse.ir/"
    }

    try:
        print(f"Connecting to official gateway: {url} ...")
        res = requests.get(url, headers=headers, timeout=25)
        
        if res.status_code == 200:
            data = res.json()
            
            # درگاه ممکن است مستقیماً لیست را در روت یا در کلید data بگذارد
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("data") or data.get("marketWatchOption") or data.get("items") or []

            rows = []
            for item in items:
                # خواندن نام نماد
                symbol = item.get("lVal18AFC") or item.get("symbol") or item.get("nemad") or ""
                symbol = str(symbol).strip()
                if not symbol:
                    continue

                # حجم، ارزش و موقعیت باز
                volume = float(item.get("qTotTran5J") or item.get("tedadMoamele") or item.get("hajmMoamele") or item.get("volume") or 0)
                value = float(item.get("qTotCap") or item.get("arzeshMoamele") or item.get("value") or 0)
                oi = float(item.get("notOPnIntrst") or item.get("moqeiatBaz") or item.get("openInterest") or item.get("oi") or 0)

                rows.append({
                    "symbol": symbol,
                    "volume": volume,
                    "value": value,
                    "oi": oi
                })

            df = pd.DataFrame(rows)
            if not df.empty:
                print(f"Successfully retrieved {len(df)} contracts.")
                return df
            else:
                print("Response received but no contracts found.")
        else:
            print(f"Gateway returned status code: {res.status_code}")
            
    except Exception as e:
        print(f"Error fetching from official gateway: {e}")

    return None

def format_number(val):
    """فرمت‌دهی اعداد به صورت خلاصه و استاندارد"""
    try:
        val = float(val)
        if val >= 1_000_000_000:
            return f"{val / 1_000_000_000:.2f} B"
        elif val >= 1_000_000:
            return f"{val / 1_000_000:.1f} M"
        elif val >= 1_000:
            return f"{val / 1_000:.0f} K"
        else:
            return f"{int(val):,}"
    except:
        return str(val)

def generate_dashboard(df, output_path="options_dashboard.png"):
    """تولید تابلوی ۳ بخشی دارک-مود برای تلگرام و بله"""
    top_value = df.sort_values(by="value", ascending=False).head(10).reset_index(drop=True)
    top_volume = df.sort_values(by="volume", ascending=False).head(10).reset_index(drop=True)
    top_oi = df.sort_values(by="oi", ascending=False).head(10).reset_index(drop=True)

    fig, axes = plt.subplots(1, 3, figsize=(16, 8.5), dpi=200)
    fig.patch.set_facecolor('#0f172a')

    fig.suptitle("Options Market Watch - TSETMC Derivative", 
                 fontsize=18, fontweight='bold', color='#f8fafc', y=0.96)

    sections = [
        {
            "ax": axes[0],
            "title": "Top 10 Traded Value (ارزش معاملات)",
            "data": top_value,
            "metric_col": "value",
            "header": ["#", "Symbol", "Value"],
            "color": "#38bdf8"
        },
        {
            "ax": axes[1],
            "title": "Top 10 Traded Volume (حجم معاملات)",
            "data": top_volume,
            "metric_col": "volume",
            "header": ["#", "Symbol", "Volume"],
            "color": "#34d399"
        },
        {
            "ax": axes[2],
            "title": "Top 10 Open Interest (موقعیت باز)",
            "data": top_oi,
            "metric_col": "oi",
            "header": ["#", "Symbol", "Open Int."],
            "color": "#fbbf24"
        }
    ]

    for sec in sections:
        ax = sec["ax"]
        ax.set_facecolor('#1e293b')
        ax.axis('tight')
        ax.axis('off')

        table_data = []
        for i, row in sec["data"].iterrows():
            table_data.append([
                str(i + 1),
                row["symbol"],
                format_number(row[sec["metric_col"]])
            ])

        table = ax.table(
            cellText=table_data,
            colLabels=sec["header"],
            loc='center',
            cellLoc='center'
        )

        table.auto_set_font_size(False)
        table.set_font_size(10)
        table.scale(1, 2.0)

        for (row_idx, col_idx), cell in table.get_celld().items():
            cell.set_edgecolor('#334155')
            if row_idx == 0:
                cell.set_facecolor(sec["color"])
                cell.get_text().set_color('#0f172a')
                cell.get_text().set_weight('bold')
            else:
                bg = '#1e293b' if row_idx % 2 == 0 else '#243247'
                cell.set_facecolor(bg)
                cell.get_text().set_color('#f8fafc')

        ax.set_title(sec["title"], fontsize=12, fontweight='bold', color=sec["color"], pad=14)

    plt.subplots_adjust(top=0.88, bottom=0.06, left=0.03, right=0.97, wspace=0.18)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Dashboard saved successfully as {output_path}")

def send_to_telegram_and_bale(image_path, caption):
    """ارسال به تلگرام و بله"""
    if not os.path.exists(image_path):
        return

    # ارسال تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=35
                )
            if res.status_code == 200:
                print("Telegram sent successfully.")
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    # ارسال بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=35
                )
            if res.status_code == 200:
                print("Bale sent successfully.")
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

def main():
    print("Fetching Options Data...")
    df = get_options_data()
    if df is not None and not df.empty:
        img_file = "options_dashboard.png"
        generate_dashboard(df, img_file)
        caption = "📊 تابلوی برترین‌های اختیار معامله (آپشن)\n⚡ ۱۰ نماد برتر ارزش معاملات، حجم و موقعیت‌های باز\n⏱ به‌روزرسانی زنده بازار مشتقه"
        send_to_telegram_and_bale(img_file, caption)
    else:
        print("No options data available or failed to retrieve.")

if __name__ == "__main__":
    main()
