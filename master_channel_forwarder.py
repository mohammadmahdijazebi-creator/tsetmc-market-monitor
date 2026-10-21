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
REQUEST_TIMEOUT = 45
MAX_CAPTION_LENGTH = 1024
MAX_TEXT_LENGTH = 4096

# تنظیمات ویدیو (محدودیت حجم تلگرام و بله ۵۰ مگابایت)
YOUTUBE_POLL = 1
YOUTUBE_MAX_BYTES = 48 * 1024 * 1024

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
            print(f"[{name}] پیام متنی ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال متن: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال متن: {e}")
        return False


def send_video_dest(endpoint, token, chat_id, video_path, caption, name):
    if not token or not chat_id:
        return False
    try:
        with video_path.open("rb") as f:
            res = requests.post(
                f"{endpoint}{token}/sendVideo",
                data={"chat_id": chat_id, "caption": caption, "supports_streaming": "true"},
                files={"video": f},
                timeout=600,
            )
        if res.status_code == 200:
            print(f"[{name}] ویدیو با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال ویدیو: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال ویدیو: {e}")
        return False


# ==================== توابع یوتیوب ====================

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


def fetch_youtube_rss_videos(channel_id, handle, last_video_id, seen_ids):
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        response = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404 and handle:
            real_id = resolve_youtube_channel_id(handle)
            if real_id and real_id != channel_id:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={real_id}"
                response = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            print(f"خطای دریافت فید RSS ({response.status_code})")
            return []

        root = ET.fromstring(response.content)
        ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

        videos = []
        for entry in root.findall("a:entry", ns):
            vid = entry.find("yt:videoId", ns)
            title = entry.find("a:title", ns)
            if vid is None:
                continue
            video_id = vid.text.strip()
            if video_id in seen_ids or (last_video_id and video_id == last_video_id):
                continue
            videos.append({
                "id": video_id,
                "title": title.text.strip() if title is not None else "ویدیو جدید",
            })
        return videos
    except Exception as e:
        print(f"خطا در پردازش فید یوتیوب: {e}")
        return []


def download_stream_to_file(download_url, output_path, max_bytes):
    try:
        # افزایش timeout دانلود و ذخیره بهینه
        with requests.get(download_url, headers=HEADERS, stream=True, timeout=180) as r:
            r.raise_for_status()
            total = 0
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        total += len(chunk)
                        if total > max_bytes:
                            print(f"حجم ویدیو ({round(total/(1024*1024), 1)}MB) بیش از سقف مجاز (۴۸ مگابایت) است.")
                            return False
                        f.write(chunk)
        if output_path.exists() and output_path.stat().st_size > 1024:
            return True
        return False
    except Exception as e:
        print(f"خطا در استریم دانلود: {e}")
        return False


def download_youtube_video_external(video_id):
    """
    دانلود مستقیم فایل ویدیویی از طریق سرورهای فعال Piped, Cobalt و Invidious
    """
    out_file = Path(f"yt_{video_id}.mp4")

    # ۱. سرورهای پایدار و فعال Piped API
    piped_instances = [
        "https://piped-api.lunar.icu",
        "https://api.piped.privacydev.net",
        "https://pipedapi.drgns.space",
        "https://pipedapi.leptons.xyz",
    ]
    for p_url in piped_instances:
        try:
            print(f"تلاش با سرور پایپد: {p_url}...")
            r = requests.get(f"{p_url}/streams/{video_id}", headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                streams = data.get("videoStreams", [])
                
                # ابتدا فرمت‌های MP4 ترکیبی (تصویر + صدا)
                progressive = [
                    s for s in streams 
                    if s.get("format") == "MPEG_4" and not s.get("videoOnly", False) and s.get("url")
                ]
                
                target_url = None
                if progressive:
                    target_url = progressive[0].get("url")
                elif streams:
                    # انتخاب ویدیوی کیفیت ۳۶۰ یا ۴۸۰
                    target_url = streams[0].get("url")

                if target_url and download_stream_to_file(target_url, out_file, YOUTUBE_MAX_BYTES):
                    return out_file, None
        except Exception:
            continue

    # ۲. سرورهای اینویدیوس (Invidious API)
    invidious_hosts = [
        "https://invidious.asir.dev",
        "https://yewtu.be",
        "https://invidious.nerdvpn.de",
        "https://inv.nadeko.net",
    ]
    for inv in invidious_hosts:
        try:
            print(f"تلاش با سرور اینویدیوس: {inv}...")
            r = requests.get(f"{inv}/api/v1/videos/{video_id}", headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                formats = data.get("formatStreams", [])
                # فرمت ۳۶۰p مناسب حجم کم و سازگاری با تلگرام
                for f in reversed(formats):
                    d_url = f.get("url")
                    if d_url and download_stream_to_file(d_url, out_file, YOUTUBE_MAX_BYTES):
                        return out_file, None
        except Exception:
            continue

    # ۳. سرورهای کبالت (Cobalt Instances)
    cobalt_hosts = [
        "https://api.cobalt.tools",
        "https://cobalt.api.sc",
        "https://cobalt-backend.canine.tools",
    ]
    for c_host in cobalt_hosts:
        try:
            print(f"تلاش با سرور کبالت: {c_host}...")
            payload = {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "videoQuality": "360",
                "downloadMode": "auto"
            }
            res = requests.post(
                f"{c_host}/",
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=18
            )
            if res.status_code == 200:
                resp_json = res.json()
                d_url = resp_json.get("url")
                if d_url and download_stream_to_file(d_url, out_file, YOUTUBE_MAX_BYTES):
                    return out_file, None
        except Exception:
            continue

    out_file.unlink(missing_ok=True)
    return None, "عدم دریافت استریم از سرورهای واسط"


def deliver_youtube_video(video, label, handle):
    video_id = video["id"]
    title = video["title"]
    url = f"https://youtu.be/{video_id}"
    caption = f"🎬 {title}\n\n📺 منبع: YouTube ({label})\n🔗 {url}"
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 3].rstrip() + "..."

    # ۱. تلاش برای دریافت و ارسال خود فایل ویدیو
    video_path, err = download_youtube_video_external(video_id)
    if video_path and video_path.exists():
        try:
            size_mb = round(video_path.stat().st_size / (1024 * 1024), 2)
            print(f"ویدیو با حجم {size_mb} MB دریافت شد. در حال ارسال ویدیوی کامل به تلگرام و بله...")
            r1 = send_video_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, video_path, caption, "Telegram")
            r2 = send_video_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, video_path, caption, "Bale")
            return any([r1, r2])
        finally:
            video_path.unlink(missing_ok=True)

    # ۲. در صورتی که تمام سرویس‌ها موقتاً آفلاین بودند، کاور و لینک ارسال می‌شود تا پیام از دست نرود
    print(f"دانلود فایل ویدیو ممکن نشد ({err}). ارسال تصویر کاور...")
    thumb_path = Path(f"thumb_{video_id}.jpg")
    try:
        thumb_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        r = requests.get(thumb_url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            thumb_path.write_bytes(r.content)
            r1 = send_photo_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, thumb_path, caption, "Telegram")
            r2 = send_photo_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, thumb_path, caption, "Bale")
            return any([r1, r2])
    except Exception:
        pass
    finally:
        thumb_path.unlink(missing_ok=True)

    # ۳. فال‌بک نهایی: ارسال متن
    r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption, "Telegram")
    r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption, "Bale")
    return any([r1, r2])


def process_youtube_channel(chan, channels_state):
    key = f"yt:{chan['handle']}"
    chan_data = channels_state.get(key, {})
    last_video_id = chan_data.get("last_video_id", "")
    seen_ids = chan_data.get("seen_ids", [])

    print(f"\n==========================================")
    print(f"بررسی YouTube ({chan['label']} - {chan['handle']})")

    videos = fetch_youtube_rss_videos(chan["channel_id"], chan["handle"], last_video_id, seen_ids)
    if not videos:
        print("هیچ ویدیوی جدیدی وجود ندارد.")
        return {"last_video_id": last_video_id, "seen_ids": seen_ids}

    new_last = last_video_id
    new_seen = list(seen_ids)

    for video in videos[:YOUTUBE_POLL]:
        print(f"در حال پردازش: {video['title']}")
        deliver_youtube_video(video, chan["label"], chan["handle"])
        new_last = video["id"]
        if video["id"] not in new_seen:
            new_seen.append(video["id"])

    new_seen = new_seen[-50:]
    return {"last_video_id": new_last, "seen_ids": new_seen}


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
            print(f"خطا در ارسال تصویر: {e}")
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
