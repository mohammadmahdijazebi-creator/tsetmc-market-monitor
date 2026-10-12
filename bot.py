import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN", "").strip()
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID", "").strip()

STATE_FILE = Path("market_monitor_state.json")
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# لیست نمادهای تحت رصد
SYMBOLS = [
    {
        "name": "ahrom",
        "title": "⚡ نماد اهرم (صندوق اهرمی)",
        "url": "https://tradersarena.ir/17914401175772326"
    },
    {
        "name": "khodro",
        "title": "🚗 نماد خودرو (ایران خودرو)",
        "url": "https://tradersarena.ir/65883838195688438"
    },
    {
        "name": "taban",
        "title": "🏢 نماد تابان (پتروشیمی تابان فردا)",
        "url": "https://tradersarena.ir/30714151942396396"
    },
    {
        "name": "ayar",
        "title": "🪙 نماد عیار (صندوق طلای مفید)",
        "url": "https://tradersarena.ir/34144395039913458"
    },
    {
        "name": "noghrat",
        "title": "🥈 نماد نقراط (صندوق نقره)",
        "url": "https://tradersarena.ir/65365726391403130"
    }
]


def load_last_hash():
    """خواندن هش آخرین وضعیت تابلوی بازار"""
    if not STATE_FILE.exists():
        return ""
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("last_main_hash", "")
    except Exception:
        return ""


def save_last_hash(img_hash):
    """ذخیره هش تابلوی بازار"""
    try:
        STATE_FILE.write_text(
            json.dumps({"last_main_hash": img_hash, "updated_at": datetime.now(TEHRAN_TZ).isoformat()}),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"خطا در ذخیره وضعیت هش: {e}")


def get_file_md5(filepath):
    """محاسبه هش محتوای تصویر جهت سنجش تغییرات تابلو"""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def is_market_time_allowed():
    """بررسی بازه زمانی مجاز بازار: شنبه تا چهارشنبه از ۰۸:۳۰ تا ۱۸:۰۰"""
    now = datetime.now(TEHRAN_TZ)
    # در پایتون: دوشنبه=0، سه‌شنبه=1، چهارشنبه=2، پنج‌شنبه=3، جمعه=4، شنبه=5، یکشنبه=6
    # روزهای کاری بورس ایران: شنبه(5), یکشنبه(6), دوشنبه(0), سه‌شنبه(1), چهارشنبه(2)
    # روزهای تعطیل: پنج‌شنبه(3) و جمعه(4)
    weekday = now.weekday()
    if weekday in (3, 4):
        print(f"[{now.strftime('%H:%M')}] امروز پنج‌شنبه یا جمعه (تعطیل) است. اجرا متوقف شد.")
        return False

    current_minutes = now.hour * 60 + now.minute
    start_minutes = 8 * 60 + 30   # 08:30
    end_minutes = 18 * 60         # 18:00

    if not (start_minutes <= current_minutes <= end_minutes):
        print(f"[{now.strftime('%H:%M')}] خارج از ساعت معاملات (۰۸:۳۰ تا ۱۸:۰۰) است. اجرا متوقف شد.")
        return False

    return True


def send_image(image_path, caption):
    """ارسال فایل تصویر به تلگرام و بله با امنیت و لاگ دقیق"""
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=45
                )
            if res.status_code == 200:
                print(f"Telegram sent: {image_path}")
            else:
                print(f"Telegram error on {image_path}: {res.text}")
        except Exception as e:
            print(f"Telegram exception on {image_path}: {e}")

    # ارسال به بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=45
                )
            if res.status_code == 200:
                print(f"Bale sent: {image_path}")
            else:
                print(f"Bale error on {image_path}: {res.text}")
        except Exception as e:
            print(f"Bale exception on {image_path}: {e}")


def capture_all():
    # ۱. فیلتر زمانی روز و ساعت
    if not is_market_time_allowed():
        return

    print("Starting market multi-symbol runner (Traders Arena)...")
    last_hash = load_last_hash()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ==============================================================
        # ۲. بررسی تابلوی اصلی و تست تغییرات (برای روزهای تعطیل رسمی یا ساعات راکد)
        # ==============================================================
        try:
            print("Checking Traders Arena Main Page for updates...")
            page.goto("https://tradersarena.ir/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            page.screenshot(path="traders_arena_1.png", full_page=False)
            current_hash = get_file_md5("traders_arena_1.png")

            # اگر تصویر نسبت به ۵ دقیقه قبل کوچکترین تغییری نکرده باشد (تعطیل رسمی یا عدم آپدیت)
            if current_hash == last_hash:
                print(f"⚠️ دیتای سایت آپدیت نشده است (یا بازار تعطیل رسمی است). هیچ پیامی ارسال نمی‌شود.")
                browser.close()
                return

            print("✅ تابلوی بازار بروزرسانی شده است. در حال ارسال تصاویر به کانال...")
            send_image("traders_arena_1.png", "📊 *تریدرز آرنا - بخش ۱ (آمارهای کلیدی بازار)*\nمنبع: tradersarena.ir")

            page.evaluate("window.scrollTo(0, 750);")
            time.sleep(1.5)
            page.screenshot(path="traders_arena_2.png", full_page=False)
            send_image("traders_arena_2.png", "📉 *تریدرز آرنا - بخش ۲ (نمودارهای جریان نقدینگی)*\nمنبع: tradersarena.ir")

            page.evaluate("window.scrollTo(0, 1500);")
            time.sleep(1.5)
            page.screenshot(path="traders_arena_3.png", full_page=False)
            send_image("traders_arena_3.png", "📋 *تریدرز آرنا - بخش ۳ (صف‌های خرید و فروش)*\nمنبع: tradersarena.ir")

            # ذخیره هش جدید به عنوان آخرین تغییرات
            save_last_hash(current_hash)

        except Exception as e:
            print(f"Error in Traders Arena Main: {e}")
            browser.close()
            return

        # ==============================================================
        # ۳. پردازش و ارسال نمادها (فقط زمانی که دیتای بازار تازه است)
        # ==============================================================
        for item in SYMBOLS:
            name = item["name"]
            title = item["title"]
            url = item["url"]
            
            try:
                print(f"Processing symbol: {name} ({url})")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # بخش اول نماد
                file_part1 = f"{name}_part1.png"
                page.screenshot(path=file_part1, full_page=False)
                send_image(file_part1, f"{title}\n📌 *بخش ۱ (تابلو و جزئیات بالایی)*\nمنبع: tradersarena.ir")

                # بخش دوم نماد
                page.evaluate("window.scrollTo(0, 850);")
                time.sleep(1.5)
                file_part2 = f"{name}_part2.png"
                page.screenshot(path=file_part2, full_page=False)
                send_image(file_part2, f"{title}\n📌 *بخش ۲ (نمودارها و اطلاعات تکمیلی)*\nمنبع: tradersarena.ir")

            except Exception as e:
                print(f"Error processing symbol {name}: {e}")

        browser.close()
        print("Done! All captures finished successfully.")


if __name__ == "__main__":
    capture_all()
