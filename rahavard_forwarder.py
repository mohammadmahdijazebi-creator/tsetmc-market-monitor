import os
import re
import sys
import requests
from bs4 import BeautifulSoup

# دریافت مقادیر حساس از متغیرهای محیطی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

CHANNEL_WEB_URL = "https://t.me/s/rahavard365"
LAST_ID_FILE = "last_rahavard_post_id.txt"

def get_last_processed_id():
    """خواندن شناسه عددی آخرین پیام ارسال‌شده"""
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return int(val) if val.isdigit() else 0
        except Exception:
            return 0
    return 0

def save_last_processed_id(msg_id):
    """ذخیره شناسه عددی آخرین پیام"""
    try:
        with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
            f.write(str(msg_id))
    except Exception as e:
        print(f"Error saving last ID: {e}")

def send_image(image_path, caption):
    """ارسال تصویر به کانال تلگرام و پیام‌رسان بله"""
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
                    timeout=45
                )
            if res.status_code == 200:
                print("Bale: Image sent successfully.")
            else:
                print(f"Bale error: {res.text}")
        except Exception as e:
            print(f"Bale exception: {e}")

def fetch_and_forward_all_images():
    print(f"Checking {CHANNEL_WEB_URL} for new image posts...")
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
    messages = soup.find_all("div", class_=re.compile(r"tgme_widget_message\b"))

    last_saved_id = get_last_processed_id()
    print(f"Last recorded Post ID: {last_saved_id}")

    # جمع‌آوری پست‌های جدید حاوی عکس
    new_posts = []

    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue
        try:
            msg_id = int(data_post.split("/")[-1])
        except ValueError:
            continue

        # فقط پست‌های بعد از آخرین ID ذخیره‌شده
        if last_saved_id > 0 and msg_id <= last_saved_id:
            continue

        # بررسی وجود تصویر در پست
        photo_el = msg.find("a", class_="tgme_widget_message_photo_wrap")
        if not photo_el:
            continue

        style = photo_el.get("style", "")
        match = re.search(r"background-image:url\('(.*?)'\)", style)
        if not match:
            continue

        img_url = match.group(1)
        text_el = msg.find("div", class_="tgme_widget_message_text")
        caption_text = text_el.get_text().strip() if text_el else ""

        new_posts.append({
            "id": msg_id,
            "img_url": img_url,
            "caption": caption_text
        })

    # مرتب‌سازی از قدیمی به جدید برای ارسال به ترتیب انتشار
    new_posts.sort(key=lambda x: x["id"])

    # در اولین اجرا اگر فایلی نبود، فقط آخرین عکس را ثبت/ارسال کن تا از ارسال یکباره ده‌ها پست قدیمی جلوگیری شود
    if last_saved_id == 0 and len(new_posts) > 1:
        new_posts = [new_posts[-1]]

    if not new_posts:
        print("No new image posts found.")
        return

    print(f"Found {len(new_posts)} new image post(s) to process.")

    highest_id = last_saved_id
    for post in new_posts:
        print(f"Processing Post #{post['id']}...")
        try:
            img_resp = requests.get(post["img_url"], headers=headers, timeout=30)
            if img_resp.status_code != 200:
                print(f"Failed to download image for post {post['id']}")
                continue

            temp_img_path = f"rahavard_{post['id']}.jpg"
            with open(temp_img_path, "wb") as f:
                f.write(img_resp.content)

            # قالب‌بندی کپشن با ذکر منبع
            full_caption = post["caption"]
            if full_caption:
                out_caption = f"{full_caption}\n\n📎 منبع: ره‌آورد ۳۶۵"
            else:
                out_caption = "📎 منبع: ره‌آورد ۳۶۵"

            if len(out_caption) > 1000:
                out_caption = out_caption[:990] + "..."

            send_image(temp_img_path, out_caption)

            # پاک‌سازی فایل محلی
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

            if post["id"] > highest_id:
                highest_id = post["id"]

        except Exception as err:
            print(f"Error processing post {post['id']}: {err}")

    # ذخیره بالاترین شناسه پردازش‌شده
    if highest_id > last_saved_id:
        save_last_processed_id(highest_id)
        print(f"Updated last post ID to {highest_id}")

if __name__ == "__main__":
    fetch_and_forward_all_images()
