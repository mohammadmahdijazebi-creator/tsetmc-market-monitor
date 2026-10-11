import os
import sys
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt

# دریافت متغیرهای محیطی تلگرام و بله
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def get_options_data():
    """دریافت داده‌های زنده تابلوی اختیار معامله از وب‌سرویس معتبر بازار مشتقه"""
    url = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://old.tsetmc.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            rows = []
            
            # استخراج ساختار داده‌های آپشن
            market_list = data.get("instrumentOptionMarketWatch", [])
            for item in market_list:
                # قرارداد خرید (Call)
                if item.get("insCode"):
                    rows.append({
                        "symbol": item.get("lVal18AFC", "").strip(),     # نماد نماد (مثلا ضاهرم...)
                        "volume": float(item.get("qTotTran5J", 0) or 0),  # حجم معاملات
                        "value": float(item.get("qTotCap", 0) or 0),     # ارزش معاملات
                        "oi": float(item.get("notOPnIntrst", 0) or 0)     # موقعیت باز
                    })
                # قرارداد فروش (Put)
                if item.get("pInsCode"):
                    rows.append({
                        "symbol": item.get("pLVal18AFC", "").strip(),
                        "volume": float(item.get("pQTotTran5J", 0) or 0),
                        "value": float(item.get("pQTotCap", 0) or 0),
                        "oi": float(item.get("pNotOPnIntrst", 0) or 0)
                    })

            df = pd.DataFrame(rows)
            df = df[df["symbol"] != ""]
            return df
        else:
            print(f"Failed to fetch data: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching options data: {e}")
        return None

def format_number(val):
    """فرمت‌دهی اعداد به صورت خوانا و سه‌رقمی یا بر حسب میلیون/میلیارد"""
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
    """تولید تصویر گرافیکی تابلوی ۳ بخشی شامل برترین‌های ارزش، حجم و موقعیت باز"""
    
    # تفکیک و مرتب‌سازی ۱۰ نماد برتر
    top_value = df.sort_values(by="value", ascending=False).head(10).reset_index(drop=True)
    top_volume = df.sort_values(by="volume", ascending=False).head(10).reset_index(drop=True)
    top_oi = df.sort_values(by="oi", ascending=False).head(10).reset_index(drop=True)

    # تنظیمات صفحه گرافیکی (تیره و شیک)
    fig, axes = plt.subplots(1, 3, figsize=(16, 8.5), dpi=200)
    fig.patch.set_facecolor('#0f172a') # پس‌زمینه دارک اسلیت

    # عنوان اصلی داشبورد
    fig.suptitle("Options Market Watch | تابلوی برترین‌های اختیار معامله بورس", 
                 fontsize=18, fontweight='bold', color='#f8fafc', y=0.96)

    sections = [
        {
            "ax": axes[0],
            "title": "🔥 ۱۰ نماد بیشترین ارزش معاملات",
            "data": top_value,
            "metric_col": "value",
            "header": ["رتبه", "نماد قرارداد", "ارزش معاملات"],
            "color": "#38bdf8" # آبی فیروزه‌ای
        },
        {
            "ax": axes[1],
            "title": "📊 ۱۰ نماد بیشترین حجم معاملات",
            "data": top_volume,
            "metric_col": "volume",
            "header": ["رتبه", "نماد قرارداد", "حجم معاملات"],
            "color": "#34d399" # سبز زمردی
        },
        {
            "ax": axes[2],
            "title": "🎯 ۱۰ نماد بیشترین موقعیت باز (OI)",
            "data": top_oi,
            "metric_col": "oi",
            "header": ["رتبه", "نماد قرارداد", "موقعیت باز"],
            "color": "#fbbf24" # طلایی/کهربایی
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

        # ساخت جدول روی کارت گرافیکی
        table = ax.table(
            cellText=table_data,
            colLabels=sec["header"],
            loc='center',
            cellLoc='center'
        )

        table.auto_set_font_size(False)
        table.set_font_size(10)
        table.scale(1, 2.0)

        # استایل‌دهی به سلول‌ها و هدر
        for (row_idx, col_idx), cell in table.get_celld().items():
            cell.set_edgecolor('#334155')
            if row_idx == 0:
                cell.set_facecolor(sec["color"])
                cell.get_text().set_color('#0f172a')
                cell.get_text().set_weight('bold')
            else:
                # ردیف‌های یک در میان برای خوانایی بهتر
                bg = '#1e293b' if row_idx % 2 == 0 else '#243247'
                cell.set_facecolor(bg)
                cell.get_text().set_color('#f8fafc')

        ax.set_title(sec["title"], fontsize=12, fontweight='bold', color=sec["color"], pad=14)

    plt.subplots_adjust(top=0.88, bottom=0.06, left=0.03, right=0.97, wspace=0.18)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Dashboard saved to {output_path}")

def send_to_telegram_and_bale(image_path, caption):
    """ارسال تصویر خروجی به تلگرام و بله"""
    if not os.path.exists(image_path):
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=30
                )
            if res.status_code == 200:
                print("Telegram sent successfully.")
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=30
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
        caption = "📊 *تابلوی برترین‌های اختیار معامله (آپشن)*\n⚡ ۱۰ نماد برتر ارزش معاملات، حجم و موقعیت‌های باز\n⏱ به‌روزرسانی زنده بازار"
        send_to_telegram_and_bale(img_file, caption)
    else:
        print("No options data available or failed to retrieve.")

if __name__ == "__main__":
    main()
