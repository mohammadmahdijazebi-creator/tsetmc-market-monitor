import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

def send_image(image_path, caption):
    """
    ارسال فایل تصویر به تلگرام و بله با سرعت بالا و لاگ دقیق
    """
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
    print("Starting fast market capture runner (Traders Arena)...")
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
        # ۱. صفحه اصلی تریدرز آرنا (۳ بخش سریع و تمیز)
        # ==============================================================
        try:
            print("1. Processing Traders Arena Main Page...")
            page.goto("https://tradersarena.ir/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3) # مکث کوتاه و بهینه برای سرعت بالا

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
        # ۲. نماد «اهرم» در تریدرز آرنا (صفحه اختصاصی تمیز و سریع)
        # ==============================================================
        try:
            print("2. Processing Ahrom symbol on Traders Arena...")
            page.goto("https://tradersarena.ir/17914401175772326", wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)

            page.screenshot(path="ahrom_arena.png", full_page=True)
            send_image(
                "ahrom_arena.png",
                "⚡ *نماد اهرم - تابلو معاملات و جزئیات کامل*\nمنبع: tradersarena.ir"
            )
        except Exception as e:
            print(f"Error in Ahrom Ahrend Arena: {e}")

        browser.close()
        print("Done! All fast captures finished successfully.")

if __name__ == "__main__":
    capture_all()
