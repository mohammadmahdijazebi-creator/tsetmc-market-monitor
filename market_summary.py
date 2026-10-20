# -*- coding: utf-8 -*-
"""
Market Summary Dispatcher - TSETMC Market Monitor
ارسال خلاصه‌وضعیت بازار مالی و بخش‌های سه‌گانه مشابه تریدر آرنا (برگرفته از metawave.ir)
تنظیم‌شده برای اجرا هر ۱۵ دقیقه توسط Cron-job در زمان فعالیت بازار.
"""

import os
import requests
import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", "")

def get_live_market_data():
    url = "https://api.navasan.tech/latest/?api_key=free`"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching live market data: {e}")
    return None

def send_to_channels(text):
    success = False
    if BOT_TOKEN and CHANNEL_ID:
        tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(tg_url, json=payload, timeout=10)
            if r.status_code == 200:
                print("Market summary successfully sent to Telegram.")
                success = True
            else:
                print(f"Telegram send failed: {r.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        bale_url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
        bale_payload = {
            "chat_id": BALE_CHANNEL_ID,
            "text": text
        }
        try:
            r = requests.post(bale_url, json=bale_payload, timeout=10)
            if r.status_code == 200:
                print("Market summary successfully sent to Bale.")
                success = True
            else:
                print(f"Bale send failed: {r.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

    return success

def generate_metawave_arena_summary():
    """بخش‌های سه‌گانه تحلیلی بازار مشابه تریدر آرنا (برگرفته از metawave.ir)"""
    now_str = datetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
    
    # بخش اول: نمای کلی و جریان نقدینگی
    part1 = "📊 *بخش اول: نمای کلی و جریان نقدینگی بازار*\n" \
            "• رصد ورود و خروج پول حقیقی در صنایع بورسی\n" \
            "• بررسی ارزش صف‌های خرید و فروش و حجم معاملات\n" \
            "• تحلیل پویایی تابلوی معاملات (MetaWave)\n"

    # بخش دوم: تابلوخوانی و تکنیکال کلیدی
    part2 = "📈 *بخش دوم: تابلوخوانی و غربالگری تکنیکال*\n" \
            "• شناسایی نمادهای مستعد برگشت و مستحکم\n" \
            "• بررسی وضعیت صندوق‌های اهرمی، طلا و درآمد ثابت\n" \
            "• هشدار در خصوص مقاومت‌ها و حمایت‌های شاخص\n"

    # بخش سوم: دیدبان مشتقات و اختیار معاملات
    part3 = "🎯 *بخش سوم: دیدبان اختیار معامله (Options)*\n" \
            "• پایش موقعیت‌های باز (OI) و قراردادهای پرحجم\n" \
            "• بررسی ارزش ذاتی و زمانی موقعیت‌ها در بازار مشتقه\n"

    footer = f"\n⏱ زمان گزارش: {now_str}\n🌐 مرجع تحلیل: MetaWave (https://metawave.ir/)\n🟢 بروزرسانی خودکار (هر ۱۵ دقیقه در زمان بازار)"
    
    return f"🔥 *گزارش جامع سه بخشی بازار (مشابه تریدر آرنا)*\n\n{part1}\n{part2}\n{part3}\n{footer}"

if __name__ == "__main__":
    print("Executing market summary dispatch with MetaWave 3-part arena sections...")
    market_data = get_live_market_data()
    
    if market_data:
        try:
            usd = market_data.get("usd", {}).get("value", "N/A")
            eur = market_data.get("eur", {}).get("value", "N/A")
            gbp = market_data.get("gbp", {}).get("value", "N/A")
            
            now_str = datetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
            arena_text = generate_metawave_arena_summary()
            
            summary_text = (
                f"📊 *گزارش زنده بازار مالی و بورس*\n"
                f"📅 تاریخ: {now_str}\n\n"
                f"💵 دلار آزاد: {usd} تومان\n"
                f"💶 یورو: {eur} تومان\n"
                f"💷 پوند: {gbp} تومان\n\n"
                f"{arena_text}"
            )
            send_to_channels(summary_text)
        except Exception as ex:
            print(f"Error parsing market data: {ex}")
            send_to_channels(generate_metawave_arena_summary())
    else:
        print("Live market API unavailable, sending MetaWave arena summary...")
        send_to_channels(generate_metawave_arena_summary())
