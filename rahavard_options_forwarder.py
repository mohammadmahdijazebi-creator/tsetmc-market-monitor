import os
import re
import sys
import requests
from bs4 import BeautifulSoup

# دریافت توکن‌ها و شناسه‌های کانال از Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

CHANNEL_WEB_URL = "https://t.me/s/rahavard365"
LAST_ID_FILE = "last_rahavard_option_id.txt"

def get_last_processed_id():
    """خواندن شناسه آخرین پیام ارسال‌شده"""
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return None
    return None

def save_last_processed_id(msg_id):
    """ذخیره شناسه پیام برای جلوگیری از ارسال تکراری"""
    try:
        with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
            f.write(str(msg_id))
    except Exception as e:
        print(f"Error saving last ID: {e}")

def send_image(image_path, caption):
    """ارسال تصویر به تلگرام و بله"""
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
                print("Telegram: Image sent successfully.")
            else:
                print(f"Telegram error: {res.text}")
        except Exception as e:
            print(f"Telegram exception: {e}")

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
                print("Bale: Image sent successfully.")
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

def fetch_and_forward():
    print(f"Checking {CHANNEL_WEB_URL} for Options Infographic...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(CHANNEL_WEB_URL, headers=headers, timeout=30)
    except Exception as e:
        print(f"Failed to load channel page: {e}")
        return

    if resp.status_code != 200:
        print(f"Channel response status: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    # استخراج همه پیام‌ها
    messages = soup.find_all("div", class_=re.compile(r"tgme_widget_message\b"))

    target_msg = None
    target_img_url = None
    target_msg_id = None
    target_caption = ""

    # بررسی پیام‌ها از جدیدترین به قدیمی‌ترین
    for msg in reversed(messages):
        # بررسی متن یا کپشن پیام
        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text() if text_el else ""

        # بررسی وجود تصویر در پیام
        photo_el = msg.find("a", class_="tgme_widget_message_photo_wrap")
        
        # شرط انطباق: داشتن تصویر + دارا بودن کلیدواژه‌های پوستر اختیار معامله
        if photo_el and ("اختیار معامله" in text or "آنچه در بازار اختیار" in text):
            # استخراج آدرس تصویر باکیفیت از background-image
            style = photo_el.get("style", "")
            match = re.search(r"background-image:url\('(.*?)'\)", style)
            if match:
                target_img_url = match.group(1)
                data_post = msg.get("data-post", "")
                target_msg_id = data_post.split("/")[-1] if "/" in data_post else data_post
                target_caption = text.strip()
                target_msg = msg
                break

    if not target_img_url or not target_msg_id:
        print("No matching Options Market Infographic found in recent messages.")
        return

    last_id = get_last_processed_id()
    print(f"Latest found Message ID: {target_msg_id} (Last saved ID: {last_id})")

    # اگر قبلاً این پیام ارسال شده باشد، مجدداً ارسال نکن
    if last_id and str(last_id) == str(target_msg_id):
        print("This infographic has already been sent. Skipping.")
        return

    # دانلود عکس اصلی
    print(f"Downloading image from: {target_img_url}")
    img_resp = requests.get(target_img_url, headers=headers, timeout=30)
    if img_resp.status_code != 200:
        print("Failed to download image.")
        return

    local_img_path = "rahavard_options_latest.jpg"
    with open(local_img_path, "wb") as f:
        f.write(img_resp.content)

    # قالب‌بندی کپشن
    out_caption = f"📊 **آنچه در بازار اختیار معامله گذشت...**\n\n{target_caption}\n\n📎 منبع: ره‌آورد ۳۶۵"
    if len(out_caption) > 1000:
        out_caption = out_caption[:990] + "..."

    # ارسال به تلگرام و بله
    send_image(local_img_path, out_caption)

    # به‌روزرسانی شناسه آخرین پیام
    save_last_processed_id(target_msg_id)
    print("Process completed successfully.")

if __name__ == "__main__":
    fetch_and_forward()
