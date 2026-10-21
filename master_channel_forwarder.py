import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# لیست کانال‌های تلگرام
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

# کانال‌های یوتیوب
YOUTUBE_CHANNELS = [
    {"handle": "@feghtesad", "channel_id": "UCl6-kUbADci3ZSINUcRZJcA", "label": "اقتصاد"},
    {"handle": "@BashgahPol", "channel_id": "UCfix78juvP77pMnYO0fyhMA", "label": "باشگاه پول"},
    {"handle": "@aliichii-tube", "channel_id": "UCqUoY21eYkSj3-zEWB9gZHA", "label": "علیچی"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 30
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


def send_message_dest(endpoint, token, chat_id, text, name):
    if not token or not chat_id:
        return False
    try:
        res = requests.post(
            f"{endpoint}{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "disable_web_page_preview": "false"},
            timeout=REQUEST_TIMEOUT,
        )
        if res.status_code == 200:
            print(f"[{name}] پیام با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال پیام: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال پیام: {e}")
        return False


# ==================== بخش تلگرام ====================

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


def process_telegram_channel(chan, channels_state):
    username = chan["username"]
    label = chan["label"]

    chan_data = channels_state.get(username, {})
    if isinstance(chan_data, int):
        last_id = chan_data
    else:
        last_id = int(chan_data.get("last_id", 0))

    print(f"\n==========================================")
    print(f"بررسی Telegram @{username} ({label})")

    try:
        messages = fetch_channel_messages(username)
    except Exception as e:
        print(f"خطا در دریافت پیام‌های @{username}: {e}")
        return {"last_id": last_id}

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

        if last_id > 0 and msg_id <= last_id:
            continue
        if last_id == 0:
            msg_time = parse_post_time(msg)
            if not msg_time or msg_time < today_start:
                continue

        text = get_message_text(msg)
        post_link = f"https://t.me/{username}/{msg_id}"
        
        posts.append({
            "id": msg_id,
            "text": text,
            "link": post_link
        })

    posts = sorted(posts, key=lambda x: x["id"])
    if not posts:
        print("هیچ پیام جدیدی وجود ندارد.")
        return {"last_id": last_id}

    new_last_id = last_id
    for post in posts:
        content = f"{post['text']}\n\n🔗 {post['link']}\n📎 منبع: @{username} ({label})" if post['text'] else f"🔗 {post['link']}\n📎 منبع: @{username} ({label})"
        
        if len(content) > MAX_TEXT_LENGTH:
            content = content[:MAX_TEXT_LENGTH - 3].rstrip() + "..."

        print(f"در حال ارسال پیام شناسه {post['id']}...")
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, content, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, content, "Bale")
        
        if any([r1, r2]):
            new_last_id = max(new_last_id, post["id"])

    return {"last_id": new_last_id}


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
            print(f"خطای دریافت فید RSS یوتیوب ({response.status_code})")
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

    print(f"ارسال آخرین ویدیوی یوتیوب: {video['title']}")
    r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, message_text, "Telegram")
    r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, message_text, "Bale")

    if any([r1, r2]):
        return {"last_video_id": vid_id}

    return chan_data


def main():
    channels_state = load_state()

    # ۱. کانال‌های تلگرام
    for chan in CHANNELS:
        res = process_telegram_channel(chan, channels_state)
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
