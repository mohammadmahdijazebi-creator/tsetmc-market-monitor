# -*- coding: utf-8 -*-
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# لیست ۲۴ کانال تحت رصد + دو کانال یوتیوب شما
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
    # دو لینک یوتیوب شما
    {"username": "feghtesad_yt", "label": "یوتیوب اقتصاد", "is_youtube": True, "url": "https://www.youtube.com/feghtesad"},
    {"username": "BashgahPol", "label": "باشگاه پول", "is_youtube": True, "url": "https://www.youtube.com/@BashgahPol"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 40
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
    """خواندن وضعیت و لیست پیام‌های ارسال‌شده قبلی"""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("channels", {})
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(channels_state):
    """ذخیره آنی وضعیت جهت پیشگیری از ارسال تکراری"""
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


def fetch_youtube_updates(yt_url, label):
    """رصد و دریافت آخرین ویدیوها/لینک‌های کانال یوتیوب"""
    posts = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(yt_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # استخراج ویدیوها یا لینک‌های جدید از صفحه یوتیوب
            for video in soup.find_all("a", {"id": "video-title"}):
                title = video.get("title", "").strip()
                href = video.get("href", "")
                if href and title:
                    full_link = f"https://www.youtube.com{href}" if href.startswith("/") else href
                    # استفاده از هش یا طول عنوان به عنوان شناسهتاکیدی یکتا
                    post_id = abs(hash(full_link)) % (10 ** 8)
                    posts.append({
                        "id": post_id,
                        "image_url": None,
                        "text": f"📺 ویدیوی جدید از {label}:\n*{title}*\n\n🔗 لینک تماشا:\n{full_link}"
                    })
    except Exception as e:
        print(f"خطا در بررسی کانال یوتیوب {yt_url}: {e}")
    return posts[:3]  # آخرین موارد جدید


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

        if msg_id in seen_ids or (last_id > 0 and msg_id <= last_id):
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
        return res.status_code == 200
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
        return res.status_code == 200
    except Exception as e:
        print(f"[{name}] استثنا در ارسال متن: {e}")
        return False


def deliver_post(post, username, label):
    is_photo = bool(post.get("image_url"))
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

    time.sleep(2)
    return any(results)


def process_channel(chan_info, channels_state):
    username = chan_info["username"]
    label = chan_info["label"]
    is_youtube = chan_info.get("is_youtube", False)

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
        if is_youtube:
            posts = fetch_youtube_updates(chan_info["url"], label)
            posts = [p for p in posts if p["id"] not in seen_ids and p["id"] > last_id]
        else:
            messages = fetch_channel_messages(username)
            posts = parse_posts(messages, last_id, seen_ids)
    except Exception as e:
        print(f"خطا در دریافت پیام‌های @{username}: {e}")
        return {"last_id": last_id, "seen_ids": seen_ids}

    if not posts:
        print(f"هیچ پیام جدیدی وجود ندارد.")
        return {"last_id": last_id, "seen_ids": seen_ids}

    print(f"تعداد {len(posts)} پیام تایید شده برای ارسال...")
    new_last_id = last_id
    new_seen = list(seen_ids)

    for post in posts:
        print(f"در حال ارسال پیام شناسه {post['id']}...")
        deliver_post(post, username, label)
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

    print("\nتمام کانال‌ها و منابع یوتیوب بررسی و فیلتر شدند. وضعیت نهایی ذخیره شد.")


if __name__ == "__main__":
    main()
