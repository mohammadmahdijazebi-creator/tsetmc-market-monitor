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
                    timeout=50
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
                    timeout=50
                )
            if res.status_code == 200:
                print(f"Bale: Sent {image_path}")
            else:
                print(f"Bale error on {image_path}: {res.text}")
        except Exception as e:
            print(f"Bale exception on {image_path}: {e}")

def capture_all():
    print("Starting robust browser session...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ۱. تصویربرداری از تمام بخش‌های Traders Arena (تمام صفحه)
        try:
            print("Navigating to Traders Arena...")
            page.goto("https://tradersarena.ir/", wait_until="networkidle", timeout=60000)
            time.sleep(6)
            
            # اسکرین‌شات تمام صفحه برای اینکه بخش دوم و جدول‌ها کامل بیفتد
            page.screenshot(path="traders_arena_full.png", full_page=True)
            send_image("traders_arena_full.png", "📊 *داشبورد جامع جریان نقدینگی و آمارهای بازار (بخش اول و دوم)*\nمنبع: tradersarena.ir")
        except Exception as e:
            print(f"Error capturing tradersarena: {e}")

        # ۲. تصویربرداری از Bourse Trader (همراه با بستن احتمالی پاپ‌آپ‌ها)
        try:
            print("Navigating to Bourse Trader...")
            page.goto("https://bourse-trader.ir/", wait_until="networkidle", timeout=60000)
            time.sleep(6)
            
            # بستن پاپ‌آپ احتمالی بروزرسانی با کلیک یا اسکریپت
            try:
                page.keyboard.press("Escape")
                page.evaluate("document.querySelectorAll('.modal, .swal2-container, div[role=\\'dialog\\']').forEach(el => el.remove());")
                time.sleep(2)
            except:
                pass
            
            # اسکرین‌شات تمام صفحه از بورس تریدر
            page.screenshot(path="bourse_trader_full.png", full_page=True)
            send_image("bourse_trader_full.png", "📈 *گزارش کامل نمودارها، سرانه‌ها و ورود پول حقیقی*\nمنبع: bourse-trader.ir")
        except Exception as e:
            print(f"Error capturing bourse-trader: {e}")

        # ۳. تصویربرداری از سایت رسمی TSETMC
        try:
            print("Navigating to TSETMC...")
            page.goto("https://old.tsetmc.com/Loader.aspx?ParTree=151311&i=0", wait_until="load", timeout=60000)
            time.sleep(6)
            page.screenshot(path="tsetmc_overview.png", full_page=True)
            send_image("tsetmc_overview.png", "🏛 *دیده‌بان در یک نگاه بورس و فرابورس (TSETMC)*\nمنبع: tsetmc.com")
        except Exception as e:
            print(f"Error capturing tsetmc: {e}")

        browser.close()
        print("All captures completed.")

if __name__ == "__main__":
    capture_all()
