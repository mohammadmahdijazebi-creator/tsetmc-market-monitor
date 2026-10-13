import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# لیست ۲۴ کانال تحت رصد
CHANNELS = [
    {"username": "MetaWave", "label": "متا ویو"},
    {"username": "rasadkhoneh", "label": "رصدخونه"},
    {"username": "MarketSummary", "label": "خلاصه بازار"},
    {"username": "shirazneowave", "label": "شیراز نئوویو"},
    {"username": "option_cofe", "label": "کافه آپشن"},
    {"username": "rahavard365", "label": "ره‌آورد ۳۶۵"},
    {"username": "etfplus", "label": "ای تی اف پلاس"},
    {"username": "trade_fundd", "label": "ترید فاند"},
    {"username": "NoavaranAmin", "label": "نوآوران امین"},
    {"username": "feghtesad", "label": "فردای اقتصاد"},
    {"username": "bourse_traderir", "label": "بورس تریدر"},
    {"username": "fundvesting", "label": "فاندوستینگ"},
    {"username": "MomeniMohsen", "label": "محسن مومنی"},
    {"username": "DataTechnical", "label": "دیتا تکنیکال"},
    {"username": "option_school", "label": "مدرسه آپشن"},
    {"username": "NerkhTv1", "label": "نرخ تی‌وی"},
    {"username": "navidacademy_option", "label": "آکادمی نوید"},
    {"username": "AgahMoshaver", "label": "آگاه مشاور"},
    {"username": "dndir", "label": "دی ان دی"},
    {"username": "boursetrader24", "label": "بورس تریدر ۲۴"},
    {"username": "fundation_analyst", "label": "تحلیل فاندامنتال"},
    {"username": "betasahm1", "label": "بتا سهم"},
    {"username": "pishrobroker", "label": "کارگزاری پیشرو"},
    {"username": "ebi_hajiahmadi_Official", "label": "ابراهیم حاجی احمدی"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 50
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
    """خواندن وضعیت و شناسه‌های پیام‌های قبلی"""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("channels", {})
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(channels_state):
    """ذخیره آنی وضعیت جهت پیشگیری از ارسال مجدد"""
    temp = STATE_FILE.with_suffix(".tmp")
    data = {"channels": channels_state}
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(STATE_FILE)


def extract_media(msg_el):
    """استخراج تصویر، ویدیو یا فایل صوتی از تگ‌های تلگرام وب"""
    media_type = None
    media_url = None

    # ۱. بررسی ویدیو
    video_el = msg_el.find("video")
    if video_el and video_el.get("src"):
        return "video", video_el.get("src")

    # ۲. بررسی فایل صوتی یا ویس
    audio_el = msg_el.find("audio")
    if audio_el and audio_el.get("src"):
        return "audio", audio_el.get("src")

    # ۳. بررسی تصویر
    photo_el = msg_el.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
    if photo_el:
        style = photo_el.get("style", "")
        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            return "photo", match.group(1)

    return media_type, media_url


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

        media_type, media_url = extract_media(msg)
        text = get_message_text(msg)

        if not media_url and not text:
            continue

        posts.append({
            "id": msg_id,
            "media_type": media_type,
            "media_url": media_url,
            "text": text,
        })

    return sorted(posts, key=lambda x: x["id"])


def format_content(text, username, label, has_media=False):
    source_tag = f"📎 منبع: @{username} ({label})"
    full_text = f"{text}\n\n{source_tag}" if text else source_tag
    max_len = MAX_CAPTION_LENGTH if has_media else MAX_TEXT_LENGTH

    if len(full_text) > max_len:
        full_text = full_text[: max_len - 3].rstrip() + "..."
    return full_text


def send_file_dest(endpoint, token, chat_id, file_path, caption, method_name, file_field, target_name):
    """متد عمومی برای ارسال عکس، ویدیو، یا صدا به تلگرام و بله"""
    if not token or not chat_id:
        return False
    try:
        url = f"{endpoint}{token}/{method_name}"
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption

        with file_path.open("rb") as f:
            files = {file_field: f}
            res = requests.post(url, data=data, files=files, timeout=REQUEST_TIMEOUT)

        if res.status_code == 200:
            print(f"[{target_name}] فایل ({method_name}) با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{target_name}] خطای ارسال {method_name}: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"[{target_name}] خطا در ارسال فایل: {e}")
        return False


def send_message_dest(endpoint, token, chat_id, text, target_name):
    if not token or not chat_id:
        return False
    try:
        url = f"{endpoint}{token}/sendMessage"
        res = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            print(f"[{target_name}] پیام متنی ارسال شد.")
            return True
        else:
            print(f"[{target_name}] خطای ارسال متن: {res.text}")
            return False
    except Exception as e:
        print(f"[{target_name}] خطا در ارتباط با {target_name}: {e}")
        return False


def deliver_post(post, username, label):
    has_media = bool(post["media_url"])
    caption_or_text = format_content(post["text"], username, label, has_media=has_media)
    results = []

    if has_media:
        m_type = post["media_type"]
        ext = ".jpg" if m_type == "photo" else (".mp4" if m_type == "video" else ".mp3")
        temp_file = Path(f"temp_{username}_{post['id']}{ext}")

        try:
            r = requests.get(post["media_url"], headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
            r.raise_for_status()
            with open(temp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)

            # ارسال متناسب با نوع فایل
            if m_type == "photo":
                r1 = send_file_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, temp_file, caption_or_text, "sendPhoto", "photo", "Telegram")
                r2 = send_file_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, temp_file, caption_or_text, "sendPhoto", "photo", "Bale")
            elif m_type == "video":
                r1 = send_file_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, temp_file, caption_or_text, "sendVideo", "video", "Telegram")
                r2 = send_file_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, temp_file, caption_or_text, "sendVideo", "video", "Bale")
            elif m_type == "audio":
                r1 = send_file_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, temp_file, caption_or_text, "sendAudio", "audio", "Telegram")
                r2 = send_file_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, temp_file, caption_or_text, "sendAudio", "audio", "Bale")
            else:
                r1, r2 = False, False

            results.extend([r1, r2])
        except Exception as e:
            print(f"خطا در دانلود یا فوروارد مدیا {post['id']}: {e}")
            return False
        finally:
            temp_file.unlink(missing_ok=True)
    else:
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
        results.extend([r1, r2])

    time.sleep(2)  # وقفه ۲ ثانیه‌ای برای کنترل نرخ ارسال
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
        seen_ids = chan_data.get("seen_ids", [])

    print(f"\n==========================================")
    print(f"بررسی @{username} ({label}) | آخرین شناسه: {last_id}")

    try:
        messages = fetch_channel_messages(username)
    except Exception as e:
        print(f"خطا در دریافت پیام‌های @{username}: {e}")
        return {"last_id": last_id, "seen_ids": seen_ids}

    posts = parse_posts(messages, last_id, seen_ids)
    if not posts:
        print(f"هیچ پیام جدیدی وجود ندارد.")
        return {"last_id": last_id, "seen_ids": seen_ids}

    print(f"تعداد {len(posts)} پیام تایید شده برای ارسال...")
    new_last_id = last_id
    new_seen = list(seen_ids)

    for post in posts:
        print(f"در حال ارسال پیام شناسه {post['id']} (نوع: {post['media_type'] or 'متن'})...")
        ok = deliver_post(post, username, label)
        new_last_id = max(new_last_id, post["id"])
        if post["id"] not in new_seen:
            new_seen.append(post["id"])

    new_seen = new_seen[-100:]
    return {"last_id": new_last_id, "seen_ids": new_seen}


def main():
    channels_state = load_state()

    for chan in CHANNELS:
        res = process_channel(chan, channels_state)
        channels_state[chan["username"]] = res
        save_state(channels_state)

    print("\nتمام کانال‌ها بررسی و فیلتر شدند. وضعیت ذخیره شد.")


if __name__ == "__main__":
    main()
