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
import yt_dlp

# ==========================================
# پیکربندی و لیست منابع
# ==========================================
CHANNELS = [
    # ۲۴ کانال بورسی تلگرام
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
    
    # ۳ کانال یوتیوب درخواستی
    {"username": "yt_feghtesad", "label": "یوتیوب فردای اقتصاد", "is_youtube": True, "url": "https://www.youtube.com/feghtesad"},
    {"username": "yt_BashgahPol", "label": "باشگاه پول", "is_youtube": True, "url": "https://www.youtube.com/@BashgahPol"},
    {"username": "yt_aliichii", "label": "Aliichii Tube", "is_youtube": True, "url": "https://www.youtube.com/@aliichii-tube"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 50
MAX_CAPTION_LENGTH = 1000
MAX_TEXT_LENGTH = 4000
MAX_FILE_SIZE_MB = 48  # محدودیت مجاز تلگرام و بله برای آپلود استاندارد

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


# ==========================================
# مدیریت وضعیت (State)
# ==========================================
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
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


# ==========================================
# ارسال به پیام‌رسان‌ها (تلگرام و بله)
# ==========================================
def send_telegram(endpoint_method, data, files=None):
    if not BOT_TOKEN or not CHANNEL_ID:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint_method}"
    data["chat_id"] = CHANNEL_ID
    try:
        r = requests.post(url, data=data, files=files, timeout=120)
        if r.status_code == 200:
            print("Telegram: ارسال موفق")
            return True
        print(f"Telegram Error ({endpoint_method}): {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Telegram Exception ({endpoint_method}): {e}")
    return False


def send_bale(endpoint_method, data, files=None):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return False
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/{endpoint_method}"
    data["chat_id"] = BALE_CHANNEL_ID
    try:
        r = requests.post(url, data=data, files=files, timeout=120)
        if r.status_code == 200:
            print("Bale: ارسال موفق")
            return True
        print(f"Bale Error ({endpoint_method}): {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Bale Exception ({endpoint_method}): {e}")
    return False


def broadcast_message(text):
    t_ok = send_telegram("sendMessage", {"text": text})
    b_ok = send_bale("sendMessage", {"text": text})
    return t_ok or b_ok


def broadcast_photo(image_path, caption):
    t_ok = False
    b_ok = False
    with open(image_path, "rb") as f:
        t_ok = send_telegram("sendPhoto", {"caption": caption}, files={"photo": f})
    with open(image_path, "rb") as f:
        b_ok = send_bale("sendPhoto", {"caption": caption}, files={"photo": f})
    return t_ok or b_ok


def broadcast_video(video_path, caption):
    t_ok = False
    b_ok = False
    with open(video_path, "rb") as f:
        t_ok = send_telegram("sendVideo", {"caption": caption, "supports_streaming": "true"}, files={"video": f})
    with open(video_path, "rb") as f:
        # در بله چنانچه sendVideo پاسخ نداد، به عنوان sendDocument نیز امتحان می‌شود
        b_ok = send_bale("sendVideo", {"caption": caption}, files={"video": f})
        if not b_ok:
            f.seek(0)
            b_ok = send_bale("sendDocument", {"caption": caption}, files={"document": f})
    return t_ok or b_ok


def broadcast_document(doc_path, caption):
    t_ok = False
    b_ok = False
    with open(doc_path, "rb") as f:
        t_ok = send_telegram("sendDocument", {"caption": caption}, files={"document": f})
    with open(doc_path, "rb") as f:
        b_ok = send_bale("sendDocument", {"caption": caption}, files={"document": f})
    return t_ok or b_ok


# ==========================================
# دانلود هوشمند ویدیو از یوتیوب با yt-dlp
# ==========================================
def download_youtube_video(video_url, output_prefix):
    """
    دانلود بهینه‌سازی شده ویدیو با فرمت mp4 و زیر ۴۸ مگابایت
    """
    out_tmpl = f"{output_prefix}.%(ext)s"
    ydl_opts = {
        # تلاش برای دریافت ویدیو زیر سقف ۴۸ مگابایت تا در تلگرام و بله خطا ندهد
        "format": "best[filesize<48M]/bestvideo[height<=480][filesize<40M]+bestaudio/best[height<=480]/worst",
        "outtmpl": out_tmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 60,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            # اگر فرمت مرج شده mp4 باشد
            p_mp4 = Path(filename).with_suffix(".mp4")
            if p_mp4.exists():
                return p_mp4
            p_orig = Path(filename)
            if p_orig.exists():
                return p_orig
    except Exception as e:
        print(f"خطا در دانلود ویدیو یوتیوب با yt-dlp: {e}")
    return None


# ==========================================
# استخراج و رصد یوتیوب (از طریق RSS کانال)
# ==========================================
def get_youtube_channel_id(yt_url):
    """استخراج channel_id از آدرس کانال با هندل یا نام یوتیوب"""
    try:
        res = requests.get(yt_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            m = re.search(r'property="og:url"\s+content="https://www\.youtube\.com/channel/(UC[\w-]+)"', res.text)
            if m:
                return m.group(1)
            m2 = re.search(r'"channelId":"(UC[\w-]+)"', res.text)
            if m2:
                return m2.group(1)
            m3 = re.search(r'(UC[\w-]{20,})', res.text)
            if m3:
                return m3.group(1)
    except Exception as e:
        print(f"خطا در دریافت channel_id یوتیوب: {e}")
    return None


def fetch_youtube_updates(yt_url, label, seen_ids):
    posts = []
    cid = get_youtube_channel_id(yt_url)
    if not cid:
        print(f"کانال یوتیوب {label} شناسایی نشد.")
        return []

    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    try:
        r = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "xml")
            entries = soup.find_all("entry")
            for ent in entries[:3]:  # ۳ ویدیوی اخیر
                vid_el = ent.find("yt:videoId")
                title_el = ent.find("title")
                if not vid_el or not title_el:
                    continue
                vid = vid_el.get_text(strip=True)
                title = title_el.get_text(strip=True)
                
                # تبدیل شناسه به عدد برای هماهنگی با State
                post_id = abs(hash(vid)) % (10 ** 8)
                if post_id in seen_ids:
                    continue

                video_link = f"https://www.youtube.com/watch?v={vid}"
                posts.append({
                    "id": post_id,
                    "type": "youtube_video",
                    "title": title,
                    "url": video_link,
                    "text": f"🎬 ویدیوی جدید از {label}:\n*{title}*\n\n🔗 لینک تماشا:\n{video_link}"
                })
    except Exception as e:
        print(f"خطا در خواندن فید یوتیوب {label}: {e}")
    return posts


# ==========================================
# استخراج پیام‌ها از تلگرام (Web Preview)
# ==========================================
def extract_media_from_tg_msg(msg):
    """تشخیص نوع فایل (عکس، ویدیو، داکیومنت) و لینک دانلود"""
    # ۱. تصویر
    photo_wrap = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
    if photo_wrap:
        style = photo_wrap.get("style", "")
        m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if m:
            return "photo", m.group(1), None

    # ۲. ویدیو
    video_tag = msg.find("video")
    if video_tag and video_tag.get("src"):
        return "video", video_tag.get("src"), None

    # ۳. سند، فایل زیپ یا پی‌دی‌اف
    doc_wrap = msg.find("a", class_=re.compile(r"\btgme_widget_message_document_wrap\b"))
    if doc_wrap:
        doc_url = doc_wrap.get("href")
        title_el = msg.find("div", class_=re.compile(r"\btgme_widget_message_document_title\b"))
        file_name = title_el.get_text(strip=True) if title_el else "file"
        return "document", doc_url, file_name

    return "text", None, None


def fetch_channel_messages(username):
    url = f"https://t.me/s/{username}"
    res = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


def parse_telegram_posts(messages, last_id, seen_ids):
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

        time_el = msg.find("time")
        if last_id == 0 and time_el and time_el.get("datetime"):
            try:
                dt = datetime.fromisoformat(time_el.get("datetime")).astimezone(TEHRAN_TZ)
                if dt < today_start:
                    continue
            except Exception:
                pass

        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text("\n", strip=True) if text_el else ""
        media_type, media_url, filename = extract_media_from_tg_msg(msg)

        if not text and not media_url:
            continue

        posts.append({
            "id": msg_id,
            "type": media_type,
            "url": media_url,
            "filename": filename,
            "text": text,
        })

    return sorted(posts, key=lambda x: x["id"])


# ==========================================
# ارسال محتواها به همراه فایل
# ==========================================
def deliver_post(post, username, label):
    source_tag = f"📎 منبع: @{username} ({label})" if not post.get("is_youtube") else f"📎 منبع: {label}"
    caption = f"{post['text']}\n\n{source_tag}" if post.get("text") else source_tag
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 4] + "..."

    # ۱. حالت ویدیوی یوتیوب
    if post.get("type") == "youtube_video":
        print(f"در حال دانلود ویدیوی یوتیوب: {post['url']}")
        temp_prefix = f"yt_{post['id']}"
        video_file = download_youtube_video(post["url"], temp_prefix)

        if video_file and video_file.exists():
            size_mb = video_file.stat().st_size / (1024 * 1024)
            print(f"ویدیو با حجم {size_mb:.1f} مگابایت دانلود شد. در حال ارسال به تلگرام و بله...")
            try:
                if size_mb <= MAX_FILE_SIZE_MB:
                    broadcast_video(video_file, caption)
                else:
                    print(f"حجم ویدیو ({size_mb:.1f}MB) بیش از حد مجاز است. ارسال به صورت پیام متنی و لینک...")
                    broadcast_message(caption)
            finally:
                video_file.unlink(missing_ok=True)
        else:
            print("دانلود ویدیو ناموفق بود، لینک متنی برای کانال ارسال می‌شود...")
            broadcast_message(caption)
        return True

    # ۲. حالت عکس تلگرام
    if post["type"] == "photo" and post["url"]:
        temp_img = Path(f"temp_{username}_{post['id']}.jpg")
        try:
            r = requests.get(post["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                temp_img.write_bytes(r.content)
                broadcast_photo(temp_img, caption)
        except Exception as e:
            print(f"خطا در ارسال عکس: {e}")
            broadcast_message(caption)
        finally:
            temp_img.unlink(missing_ok=True)
        return True

    # ۳. حالت ویدیوی تلگرام
    if post["type"] == "video" and post["url"]:
        temp_vid = Path(f"temp_{username}_{post['id']}.mp4")
        try:
            r = requests.get(post["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                temp_vid.write_bytes(r.content)
                broadcast_video(temp_vid, caption)
        except Exception as e:
            print(f"خطا در ارسال ویدیو تلگرام: {e}")
            broadcast_message(caption)
        finally:
            temp_vid.unlink(missing_ok=True)
        return True

    # ۴. حالت فایل/داکیومنت تلگرام (PDF, ZIP, ...)
    if post["type"] == "document" and post["url"]:
        fname = post.get("filename") or f"file_{post['id']}.bin"
        temp_doc = Path(f"temp_{username}_{fname}")
        try:
            r = requests.get(post["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                temp_doc.write_bytes(r.content)
                broadcast_document(temp_doc, caption)
            else:
                broadcast_message(caption)
        except Exception as e:
            print(f"خطا در ارسال فایل: {e}")
            broadcast_message(caption)
        finally:
            temp_doc.unlink(missing_ok=True)
        return True

    # ۵. پیام معمولی متنی
    full_text = f"{post['text']}\n\n{source_tag}" if post.get("text") else source_tag
    if len(full_text) > MAX_TEXT_LENGTH:
        full_text = full_text[:MAX_TEXT_LENGTH - 4] + "..."
    broadcast_message(full_text)
    return True


# ==========================================
# حلقه اصلی پردازش کانال‌ها
# ==========================================
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
    print(f"بررسی {'یوتیوب' if is_youtube else 'تلگرام'}: {label} (@{username}) | آخرین شناسه: {last_id}")

    posts = []
    try:
        if is_youtube:
            posts = fetch_youtube_updates(chan_info["url"], label, seen_ids)
            for p in posts:
                p["is_youtube"] = True
        else:
            messages = fetch_channel_messages(username)
            posts = parse_telegram_posts(messages, last_id, seen_ids)
    except Exception as e:
        print(f"خطا در دریافت اطلاعات {username}: {e}")
        return {"last_id": last_id, "seen_ids": seen_ids}

    if not posts:
        print("هیچ پست یا ویدیوی جدیدی وجود ندارد.")
        return {"last_id": last_id, "seen_ids": seen_ids}

    print(f"تعداد {len(posts)} مورد جدید تایید شده برای ارسال...")
    new_last_id = last_id
    new_seen = list(seen_ids)

    for post in posts:
        print(f"در حال پردازش و ارسال: {post['id']} ({post.get('type')})...")
        deliver_post(post, username, label)
        new_last_id = max(new_last_id, post["id"])
        if post["id"] not in new_seen:
            new_seen.append(post["id"])
        time.sleep(3)

    new_seen = new_seen[-150:]
    return {"last_id": new_last_id, "seen_ids": new_seen}


def main():
    channels_state = load_state()

    for chan in CHANNELS:
        res = process_channel(chan, channels_state)
        channels_state[chan["username"]] = res
        save_state(channels_state)

    print("\n✅ رصد تمامی کانال‌های تلگرام و یوتیوب با موفقیت پایان یافت.")


if __name__ == "__main__":
    main()
