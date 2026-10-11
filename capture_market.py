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
    ارسال فایل تصویر به تلگرام و بله با لاگ دقیق
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
                    timeout=60
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
                    timeout=60
                )
            if res.status_code == 200:
                print(f"Bale sent: {image_path}")
            else:
                print(f"Bale error on {image_path}: {res.text}")
        except Exception as e:
            print(f"Bale exception on {image_path}: {e}")

def capture_all():
    print("Starting market capture runner...")
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
            viewport={"width": 1400, "height": 850},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ==============================================================
        # ۱. تریدرز آرنا (۳ بخش کامل و فریز شده)
        # ==============================================================
        try:
            print("1. Processing Traders Arena...")
            page.goto("https://tradersarena.ir/", wait_until="networkidle", timeout=45000)
            time.sleep(6)

            # بخش اول
            page.screenshot(path="traders_arena_1.png", full_page=False)
            send_image(
                "traders_arena_1.png",
                "📊 *تریدرز آرنا - بخش ۱ (آمارهای کلیدی بازار)*\nمنبع: tradersarena.ir"
            )

            # بخش دوم
            page.evaluate("window.scrollTo(0, 750);")
            time.sleep(3)
            page.screenshot(path="traders_arena_2.png", full_page=False)
            send_image(
                "traders_arena_2.png",
                "📉 *تریدرز آرنا - بخش ۲ (نمودارهای جریان نقدینگی)*\nمنبع: tradersarena.ir"
            )

            # بخش سوم
            page.evaluate("window.scrollTo(0, 1500);")
            time.sleep(3)
            page.screenshot(path="traders_arena_3.png", full_page=False)
            send_image(
                "traders_arena_3.png",
                "📋 *تریدرز آرنا - بخش ۳ (صف‌های خرید و فروش)*\nمنبع: tradersarena.ir"
            )
        except Exception as e:
            print(f"Error in Traders Arena: {e}")

        # ==============================================================
        # ۲. تابلوی نماد «اهرم» (۲ بخش: تابلو قیمت و عمق بازار/نمودار)
        # ==============================================================
        try:
            print("2. Processing Ahrom symbol...")
            page.goto("https://rahavard365.com/asset/52309/اهرم", wait_until="domcontentloaded", timeout=45000)
            time.sleep(7)

            # بستن پاپ‌آپ احتمالی سایت در صورت وجود
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

            # بخش اول نماد اهرم (تابلوی زنده قیمت و معاملات)
            page.screenshot(path="ahrom_part1.png", full_page=False)
            send_image(
                "ahrom_part1.png",
                "⚡ *نماد اهرم - بخش ۱ (تابلو قیمت، صف‌ها و دامنه نوسان)*\nمنبع: rahavard365"
            )

            # بخش دوم نماد اهرم (اسکرول به بخش حقیقی/حقوقی و نمودار)
            page.evaluate("window.scrollTo(0, 600);")
            time.sleep(2)
            page.screenshot(path="ahrom_part2.png", full_page=False)
            send_image(
                "ahrom_part2.png",
                "⚡ *نماد اهرم - بخش ۲ (آمار خریداران/فروشندگان و سوابق)*\nمنبع: rahavard365"
            )
        except Exception as e:
            print(f"Error in Ahrom: {e}")

        # ==============================================================
        # ۳. تابلوی نماد «خودرو» (۲ بخش: تابلو قیمت و عمق بازار/نمودار)
        # ==============================================================
        try:
            print("3. Processing Khodro symbol...")
            page.goto("https://rahavard365.com/asset/283/خودرو", wait_until="domcontentloaded", timeout=45000)
            time.sleep(7)

            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

            # بخش اول نماد خودرو
            page.screenshot(path="khodro_part1.png", full_page=False)
            send_image(
                "khodro_part1.png",
                "🚗 *نماد خودرو - بخش ۱ (تابلو قیمت، صف‌ها و دامنه نوسان)*\nمنبع: rahavard365"
            )

            # بخش دوم نماد خودرو
            page.evaluate("window.scrollTo(0, 600);")
            time.sleep(2)
            page.screenshot(path="khodro_part2.png", full_page=False)
            send_image(
                "khodro_part2.png",
                "🚗 *نماد خودرو - بخش ۲ (آمار خریداران/فروشندگان و سوابق)*\nمنبع: rahavard365"
            )
        except Exception as e:
            print(f"Error in Khodro: {e}")

        browser.close()
        print("Done! All captures finished.")

if __name__ == "__main__":
    capture_all()
