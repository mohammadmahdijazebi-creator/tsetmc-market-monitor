import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# لیست کامل ۲۴ کانال تلگرام
CHANNELS = [
    {"username": "MarketSummary", "label": "خلاصه بازار"},
    {"username": "rahavard365", "label": "ره‌آورد ۳۶۵"},
    {"username": "rasadkhoneh", "label": "رصدخونه"},
    {"username": "parsistahlil", "label": "پارسیس تحلیل"},
    {"username": "MetaWave", "label": "متا ویو"},
    {"username": "dndir", "label": "دی ان دی"},
    {"username": "option_cofe", "label": "کافه آپشن"},
    {"username": "trade_fundd", "label": "ترید فاند"},
    {"username": "bourse24ir", "label": "بورس ۲۴"},
    {"username": "BourseNews", "label": "بورس نیوز"},
    {"username": "sena_news", "label": "سنا"},
    {"username": "sahamyab", "label": "سهام یاب"},
    {"username": "tsetmc_plus", "label": "تی اس ای پلاس"},
    {"username": "nabzebourse", "label": "نبض بورس"},
    {"username": "ecobourse", "label": "اکوبورس"},
    {"username": "boursepressir", "label": "بورس پرس"},
    {"username": "donya_e_eqtesad", "label": "دنیای اقتصاد"},
    {"username": "tejaratnews", "label": "تجارت نیوز"},
    {"username": "Farsna", "label": "فارس اقتصادی"},
    {"username": "EtemadOnline", "label": "اعتماد آنلاین"},
    {"username": "isna94", "label": "ایسنا اقتصادی"},
    {"username": "iribnews", "label": "خبرگزاری صداوسیما"},
    {"username": "Tasnimnews", "label": "تسنیم اقتصادی"},
    {"username": "Mehrnews", "label": "مهر اقتصادی"},
]

# کانال‌های یوتیوب
YOUTUBE_CHANNELS = [
    {"handle": "@feghtesad", "channel_id": "UCl6-kUbADci3ZSINUcRZJcA", "label": "اقتصاد"},
    {"handle": "@BashgahPol", "channel_id": "UCfix78juvP77pMnYO0fyhMA", "label": "باشگاه پول"},
    {"handle": "@aliichii-tube", "channel_id": "UCqUoY21eYkSj3-zEWB9gZHA", "label": "علیچی"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 30
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
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("channels", {})
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(channels_state):
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
    time_el = message_el.find("time")
    if time_el and time_el.get("datetime"):
        dt_str = time_el.get("datetime")
        try:
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


def parse_posts(messages, last_id, seen_ids):
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

        if msg_id in seen_ids:
            continue

        if last_id > 0 and msg_id <= last_id:
            continue

        msg_time = parse_post_time(msg)
        if last_id == 0:
            if not msg_time or msg_time < today_start:
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
        if res.status_code == 200:
            print(f"[{name}] تصویر با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال تصویر: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال تصویر: {e}")
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
        if res.status_code == 200:
            print(f"[{name}] پیام متنی با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال متن: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال متن: {e}")
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
            print(f"خطا در دریافت یا ارسال تصویر: {e}")
            # در صورت عدم موفقیت ارسال عکس، متن را ارسال کن
            r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
            r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
            results.extend([r1, r2])
        finally:
            temp_img.unlink(missing_ok=True)
    else:
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
        results.extend([r1, r2])

    time.sleep(1.5)
    return any(results)


def process_channel(chan_info, channels_state):
    username = chan_info["username"]
    label = chan_info["label"]

    chan_data = channels_state.get(username, {})
    if isinstance(chan_data, int):
        last_id = chan_data
        seen_ids = [last_id] if last_id > 0 else []
    else:
        last_id = int(chan_data.get("last_id", 0))
        seen_ids = list(chan_data.get("seen_ids", []))

    print(f"\n==========================================")
    print(f"بررسی Telegram @{username} ({label})")

    try:
        messages = fetch_channel_messages(username)
    except Exception as e:
        print(f"خطا در دریافت پیام‌های @{username}: {e}")
        return {"last_id": last_id, "seen_ids": seen_ids}

    posts = parse_posts(messages, last_id, seen_ids)
    if not posts:
        print("هیچ پیام جدیدی وجود ندارد.")
        return {"last_id": last_id, "seen_ids": seen_ids}

    new_last_id = last_id
    new_seen = list(seen_ids)

    for post in posts:
        print(f"در حال ارسال پیام شناسه {post['id']}...")
        ok = deliver_post(post, username, label)
        if ok or True:
            new_last_id = max(new_last_id, post["id"])
            if post["id"] not in new_seen:
                new_seen.append(post["id"])

    new_seen = new_seen[-100:]
    return {"last_id": new_last_id, "seen_ids": new_seen}


# ==================== بخش یوتیوب ====================

def resolve_youtube_channel_id(handle):
    try:
        url = f"https://www.youtube.com/{handle}"
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            m = re.search(r'href="https://www\.youtube\.com/channel/([^"]+)"', r.text)
            if m:
                return m.group(1)
            m = re.search(r'"channelId":"([^"]+)"', r.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def fetch_youtube_latest_video(channel_id, handle):
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        response = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404 and handle:
            real_id = resolve_youtube_channel_id(handle)
            if real_id and real_id != channel_id:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={real_id}"
                response = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            return None

        root = ET.fromstring(response.content)
        ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        entry = root.find("a:entry", ns)
        if entry is not None:
            vid = entry.find("yt:videoId", ns)
            title = entry.find("a:title", ns)
            if vid is not None:
                return {
                    "id": vid.text.strip(),
                    "title": title.text.strip() if title is not None else "ویدیو جدید"
                }
    except Exception as e:
        print(f"خطا در پردازش فید یوتیوب: {e}")
    return None


def process_youtube_channel(chan, channels_state):
    key = f"yt:{chan['handle']}"
    chan_data = channels_state.get(key, {})
    last_video_id = chan_data.get("last_video_id", "")

    print(f"\n==========================================")
    print(f"بررسی YouTube ({chan['label']} - {chan['handle']})")

    video = fetch_youtube_latest_video(chan["channel_id"], chan["handle"])
    if not video:
        print("هیچ ویدیویی یافت نشد.")
        return chan_data

    vid_id = video["id"]
    if vid_id == last_video_id:
        print("ویدیوی جدیدی منتشر نشده است.")
        return chan_data

    url = f"https://youtu.be/{vid_id}"
    message_text = f"🎬 {video['title']}\n\n🔗 {url}\n📺 منبع: YouTube ({chan['label']})"

    print(f"ارسال ویدیوی یوتیوب: {video['title']}")
    r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, message_text, "Telegram")
    r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, message_text, "Bale")

    if any([r1, r2]):
        return {"last_video_id": vid_id}

    return chan_data


def main():
    channels_state = load_state()

    # ۱. کانال‌های تلگرام
    for chan in CHANNELS:
        res = process_channel(chan, channels_state)
        channels_state[chan["username"]] = res
        save_state(channels_state)

    # ۲. کانال‌های یوتیوب
    for chan in YOUTUBE_CHANNELS:
        res = process_youtube_channel(chan, channels_state)
        channels_state[f"yt:{chan['handle']}"] = res
        save_state(channels_state)

    print("\nعملیات با موفقیت به پایان رسید.")


if __name__ == "__main__":
    main()
