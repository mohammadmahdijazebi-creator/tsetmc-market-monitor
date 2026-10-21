import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# فقط کانال‌های مدنظر شما (بدون اضافه/کم)
CHANNELS = [
    {"username": "bourse24ir", "label": "بورس ۲۴"},
    {"username": "tejaratnews", "label": "تجارت نیوز"},
    {"username": "MarketSummary", "label": "خلاصه بازار"},
    {"username": "rahavard365", "label": "ره‌آورد ۳۶۵"},
    {"username": "etfplus", "label": "ETF Plus"},
    {"username": "rasadkhoneh", "label": "رصدخونه"},
    {"username": "parsistahlil", "label": "پارسیس تحلیل"},
    {"username": "pouyanbrokerage", "label": "پویان کارگزاری"},
    {"username": "Mehdiafzaliaan", "label": "مهدی افضلیان"},
    {"username": "option_school", "label": "Option School"},
    {"username": "dndir", "label": "دی ان دی"},
    {"username": "option_cofe", "label": "کافه آپشن"},
    {"username": "trade_fundd", "label": "ترید فاند"},
    {"username": "donya_e_eqtesad", "label": "دنیای اقتصاد"},
    {"username": "shirazneowave", "label": "شیراز نئوویو"},
    {"username": "bourse_traderir", "label": "Bourse Trader"},
    {"username": "pishrobroker", "label": "پیشرو بروکر"},
    {"username": "DataTechnical", "label": "Data Technical"},
    {"username": "MomeniMohsen", "label": "محسن مومنی"},
    {"username": "bamdad_institute", "label": "موسسه بامداد"},
    {"username": "kiancasts", "label": "KianCasts"},
    {"username": "feghtesad", "label": "فقط اقتصاد (تلگرام)"},
    {"username": "MetaWave", "label": "متا ویو"},
    {"username": "NoavaranAmin", "label": "نوآوران امین"},
    {"username": "ebi_hajiahmadi_Official", "label": "ابی حاجی احمدی"},
    {"username": "StockArk", "label": "StockArk"},
    {"username": "OptionBaaz", "label": "OptionBaaz"},
    {"username": "AgahMoshaver", "label": "آگاه مشاور"},
    {"username": "lamozsh_borsl", "label": "آموزش بورس"},
    {"username": "betasahm1", "label": "بتاسهم"},
    {"username": "NAVSTOCK", "label": "NAVSTOCK"},
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
    tmp = STATE_FILE.with_suffix(".tmp")
    data = {"channels": channels_state}
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def extract_image_url(photo_element):
    if not photo_element:
        return None
    style = photo_element.get("style", "")
    m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
    return m.group(1) if m else None


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
            return None
    return None


def fetch_channel_messages(username):
    url = f"https://t.me/s/{username}"
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    # بعضی مواقع صفحه 200 می‌دهد اما محتوا "channel is private" یا ... است
    r.raise_for_status()
    return r.text


def parse_messages_html(html):
    soup = BeautifulSoup(html, "html.parser")
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

        # جلوگیری از تکرار
        if msg_id in seen_ids:
            continue
        if last_id > 0 and msg_id <= last_id:
            continue

        # اجرای اول: فقط از امروز
        if last_id == 0:
            msg_time = parse_post_time(msg)
            if not msg_time or msg_time < today_start:
                continue

        photo_el = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
        image_url = extract_image_url(photo_el)
        text = get_message_text(msg)

        # اگر هیچ چیز نداشت
        if not image_url and not text:
            continue

        posts.append({"id": msg_id, "image_url": image_url, "text": text})

    return sorted(posts, key=lambda x: x["id"])


def format_content(text, username, label, is_photo=False):
    source_tag = f"📎 منبع: @{username} ({label})"
    full = f"{text}\n\n{source_tag}" if text else source_tag
    max_len = MAX_CAPTION_LENGTH if is_photo else MAX_TEXT_LENGTH
    if len(full) > max_len:
        full = full[: max_len - 3].rstrip() + "..."
    return full


def send_photo(endpoint, token, chat_id, image_bytes, caption, name):
    if not token or not chat_id:
        return False
    try:
        files = {"photo": ("image.jpg", image_bytes)}
        data = {"chat_id": chat_id, "caption": caption}
        res = requests.post(f"{endpoint}{token}/sendPhoto", data=data, files=files, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            print(f"[{name}] ارسال عکس OK")
            return True
        print(f"[{name}] خطای ارسال عکس: {res.text}")
        return False
    except Exception as e:
        print(f"[{name}] استثنا ارسال عکس: {e}")
        return False


def send_message(endpoint, token, chat_id, text, name):
    if not token or not chat_id:
        return False
    try:
        data = {"chat_id": chat_id, "text": text}
        res = requests.post(f"{endpoint}{token}/sendMessage", data=data, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            print(f"[{name}] ارسال متن OK")
            return True
        print(f"[{name}] خطای ارسال متن: {res.text}")
        return False
    except Exception as e:
        print(f"[{name}] استثنا ارسال متن: {e}")
        return False


def deliver_post(post, username, label):
    is_photo = bool(post["image_url"])
    content = format_content(post["text"], username, label, is_photo=is_photo)

    ok_any = False

    if is_photo:
        try:
            img = requests.get(post["image_url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            img.raise_for_status()
            img_bytes = img.content
        except Exception as e:
            print(f"خطا در دانلود عکس @{username}/{post['id']}: {e}")
            img_bytes = None

        if img_bytes:
            ok1 = send_photo("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, img_bytes, content, "Telegram")
            ok2 = send_photo("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, img_bytes, content, "Bale")
            ok_any = ok1 or ok2
        else:
            ok1 = send_message("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, content, "Telegram")
            ok2 = send_message("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, content, "Bale")
            ok_any = ok1 or ok2
    else:
        ok1 = send_message("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, content, "Telegram")
        ok2 = send_message("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, content, "Bale")
        ok_any = ok1 or ok2

    time.sleep(1.2)
    return ok_any


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

    print("\n==========================================")
    print(f"بررسی Telegram @{username} ({label}) | last_id={last_id}")

    try:
        html = fetch_channel_messages(username)
        messages = parse_messages_html(html)

        # اگر صفحه چیزی شبیه Access Denied/Private داشت، لاگ بده
        if "Access Denied" in html or "access denied" in html.lower():
            print(f"⚠️ @{username}: Access Denied")
        if "If you have Telegram" in html and len(messages) == 0:
            print(f"⚠️ @{username}: احتمالاً private/blocked یا HTML غیرقابل‌خواندن")

    except Exception as e:
        print(f"خطا در دریافت @{username}: {e}")
        return {"last_id": last_id, "seen_ids": seen_ids}

    posts = parse_posts(messages, last_id, seen_ids)
    if not posts:
        print("هیچ پیام جدیدی وجود ندارد.")
        return {"last_id": last_id, "seen_ids": seen_ids}

    new_last_id = last_id
    new_seen = list(seen_ids)

    for post in posts:
        print(f"ارسال @{username} پیام {post['id']} ...")
        ok = deliver_post(post, username, label)

        # فقط اگر واقعاً ارسال شد، وضعیت جلو برود
        if ok:
            new_last_id = max(new_last_id, post["id"])
            if post["id"] not in new_seen:
                new_seen.append(post["id"])
        else:
            print(f"⚠️ ارسال ناموفق @{username}/{post['id']} -> last_id جلو نرفت")

    new_seen = new_seen[-200:]
    return {"last_id": new_last_id, "seen_ids": new_seen}


def main():
    channels_state = load_state()

    for chan in CHANNELS:
        res = process_channel(chan, channels_state)
        channels_state[chan["username"]] = res
        save_state(channels_state)

    print("\nپایان.")


if __name__ == "__main__":
    main()
