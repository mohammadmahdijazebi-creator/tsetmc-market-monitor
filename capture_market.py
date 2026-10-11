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
    ارسال تصویر به تلگرام و بله با مدیریت کامل خطا
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
                    timeout=40
                )
            if res.status_code == 200:
                print(f"Telegram: Sent {image_path}")
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
                    timeout=40
                )
            if res.status_code == 200:
                print(f"Bale: Sent {image_path}")
            else:
                print(f"Bale error on {image_path}: {res.text}")
        except Exception as e:
            print(f"Bale exception on {image_path}: {e}")

def capture_all():
    print("Starting browser session...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        # رزولوشن دسکتاپ مناسب برای لود بهینه داشبوردها
        context = browser.new_context(
            viewport={"width": 1600, "height": 950},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ۱. تصویربرداری از Traders Arena
        try:
            print("Capturing Traders Arena...")
            page.goto("https://tradersarena.ir/", wait_until="networkidle", timeout=60000)
            time.sleep(6)  # مکث برای رندر شدن ویجت‌ها و نمودارها
            page.screenshot(path="traders_arena.png")
            send_image("traders_arena.png", "📊 *داشبورد جریان نقدینگی و آمارهای کلیدی*\nمنبع: tradersarena.ir")
        except Exception as e:
            print(f"Error capturing tradersarena: {e}")

        # ۲. تصویربرداری از بخش نمودارها و آمار Bourse Trader
        try:
            print("Capturing Bourse Trader...")
            page.goto("https://bourse-trader.ir/", wait_until="networkidle", timeout=60000)
            time.sleep(6)
            
            # اسکرین‌شات از بالای صفحه (نمودارهای روند)
            page.screenshot(path="bourse_trader_charts.png")
            send_image("bourse_trader_charts.png", "📈 *نمودارهای روند و سرانه‌های بازار*\nمنبع: bourse-trader.ir")
            
            # اسکرول به پایین صفحه برای جداول ورود/خروج پول و سرانه‌ها
            page.evaluate("window.scrollBy(0, 850)")
            time.sleep(2)
            page.screenshot(path="bourse_trader_tables.png")
            send_image("bourse_trader_tables.png", "📋 *بیشترین ورود/خروج پول حقیقی و سرانه‌ها*\nمنبع: bourse-trader.ir")
        except Exception as e:
            print(f"Error capturing bourse-trader: {e}")

        # ۳. تصویربرداری از سایت رسمی مدیریت فناوری بورس (TSETMC)
        try:
            print("Capturing TSETMC...")
            page.goto("https://old.tsetmc.com/Loader.aspx?ParTree=151311&i=0", wait_until="load", timeout=60000)
            time.sleep(5)
            page.screenshot(path="tsetmc_overview.png")
            send_image("tsetmc_overview.png", "🏛 *دیده‌بان در یک نگاه بورس و فرابورس*\nمنبع: tsetmc.com")
        except Exception as e:
            print(f"Error capturing tsetmc: {e}")

        browser.close()
        print("Session completed successfully.")

if __name__ == "__main__":
    capture_all()
