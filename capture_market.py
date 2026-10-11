import os
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

SCREENSHOT_PATH = "market_overview.png"

def capture_traders_arena():
    """
    باز کردن سایت tradersarena و تهیه اسکرین‌شات با کیفیت از داشبورد بازار
    """
    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # تنظیم ابعاد صفحه نمایش برای نمایش کامل جدول‌ها و نمودارها
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        url = "https://tradersarena.ir/"
        print(f"Navigating to {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # چند ثانیه مکث برای لود کامل رندرهای جاوااسکریپت و نمودارها
        time.sleep(5)
        
        # اسکرین‌شات از نمای اصلی
        page.screenshot(path=SCREENSHOT_PATH, full_page=False)
        print("Screenshot captured successfully.")
        browser.close()

def send_image_to_channels():
    caption = "📊 پایش تصویری جریان نقدینگی و وضعیت بازار بورس\nمنبع: tradersarena.ir"
    
    # ارسال به تلگرام با sendPhoto
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(SCREENSHOT_PATH, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=30
                )
            if res.status_code == 200:
                print("Telegram photo sent successfully.")
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    # ارسال به بله با sendPhoto
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(SCREENSHOT_PATH, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=30
                )
            if res.status_code == 200:
                print("Bale photo sent successfully.")
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

if __name__ == "__main__":
    try:
        capture_traders_arena()
        send_image_to_channels()
    except Exception as e:
        print(f"Fatal execution error: {e}")
