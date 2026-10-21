import json
import os
import re
import subprocess
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

# سقف حجم تلگرام و بله
YOUTUBE_MAX_BYTES = 48 * 1024 * 1024  # 48 MB

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


# ==================== توابع ارسال به مقصدها ====================

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
            print(f"[{name}] تصویر کاور با موفقیت ارسال شد.")
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
            print(f"[{name}] فایل ویدیو با موفقیت ارسال شد.")
            return True
        else:
            print(f"[{name}] خطای ارسال ویدیو: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال ویدیو: {e}")
        return False


def send_audio_dest(endpoint, token, chat_id, audio_path, caption, title, performer, name):
    if not token or not chat_id:
        return False
    try:
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "title": title[:64] if title else "پادکست",
            "performer": performer[:64] if performer else "کانال یوتیوب"
        }
        with audio_path.open("rb") as f:
            res = requests.post(
                f"{endpoint}{token}/sendAudio",
                data=data,
                files={"audio": f},
                timeout=600,
            )
        if res.status_code == 200:
            print(f"[{name}] فایل صوتی (پادکست) با موفقیت ارسال شد.")
            return True
        else:
            with audio_path.open("rb") as f2:
                res_doc = requests.post(
                    f"{endpoint}{token}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": f2},
                    timeout=600,
                )
            if res_doc.status_code == 200:
                print(f"[{name}] فایل صوتی بصورت سند با موفقیت ارسال شد.")
                return True
            print(f"[{name}] خطای ارسال فایل صوتی: {res.text}")
            return False
    except Exception as e:
        print(f"[{name}] استثنا در ارسال صوت: {e}")
        return False


# ==================== دریافت و دانلود از یوتیوب ====================

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


def fetch_all_youtube_rss_videos(channel_id, handle):
    """لیست تمام ویدیوهای موجود در فید یوتیوب"""
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
            videos.append({
                "id": vid.text.strip(),
                "title": title.text.strip() if title is not None else "ویدیو جدید",
            })
        return videos
    except Exception as e:
        print(f"خطا در پردازش فید یوتیوب: {e}")
        return []


def download_stream_to_file(download_url, output_path, max_bytes):
    try:
        with requests.get(download_url, headers=HEADERS, stream=True, timeout=180) as r:
            r.raise_for_status()
            total = 0
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        total += len(chunk)
                        if total > max_bytes:
                            return False
                        f.write(chunk)
        if output_path.exists() and output_path.stat().st_size > 1024:
            return True
        return False
    except Exception:
        return False


def try_download_ytdlp(video_id, out_file, is_audio=False):
    """دانلود هوشمند با yt-dlp برای ویدیو کم‌حجم یا صوت"""
    if is_audio:
        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=tv_embedded,web_embedded",
            "--no-playlist",
            "-f", "ba/ba*/140/worst[ext=m4a]",
            "--max-filesize", "48M",
            "-o", str(out_file),
            f"https://www.youtube.com/watch?v={video_id}"
        ]
    else:
        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=tv_embedded,web_embedded",
            "--no-playlist",
            "-f", "b[filesize<48M]/w[filesize<48M]/18/worst[ext=mp4]",
            "--max-filesize", "48M",
            "-o", str(out_file),
            f"https://www.youtube.com/watch?v={video_id}"
        ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if p.returncode == 0 and out_file.exists() and out_file.stat().st_size > 1024:
            return True
    except Exception:
        pass
    return False


def get_media_via_piped(video_id, out_path, is_audio=False):
    """تلاش برای دانلود مستقیم از طریق سرورهای پایپد"""
    piped_instances = [
        "https://pipedapi.leptons.xyz",
        "https://api.piped.privacydev.net",
        "https://piped-api.lunar.icu",
        "https://pipedapi.drgns.space",
    ]
    for p_url in piped_instances:
        try:
            r = requests.get(f"{p_url}/streams/{video_id}", headers=HEADERS, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if is_audio:
                    streams = data.get("audioStreams", [])
                    if streams:
                        chosen = streams[-1].get("url")
                        if chosen and download_stream_to_file(chosen, out_path, YOUTUBE_MAX_BYTES):
                            return True
                else:
                    streams = data.get("videoStreams", [])
                    valid = [s for s in streams if s.get("format") == "MPEG_4" and not s.get("videoOnly", False) and s.get("url")]
                    if not valid:
                        valid = [s for s in streams if s.get("format") == "MPEG_4" and s.get("url")]
                    if valid:
                        chosen = valid[-1].get("url")
                        if chosen and download_stream_to_file(chosen, out_path, YOUTUBE_MAX_BYTES):
                            return True
        except Exception:
            continue
    return False


def deliver_youtube_media(video, label, handle):
    video_id = video["id"]
    title = video["title"]
    url = f"https://youtu.be/{video_id}"
    video_caption = f"🎬 {title}\n\n📺 منبع: YouTube ({label})\n🔗 {url}"
    if len(video_caption) > MAX_CAPTION_LENGTH:
        video_caption = video_caption[:MAX_CAPTION_LENGTH - 3].rstrip() + "..."

    # ۱. گام اول: تلاش برای دانلود و ارسال فایل ویدیو (زیر ۴۸ مگابایت)
    out_video = Path(f"yt_{video_id}.mp4")
    print("بررسی و دانلود فایل ویدیو (کمتر از ۴۸ مگابایت)...")
    has_video = try_download_ytdlp(video_id, out_video, is_audio=False) or get_media_via_piped(video_id, out_video, is_audio=False)
    
    if has_video and out_video.exists():
        try:
            size_mb = round(out_video.stat().st_size / (1024 * 1024), 2)
            print(f"ویدیو با حجم {size_mb} MB دانلود شد. در حال ارسال ویدیو...")
            r1 = send_video_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, out_video, video_caption, "Telegram")
            r2 = send_video_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, out_video, video_caption, "Bale")
            return any([r1, r2])
        finally:
            out_video.unlink(missing_ok=True)

    # ۲. گام دوم: اگر ویدیو سنگین بود (بیش از ۴۸ مگابایت)، صوت کامل آن (پادکست سبک) ارسال شود
    print("ویدیو بیش از ۴۸ مگابایت است یا لود نشد. در حال دریافت پادکست صوتی...")
    out_audio = Path(f"yt_audio_{video_id}.m4a")
    has_audio = try_download_ytdlp(video_id, out_audio, is_audio=True) or get_media_via_piped(video_id, out_audio, is_audio=True)
    
    if has_audio and out_audio.exists():
        try:
            audio_mb = round(out_audio.stat().st_size / (1024 * 1024), 2)
            print(f"صوت برنامه با حجم {audio_mb} MB آماده شد. در حال ارسال پادکست صوتی...")
            audio_caption = f"🎙 صوت کامل برنامه:\n{title}\n\n📺 منبع: YouTube ({label})\n🔗 {url}"
            if len(audio_caption) > MAX_CAPTION_LENGTH:
                audio_caption = audio_caption[:MAX_CAPTION_LENGTH - 3].rstrip() + "..."
            r1 = send_audio_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, out_audio, audio_caption, title, label, "Telegram")
            r2 = send_audio_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, out_audio, audio_caption, title, label, "Bale")
            return any([r1, r2])
        finally:
            out_audio.unlink(missing_ok=True)

    # ۳. گام سوم: فال‌بک کاور باکیفیت و لینک مستقیم
    print("ارسال کاور و لینک یوتیوب...")
    thumb_path = Path(f"thumb_{video_id}.jpg")
    try:
        thumb_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        r = requests.get(thumb_url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            thumb_path.write_bytes(r.content)
            r1 = send_photo_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, thumb_path, video_caption, "Telegram")
            r2 = send_photo_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, thumb_path, video_caption, "Bale")
            return any([r1, r2])
    except Exception:
        pass
    finally:
        thumb_path.unlink(missing_ok=True)

    # ۴. پیام متنی ساده در صورت نبود کاور
    r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, video_caption, "Telegram")
    r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, video_caption, "Bale")
    return any([r1, r2])


def process_youtube_channel(chan, channels_state):
    key = f"yt:{chan['handle']}"
    chan_data = channels_state.get(key, {})
    delivered_media_ids = chan_data.get("delivered_media_ids", [])
    seen_ids = chan_data.get("seen_ids", [])

    print(f"\n==========================================")
    print(f"بررسی YouTube ({chan['label']} - {chan['handle']})")

    videos = fetch_all_youtube_rss_videos(chan["channel_id"], chan["handle"])
    if not videos:
        print("هیچ ویدیویی در فید یافت نشد.")
        return chan_data

    # پیدا کردن آخرین ویدیویی که هنوز مدیا/پادکست آن فرستاده نشده است
    target_video = None
    for v in videos:
        if v["id"] not in delivered_media_ids:
            target_video = v
            break

    if not target_video:
        print("آخرین فیلم/پادکست قبلاً ارسال شده است و پیام جدیدی وجود ندارد.")
        return chan_data

    print(f"در حال پردازش آخرین ویدیو: {target_video['title']}")
    delivered = deliver_youtube_media(target_video, chan["label"], chan["handle"])

    if delivered:
        if target_video["id"] not in delivered_media_ids:
            delivered_media_ids.append(target_video["id"])
        if target_video["id"] not in seen_ids:
            seen_ids.append(target_video["id"])

    delivered_media_ids = delivered_media_ids[-50:]
    seen_ids = seen_ids[-50:]

    return {
        "last_video_id": target_video["id"],
        "delivered_media_ids": delivered_media_ids,
        "seen_ids": seen_ids,
    }


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
