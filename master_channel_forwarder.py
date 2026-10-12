import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# لیست هر ۸ کانال درخواستی با عناوین نمایشی
CHANNELS = [
    {"username": "MarketSummary", "label": "خلاصه بازار"},
    {"username": "rahavard365", "label": "ره‌آورد ۳۶۵"},
    {"username": "rasadkhoneh", "label": "رصدخونه"},
    {"username": "parsistahlil", "label": "پارسیس تحلیل"},
    {"username": "MetaWave", "label": "متا ویو"},
    {"username": "dndir", "label": "دی ان دی"},
    {"username": "option_cofe", "label": "کافه آپشن"},
    {"username": "trade_fundd", "label": "ترید فاند"},
]

STATE_FILE = Path("channels_state.json")
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

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def load_state():
    """خواندن وضعیت کانال‌ها"""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("channels", {})
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(channels_state):
    """ذخیره وضعیت تمام کانال‌ها"""
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


def parse_post_time(message_el):
    """استخراج زمان پیام به وقت محلی تهران"""
    time_el = message_el.find("time")
    if time_el and time_el.get("datetime"):
        dt_str = time_el.get("datetime")
        try:
            # فرمت نمونه: 2026-10-12T08:30:00+00:00
            dt = datetime.fromisoformat(dt_str)
            return dt.astimezone(TEHRAN_TZ)
        except Exception:
            pass
    return None


def fetch_channel_messages(username):
    url = f"https://t.me/s/{username}"
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


def parse_posts(messages, last_id):
    posts = []
    now_tehran = datetime.now(TEHRAN_TZ)
    today_start = now_tehran.replace(hour=0, minute=0, second=0, microsecond=0)

    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue

        try:
            msg_id = int(data_post.rsplit("/", 1)[-1])
        except ValueError:
            continue

        msg_time = parse_post_time(msg)

        # اگر برای بار اول است (last_id == 0)، فقط پیام‌های امروز ثبت و ارسال شوند
        if last_id == 0:
            if not msg_time or msg_time < today_start:
                continue
        else:
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
        print(f"[{name}] تصویر با موفقیت ارسال شد.")
        return True
    except Exception as e:
        print(f"[{name}] خطا در ارسال تصویر: {e}")
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
        print(f"[{name}] پیام متنی با موفقیت ارسال شد.")
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
            print(f"خطا در دانلود یا فوروارد تصویر {post['id']}: {e}")
            return False
        finally:
            temp_img.unlink(missing_ok=True)
    else:
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
        results.extend([r1, r2])

    time.sleep(1.5)  # تاخیر کوتاه برای پیشگیری از لیمیت شدن
    return any(results)


def process_channel(chan_info, channels_state):
    username = chan_info["username"]
    label = chan_info["label"]
    last_id = int(channels_state.get(username, 0))

    print(f"\n==========================================")
    print(f"در حال بررسی کانال @{username} ({label}) | آخرین شناسه: {last_id}")

    try:
        messages = fetch_channel_messages(username)
    except Exception as e:
        print(f"خطا در دریافت پیام‌های @{username}: {e}")
        return last_id

    posts = parse_posts(messages, last_id)
    if not posts:
        print(f"هیچ پیام جدیدی برای @{username} یافت نشد.")
        return last_id

    print(f"تعداد {len(posts)} پیام جدید/امروز برای ارسال پیدا شد.")
    new_last_id = last_id

    for post in posts:
        print(f"ارسال پست شناسه {post['id']}...")
        ok = deliver_post(post, username, label)
        if ok:
            new_last_id = max(new_last_id, post["id"])

    return new_last_id


def main():
    channels_state = load_state()

    for chan in CHANNELS:
        new_id = process_channel(chan, channels_state)
        channels_state[chan["username"]] = new_id

    save_state(channels_state)
    print("\nعملیات با موفقیت پایان یافت و وضعیت ذخیره گردید.")


if __name__ == "__main__":
    main()
