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

# -----------------------------
# تنظیمات سایت‌ها
# -----------------------------
TRADERS_ARENA_MAIN = "https://tradersarena.ir/"
METAWAVE_MAIN = "https://metawave.ir/"

# لیست نمادهای تحت رصد (تریدر آرنا)
SYMBOLS = [
    {"name": "ahrom", "title": "⚡ نماد اهرم (صندوق اهرمی)", "url": "https://tradersarena.ir/17914401175772326"},
    {"name": "khodro", "title": "🚗 نماد خودرو (ایران خودرو)", "url": "https://tradersarena.ir/65883838195688438"},
    {"name": "taban", "title": "🏢 نماد تابان (پتروشیمی تابان فردا)", "url": "https://tradersarena.ir/30714151942396396"},
    {"name": "ayar", "title": "🪙 نماد عیار (صندوق طلای مفید)", "url": "https://tradersarena.ir/34144395039913458"},
    {"name": "noghrat", "title": "🥈 نماد نقراط (صندوق نقره)", "url": "https://tradersarena.ir/65365726391403130"},
]


def load_state():
    """
    state نمونه:
    {
      "last_tradersarena_hash": "...",
      "last_metawave_hash": "...",
      "updated_at": "..."
    }
    """
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict):
    try:
        state["updated_at"] = datetime.now(TEHRAN_TZ).isoformat()
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"خطا در ذخیره state: {e}")


def get_file_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def is_market_time_allowed():
    """شنبه تا چهارشنبه از ۰۸:۳۰ تا ۱۸:۰۰"""
    now = datetime.now(TEHRAN_TZ)
    weekday = now.weekday()

    if weekday in (3, 4):  # پنج‌شنبه/جمعه
        print(f"[{now.strftime('%H:%M')}] امروز پنج‌شنبه یا جمعه (تعطیل) است. اجرا متوقف شد.")
        return False

    current_minutes = now.hour * 60 + now.minute
    start_minutes = 8 * 60 + 30
    end_minutes = 18 * 60

    if not (start_minutes <= current_minutes <= end_minutes):
        print(f"[{now.strftime('%H:%M')}] خارج از ساعت معاملات (۰۸:۳۰ تا ۱۸:۰۰) است. اجرا متوقف شد.")
        return False

    return True


def send_image(image_path, caption):
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    # تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=60
                )
            if res.status_code == 200:
                print(f"Telegram sent: {image_path}")
            else:
                print(f"Telegram error on {image_path}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Telegram exception on {image_path}: {e}")

    # بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=60
                )
            if res.status_code == 200:
                print(f"Bale sent: {image_path}")
            else:
                print(f"Bale error on {image_path}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Bale exception on {image_path}: {e}")


def capture_site_3parts(page, base_name: str, caption_prefix: str, source_domain: str,
                        scrolls=(0, 750, 1500), wait_after_load=5, wait_between=1.5):
    """
    سه اسکرین‌شات با اسکرول‌های مختلف می‌گیرد و ارسال می‌کند.
    خروجی فایل‌ها: {base_name}_1.png, {base_name}_2.png, {base_name}_3.png
    """
    for i, y in enumerate(scrolls, start=1):
        try:
            page.evaluate(f"window.scrollTo(0, {int(y)});")
            time.sleep(wait_between)
        except Exception:
            pass

        out = f"{base_name}_{i}.png"
        page.screenshot(path=out, full_page=False)
        send_image(out, f"{caption_prefix} - بخش {i}\nمنبع: {source_domain}")


def capture_metawave(page, state):
    """
    متاویو: اگر صفحه واقعاً تغییر نکرده باشد (هش ثابت)، ارسال انجام نمی‌شود.
    """
    print("Checking MetaWave Main Page for updates...")
    try:
        page.goto(METAWAVE_MAIN, wait_until="networkidle", timeout=60000)
        time.sleep(6)

        # اسکرین شات اول برای هش
        first_img = "metawave_1.png"
        page.screenshot(path=first_img, full_page=False)
        current_hash = get_file_md5(first_img)

        last_hash = state.get("last_metawave_hash", "")
        if current_hash == last_hash:
            print("⚠️ MetaWave آپدیت نشده است (یا بازار تعطیل رسمی/راکد است). هیچ پیامی از MetaWave ارسال نمی‌شود.")
            return state

        print("✅ MetaWave بروزرسانی شده است. در حال ارسال تصاویر...")
        send_image(first_img, "📊 *متاویو - بخش ۱ (نمای کلی)*\nمنبع: metawave.ir")

        # بخش ۲ و ۳
        try:
            page.evaluate("window.scrollTo(0, 850);")
            time.sleep(2)
        except Exception:
            pass
        page.screenshot(path="metawave_2.png", full_page=False)
        send_image("metawave_2.png", "📉 *متاویو - بخش ۲ (جزئیات/نمودارها)*\nمنبع: metawave.ir")

        try:
            page.evaluate("window.scrollTo(0, 1700);")
            time.sleep(2)
        except Exception:
            pass
        page.screenshot(path="metawave_3.png", full_page=False)
        send_image("metawave_3.png", "📋 *متاویو - بخش ۳ (ادامه صفحه)*\nمنبع: metawave.ir")

        state["last_metawave_hash"] = current_hash
        save_state(state)
        return state

    except Exception as e:
        print(f"Error in MetaWave Main: {e}")
        return state


def capture_tradersarena(page, state):
    """
    تریدر آرنا: همان منطق قبلی + ذخیره هش جداگانه
    """
    print("Checking Traders Arena Main Page for updates...")
    try:
        page.goto(TRADERS_ARENA_MAIN, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        page.screenshot(path="traders_arena_1.png", full_page=False)
        current_hash = get_file_md5("traders_arena_1.png")

        last_hash = state.get("last_tradersarena_hash", "")
        if current_hash == last_hash:
            print("⚠️ دیتای تریدر آرنا آپدیت نشده است (یا بازار تعطیل رسمی است). هیچ پیامی ارسال نمی‌شود.")
            return False, state

        print("✅ تابلوی بازار تریدر آرنا بروزرسانی شده است. در حال ارسال تصاویر...")
        send_image("traders_arena_1.png", "📊 *تریدرز آرنا - بخش ۱ (آمارهای کلیدی بازار)*\nمنبع: tradersarena.ir")

        page.evaluate("window.scrollTo(0, 750);")
        time.sleep(1.5)
        page.screenshot(path="traders_arena_2.png", full_page=False)
        send_image("traders_arena_2.png", "📉 *تریدرز آرنا - بخش ۲ (نمودارهای جریان نقدینگی)*\nمنبع: tradersarena.ir")

        page.evaluate("window.scrollTo(0, 1500);")
        time.sleep(1.5)
        page.screenshot(path="traders_arena_3.png", full_page=False)
        send_image("traders_arena_3.png", "📋 *تریدرز آرنا - بخش ۳ (صف‌های خرید و فروش)*\nمنبع: tradersarena.ir")

        state["last_tradersarena_hash"] = current_hash
        save_state(state)
        return True, state

    except Exception as e:
        print(f"Error in Traders Arena Main: {e}")
        return False, state


def capture_symbols(page):
    for item in SYMBOLS:
        name = item["name"]
        title = item["title"]
        url = item["url"]

        try:
            print(f"Processing symbol: {name} ({url})")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            file_part1 = f"{name}_part1.png"
            page.screenshot(path=file_part1, full_page=False)
            send_image(file_part1, f"{title}\n📌 *بخش ۱ (تابلو و جزئیات بالایی)*\nمنبع: tradersarena.ir")

            page.evaluate("window.scrollTo(0, 850);")
            time.sleep(1.5)
            file_part2 = f"{name}_part2.png"
            page.screenshot(path=file_part2, full_page=False)
            send_image(file_part2, f"{title}\n📌 *بخش ۲ (نمودارها و اطلاعات تکمیلی)*\nمنبع: tradersarena.ir")

        except Exception as e:
            print(f"Error processing symbol {name}: {e}")


def capture_all():
    # ۱) فیلتر زمانی کلی
    if not is_market_time_allowed():
        return

    state = load_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        print("Starting market runner (Traders Arena + MetaWave)...")

        # ۲) اول MetaWave (مستقل از TradersArena؛ اگر خطا بدهد بقیه ادامه می‌یابد)
        state = capture_metawave(page, state)

        # ۳) بعد TradersArena (اگر آپدیت نشده باشد، نمادها هم ارسال نشوند)
        changed, state = capture_tradersarena(page, state)
        if changed:
            capture_symbols(page)

        browser.close()
        print("Done! All captures finished successfully.")


if __name__ == "__main__":
    capture_all()
