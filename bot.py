import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

# فهرست نمادها و صفحات (قابل ویرایش و توسعه آسان)
SYMBOLS = [
    {
        "name": "اهرم",
        "title": "⚡ نماد اهرم (صندوق اهرمی)",
        "url": "https://tradersarena.ir/17914401175772326"
    },
    {
        "name": "خودرو",
        "title": "🚗 نماد خودرو (ایران خودرو)",
        "url": "https://tradersarena.ir/46348159173323680" # قابل تنظیم با لینک تریدرز آرنا
    },
    {
        "name": "فملی",
        "title": "🏭 نماد فملی (ملی صنایع مس ایران)",
        "url": "https://tradersarena.ir/35425587644337450"
    },
    {
        "name": "کلید",
        "title": "🏠 نماد کلید (صندوق املاک و مستغلات)",
        "url": "https://tradersarena.ir/45292762906823004"
    },
    {
        "name": "تابان",
        "title": "🏢 نماد تابان (پتروشیمی تابان فردا)",
        "url": "https://tradersarena.ir/14079693677610396"
    },
    {
        "name": "عیار",
        "title": "🪙 نماد عیار (صندوق طلای مفید)",
        "url": "https://tradersarena.ir/656152729057801962"
    },
    {
        "name": "عسکه2",
        "title": "🥇 نماد عسکه2 (سلف سکه بانک مرکزی)",
        "url": "https://tradersarena.ir/51198"
    },
    {
        "name": "نقراط",
        "title": "🥈 نماد نقراط (صندوق نقره)",
        "url": "https://tradersarena.ir/67852391048291456"
    }
]

def send_image(image_path, caption):
    """ارسال تصویر به تلگرام و بله با امنیت و لاگ دقیق"""
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
    print("Starting market multi-symbol runner (Traders Arena)...")
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
        # ۱. صفحه اصلی تریدرز آرنا (۳ بخش کلیدی بازار)
        # ==============================================================
        try:
            print("Processing Traders Arena Main Page...")
            page.goto("https://tradersarena.ir/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            page.screenshot(path="traders_arena_1.png", full_page=False)
            send_image("traders_arena_1.png", "📊 *تریدرز آرنا - بخش ۱ (آمارهای کلیدی بازار)*\nمنبع: tradersarena.ir")

            page.evaluate("window.scrollTo(0, 750);")
            time.sleep(1.5)
            page.screenshot(path="traders_arena_2.png", full_page=False)
            send_image("traders_arena_2.png", "📉 *تریدرز آرنا - بخش ۲ (نمودارهای جریان نقدینگی)*\nمنبع: tradersarena.ir")

            page.evaluate("window.scrollTo(0, 1500);")
            time.sleep(1.5)
            page.screenshot(path="traders_arena_3.png", full_page=False)
            send_image("traders_arena_3.png", "📋 *تریدرز آرنا - بخش ۳ (صف‌های خرید و فروش)*\nمنبع: tradersarena.ir")
        except Exception as e:
            print(f"Error in Traders Arena Main: {e}")

        # ==============================================================
        # ۲. پردازش تمام نمادها (هر نماد در دو بخش مجزا)
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

                # اسکرول به پایین برای بخش دوم نماد
                page.evaluate("window.scrollTo(0, 850);")
                time.sleep(1.5)
                
                file_part2 = f"{name}_part2.png"
                page.screenshot(path=file_part2, full_page=False)
                send_image(file_part2, f"{title}\n📌 *بخش ۲ (نمودارها و اطلاعات تکمیلی)*\nمنبع: tradersarena.ir")

            except Exception as e:
                print(f"Error processing symbol {name}: {e}")

        browser.close()
        print("Done! All multi-symbol captures finished successfully.")

if __name__ == "__main__":
    capture_all()
