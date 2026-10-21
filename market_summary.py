# -*- coding: utf-8 -*-
"""
Market Summary Dispatcher - TSETMC Market Monitor
ارسال خلاصه‌وضعیت بازار مالی و بخش‌های سه‌گانه مشابه تریدر آرنا (برگرفته از metawave.ir)
تنظیم‌شده برای روزهای کاری (شنبه تا چهارشنبه) از ساعت ۰۸:۳۰ الی ۱۸:۰۰ به وقت ایران.
"""

import os
import sys
import datetime
import requests

# خواندن متغیرهای محیطی با پشتیبانی از هر دو نام‌گذاری
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID") or os.getenv("TELEGRAM_CHANNEL_ID", "")
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", "")

def get_iran_time():
    """محاسبه زمان رسمی ایران (UTC + 3:30)"""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    iran_tz = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
    return utc_now.astimezone(iran_tz)

def is_market_time(now_iran):
    """
    بررسی زمان فعالیت بازار:
    روزهای شنبه تا چهارشنبه (در پایتون دوشنبه=0، یکشنبه=6؛ پس شنبه=5، یکشنبه=6، دوشنبه=0، سه‌شنبه=1، چهارشنبه=2)
    بازه زمانی 08:30 تا 18:00
    """
    # شنبه تا چهارشنبه در پایتون: [5, 6, 0, 1, 2]
    trading_days = [5, 6, 0, 1, 2]
    if now_iran.weekday() not in trading_days:
        return False

    current_minutes = now_iran.hour * 60 + now_iran.minute
    start_minutes = 8 * 60 + 30   # 08:30
    end_minutes = 18 * 60         # 18:00

    return start_minutes <= current_minutes <= end_minutes

def generate_metawave_arena_summary(now_iran):
    """ایجاد گزارش سه‌بخشی تحلیلی مشابه تریدر آرنا بر مبنای متاموج (MetaWave)"""
    date_str = now_iran.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")

    part1 = (
        "📊 *بخش اول: نمای کلی، ارزش معاملات و جریان نقدینگی*\n"
        "• رصد تراز ورود و خروج پول حقیقی در کل بازار و صنایع پیشرو\n"
        "• بررسی حجم معاملات خرد و مقایسه نسبت به میانگین ماهانه\n"
        "• پایش نسبت ارزش صف‌های خرید به صف‌های فروش در تابلوی متاموج\n"
    )

    part2 = (
        "📈 *بخش دوم: تابلوخوانی، صندوق‌های اهرمی و تکنیکال کلیدی*\n"
        "• بررسی فشار عرضه و تقاضا در صندوق‌های اهرمی (شتاب، اهرم، موج، جهش)\n"
        "• رصد وضعیت ورود پول به صندوق‌های طلا و با درآمد ثابت (Fixed Income)\n"
        "• شناسایی الگوهای برگشتی تابلویی و سطوح کلیدی حمایت/مقاومت شاخص\n"
    )

    part3 = (
        "🎯 *بخش سوم: دیدبان بازار مشتقه و اختیار معامله (Options)*\n"
        "• بررسی تغییرات موقعیت‌های باز (OI) در نمادهای قراردادهای پرحجم\n"
        "• تحلیل نسبت حجم اختیارهای خرید (Call) به فروش (Put) در بازار\n"
        "• سنجش حباب قیمتی، نوسان‌پذیری ضمنی (IV) و ارزش زمانی قراردادها\n"
    )

    header = f"🏛 *گزارش زنده تحلیل بازار (سبک تریدر آرنا - برگرفته از MetaWave)*\n📅 تاریخ: {date_str}  ⏱ ساعت: {time_str}\n\n"
    footer = (
        "\n🌐 مرجع داده‌ها: سامانه MetaWave (https://metawave.ir/)\n"
        "⏱ بازه انتشار: ساعت ۰۸:۳۰ تا ۱۸:۰۰ (هر ۱۵ دقیقه در روزهای بازار)"
    )

    return header + part1 + "\n" + part2 + "\n" + part3 + footer

def send_to_channels(text):
    """ارسال پیام به کانال‌های تلگرام و بله"""
    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            r = requests.post(tg_url, json=payload, timeout=15)
            if r.status_code == 200:
                print("Market summary successfully sent to Telegram.")
            else:
                print(f"Telegram error ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")
    else:
        print("Telegram tokens not set, skipping Telegram.")

    # ارسال به بله (تبدیل مارک‌داون برای جلوگیری از عدم ارسال در پیام‌رسان بله)
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        bale_url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
        # در بله حذف ستاره‌های مارک‌داون پیام را خواناتر و بدون ارور می‌کند
        clean_text = text.replace("*", "")
        bale_payload = {
            "chat_id": BALE_CHANNEL_ID,
            "text": clean_text
        }
        try:
            r = requests.post(bale_url, json=bale_payload, timeout=15)
            if r.status_code == 200:
                print("Market summary successfully sent to Bale.")
            else:
                print(f"Bale error ({r.status_code}): {r.text}")
        except Exception as e:
            print(f"Bale exception: {e}")
    else:
        print("Bale tokens not set, skipping Bale.")

if __name__ == "__main__":
    now_iran = get_iran_time()
    print(f"Starting Market Summary check. Current Iran Time: {now_iran.strftime('%Y-%m-%d %H:%M:%S')}")

    # در صورت تمایل به تست دستی در هر ساعتی، می‌توانید آرگومان --force پاس دهید
    force_run = "--force" in sys.argv

    if force_run or is_market_time(now_iran):
        print("Market hours detected (or force triggered). Generating and sending 3-part arena summary...")
        report = generate_metawave_arena_summary(now_iran)
        send_to_channels(report)
    else:
        print("Market is closed (Outside 08:30 - 18:00 or weekend). Skipping message dispatch.")
