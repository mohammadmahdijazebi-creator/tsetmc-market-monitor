import os
import re
import json
import requests
from bs4 import BeautifulSoup

# دریافت توکن‌ها و شناسه‌های مقصد
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BALE_BOT_TOKEN = os.environ.get("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.environ.get("BALE_CHANNEL_ID")

STATE_FILE = "forwarder_state.json"

# لیست کانال‌های تحت پوشش
CHANNELS = [
    {"username": "rahavard365", "title": "ره‌آورد ۳۶۵"},
    {"username": "rasadkhoneh", "title": "رصدخونه"},
    {"username": "MarketSummary", "title": "خلاصه بازار"},
]

def load_state():
    """خواندن آخرین وضعیت شناسه‌های پردازش‌شده"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
    return {}

def save_state(state):
    """ذخیره وضعیت شناسه‌ها در قالب JSON"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")

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
                print(" -> Telegram: Sent successfully.")
            else:
                print(f" -> Telegram error: {res.text}")
        except Exception as e:
            print(f" -> Telegram exception: {e}")

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
                print(" -> Bale: Sent successfully.")
            else:
                print(f" -> Bale error: {res.text}")
        except Exception as e:
            print(f" -> Bale exception: {e}")

def process_channel(channel_info, state, headers):
    username = channel_info["username"]
    title = channel_info["title"]
    url = f"https://t.me/s/{username}"
    
    last_saved_id = int(state.get(username, 0))
    print(f"\nScanning @{username} ({title}) | Last processed ID: {last_saved_id}")

    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return

    if resp.status_code != 200:
        print(f"Failed loading @{username}, status: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    messages = soup.find_all("div", class_=re.compile(r"tgme_widget_message\b"))

    new_posts = []

    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue
        try:
            msg_id = int(data_post.split("/")[-1])
        except ValueError:
            continue

        # فیلتر پیام‌های قدیمی
        if last_saved_id > 0 and msg_id <= last_saved_id:
            continue

        # بررسی وجود عکس در پیام
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

    # مرتب‌سازی به ترتیب زمان انتشار (از قدیم به جدید)
    new_posts.sort(key=lambda x: x["id"])

    # جلوگیری از ارسال ناگهانی ده‌ها پست گذشته در اولین اجرا
    if last_saved_id == 0 and len(new_posts) > 1:
        new_posts = [new_posts[-1]]

    if not new_posts:
        print(f"No new images in @{username}.")
        return

    print(f"Found {len(new_posts)} new image(s) in @{username}.")

    highest_id = last_saved_id
    for post in new_posts:
        print(f"Posting image #{post['id']} from @{username}...")
        try:
            img_resp = requests.get(post["img_url"], headers=headers, timeout=30)
            if img_resp.status_code != 200:
                print(f"Download error on post {post['id']}")
                continue

            temp_img_path = f"temp_{username}_{post['id']}.jpg"
            with open(temp_img_path, "wb") as f:
                f.write(img_resp.content)

            # ساخت کپشن
            caption_body = post["caption"]
            if caption_body:
                final_caption = f"{caption_body}\n\n📎 منبع: @{username}"
            else:
                final_caption = f"📎 منبع: @{username} ({title})"

            if len(final_caption) > 1000:
                final_caption = final_caption[:990] + "..."

            send_image(temp_img_path, final_caption)

            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

            if post["id"] > highest_id:
                highest_id = post["id"]

        except Exception as err:
            print(f"Error handling post {post['id']}: {err}")

    if highest_id > last_saved_id:
        state[username] = highest_id

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    state = load_state()

    for ch in CHANNELS:
        process_channel(ch, state, headers)

    save_state(state)
    print("\nForwarder run completed.")

if __name__ == "__main__":
    main()
