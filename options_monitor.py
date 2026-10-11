import os
import sys
import time
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

TARGET_URL = "https://tradersarena.ir/options-arena"

def send_image(image_path, caption):
    """ارسال تصویر خروجی به تلگرام و بله"""
    if not os.path.exists(image_path):
        return

    # ارسال به تلگرام
    if BOT_TOKEN and CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=35
                )
            if res.status_code == 200:
                print("Telegram sent successfully.")
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

    # ارسال به پیام‌رسان بله
    if BALE_BOT_TOKEN and BALE_CHANNEL_ID:
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": BALE_CHANNEL_ID, "caption": caption},
                    files={"photo": img},
                    timeout=35
                )
            if res.status_code == 200:
                print("Bale sent successfully.")
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

def capture_options_dashboard():
    """عکس‌برداری از داشبورد کامل اختیار معامله تریدرز آرنا"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ابعاد مناسب دسکتاپ برای باز شدن کامل داشبورد
        context = browser.new_context(
            viewport={"width": 1400, "height": 1100},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"Loading {TARGET_URL} ...")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        
        # ۲ ثانیه مکث برای لود کامل اعداد و جداول زنده
        time.sleep(3)

        # حذف پاپ‌آپ‌ها یا المان‌های مزاحم احتمالی
        page.evaluate("""() => {
            const overlays = document.querySelectorAll('.modal, .backdrop, header, footer');
            overlays.forEach(el => el.remove());
        }""")

        top_img = "options_overview.png"
        bottom_img = "options_tables.png"

        # بخش ۱: نمای کلی داشبورد (خلاصه بازار و موقعیت‌های باز)
        page.screenshot(path=top_img, full_page=False)
        print(f"Saved: {top_img}")

        # اسکرول به پایین برای بخش جداول تجمیعی نمادها
        page.evaluate("window.scrollBy(0, 750)")
        time.sleep(1)
        page.screenshot(path=bottom_img, full_page=False)
        print(f"Saved: {bottom_img}")

        browser.close()
        return [top_img, bottom_img]

def main():
    print("Starting Options Market Visual Capture...")
    try:
        images = capture_options_dashboard()
        
        caption_1 = "📊 **داشبورد بازار اختیار معامله (Options Arena)**\n⚡ خلاصه معاملات، ارزش، حجم و موقعیت‌های باز\n⏱ به‌روزرسانی زنده"
        caption_2 = "📋 **جدول تجمیعی معاملات اختیار معامله بر اساس دارایی پایه**"

        if len(images) >= 2:
            send_image(images[0], caption_1)
            time.sleep(2)
            send_image(images[1], caption_2)
            
    except Exception as e:
        print(f"Error capturing options dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
