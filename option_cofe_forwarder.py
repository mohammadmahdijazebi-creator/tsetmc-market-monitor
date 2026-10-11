import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# لیست کانال‌های تحت رصد (نام کاربری و برچسب نمایشی)
CHANNELS = [
    {"username": "option_cofe", "label": "کافه آپشن"},
    {"username": "MomeniMohsen", "label": "محسن مومنی"},
]

STATE_FILE = Path("option_cofe_state.json")
REQUEST_TIMEOUT = 45
MAX_CAPTION_LENGTH = 1024
MAX_TEXT_LENGTH = 4096

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def load_state():
    """خواندن وضعیت کانال‌ها با پشتیبانی از ساختار قبلی و چندکاناله"""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # سازگاری با فرمت قدیمی تک‌کاناله
        if "last_id" in data and not any(k in data for k in ["channels"]):
            return {"option_cofe": int(data.get("last_id", 0))}
        return data.get("channels", {})
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(channels_state):
    """ذخیره امن وضعیت تمام کانال‌ها"""
    temp = STATE_FILE.with_suffix(".tmp")
    data = {"channels": channels_state}
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(STATE_FILE)


def extract_image_url(photo_element):
    if not photo_element:
        return None
    style = photo_element.get("style", "")
    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
    return match.group(1) if match else None


def get_message_text(message_el):
    text_el = message_el.find("div", class_="tgme_widget_message_text")
    if not text_el:
        return ""
    return text_el.get_text("\n", strip=True)


def fetch_channel_messages(username):
    url = f"https://t.me/s/{username}"
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


def parse_posts(messages, last_id):
    posts = []
    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue

        try:
            msg_id = int(data_post.rsplit("/", 1)[-1])
        except ValueError:
            continue

        if msg_id <= last_id:
            continue

        photo_el = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
        image_url = extract_image_url(photo_el)
        text = get_message_text(msg)

        if not image_url and not text:
            continue

        posts.append({
            "id": msg_id,
            "image_url": image_url,
            "text": text,
        })

    return sorted(posts, key=lambda x: x["id"])


def format_content(text, username, label, is_photo=False):
    source_tag = f"📎 منبع: @{username} ({label})"
    full_text = f"{text}\n\n{source_tag}" if text else source_tag
    max_len = MAX_CAPTION_LENGTH if is_photo else MAX_TEXT_LENGTH

    if len(full_text) > max_len:
        full_text = full_text[: max_len - 3].rstrip() + "..."
    return full_text


def send_photo_dest(endpoint, token, chat_id, image_path, caption, name):
    if not token or not chat_id:
        return False
    try:
        with image_path.open("rb") as f:
            res = requests.post(
                f"{endpoint}{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f},
                timeout=REQUEST_TIMEOUT,
            )
        res.raise_for_status()
        print(f"[{name}] عکس ارسال شد.")
        return True
    except Exception as e:
        print(f"[{name}] خطا در ارسال عکس: {e}")
        return False


def send_message_dest(endpoint, token, chat_id, text, name):
    if not token or not chat_id:
        return False
    try:
        res = requests.post(
            f"{endpoint}{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        print(f"[{name}] پیام متنی ارسال شد.")
        return True
    except Exception as e:
        print(f"[{name}] خطا در ارسال متن: {e}")
        return False


def deliver_post(post, username, label):
    is_photo = bool(post["image_url"])
    caption_or_text = format_content(post["text"], username, label, is_photo=is_photo)
    results = []

    if is_photo:
        temp_img = Path(f"temp_{username}_{post['id']}.jpg")
        try:
            r = requests.get(post["image_url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            temp_img.write_bytes(r.content)

            r1 = send_photo_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, temp_img, caption_or_text, "Telegram")
            r2 = send_photo_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, temp_img, caption_or_text, "Bale")
            results.extend([r1, r2])
        except Exception as e:
            print(f"خطا در دانلود یا ارسال تصویر {post['id']}: {e}")
            return False
        finally:
            temp_img.unlink(missing_ok=True)
    else:
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
        results.extend([r1, r2])

    return any(results)


def process_channel(chan_info, channels_state):
    username = chan_info["username"]
    label = chan_info["label"]
    last_id = int(channels_state.get(username, 0))

    print(f"\n--- بررسی کانال @{username} ({label}) | آخرین شناسه: {last_id} ---")

    try:
        messages = fetch_channel_messages(username)
    except Exception as e:
        print(f"خطا در بارگذاری پیام‌های @{username}: {e}")
        return last_id

    # اگر بار اول است، شناسه آخرین پست فعلی را ذخیره می‌کنیم تا تاریخچه ارسال نشود
    if last_id == 0:
        latest_posts = parse_posts(messages, 0)
        latest_id = latest_posts[-1]["id"] if latest_posts else 0
        print(f"اجرای اول برای @{username}: شناسه {latest_id} ثبت شد. پست‌های جدید از این به بعد ارسال می‌شوند.")
        return latest_id

    posts = parse_posts(messages, last_id)
    new_last_id = last_id

    for post in posts:
        print(f"در حال پردازش پست {post['id']} از @{username}...")
        ok = deliver_post(post, username, label)
        if ok:
            new_last_id = max(new_last_id, post["id"])
        else:
            print(f"پست {post['id']} ارسال نشد.")

    return new_last_id


def main():
    channels_state = load_state()

    for chan in CHANNELS:
        new_id = process_channel(chan, channels_state)
        channels_state[chan["username"]] = new_id

    save_state(channels_state)
    print("\nپایان بررسی همه کانال‌ها. وضعیت ذخیره شد.")


if __name__ == "__main__":
    main()
