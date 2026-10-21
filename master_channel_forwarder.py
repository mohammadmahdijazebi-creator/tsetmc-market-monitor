# -*- coding: utf-8 -*-
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# =========================
# کانال‌ها + یوتیوب‌ها
# =========================
CHANNELS = [
    # تلگرام
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

    # یوتیوب (سه لینک)
    {"username": "feghtesad_yt", "label": "یوتیوب فردای اقتصاد", "is_youtube": True, "url": "https://www.youtube.com/feghtesad"},
    {"username": "BashgahPol", "label": "باشگاه پول", "is_youtube": True, "url": "https://www.youtube.com/@BashgahPol"},
    {"username": "aliichii_tube", "label": "Aliichii Tube", "is_youtube": True, "url": "https://www.youtube.com/@aliichii-tube"},
]

STATE_FILE = Path("channels_state.json")
REQUEST_TIMEOUT = 45
MAX_CAPTION_LENGTH = 1024
MAX_TEXT_LENGTH = 4096
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

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

TG_BOT_API = "https://api.telegram.org/bot"
BALE_BOT_API = "https://tapi.bale.ai/bot"


# =========================
# مدل داده
# =========================
@dataclass
class Post:
    key: str                 # یکتا برای جلوگیری از تکرار
    text: str
    media_url: Optional[str] = None   # لینک مستقیم فایل/عکس/ویدیو اگر از t.me قابل استخراج باشد
    media_type: str = "text"          # text | photo | video | document
    filename: Optional[str] = None


# =========================
# State
# =========================
def load_state() -> Dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"خطا در خواندن فایل وضعیت: {e}")
        return {}


def save_state(state: Dict):
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def get_seen_set(state: Dict, source_key: str) -> List[str]:
    obj = state.get(source_key, {})
    if isinstance(obj, dict):
        return obj.get("seen_keys", [])
    # سازگاری با نسخه قدیمی
    return []


def set_seen_set(state: Dict, source_key: str, seen_keys: List[str]):
    state[source_key] = {"seen_keys": seen_keys[-300:]}  # نگهداری ۳۰۰ مورد آخر


# =========================
# ابزارهای استخراج تلگرام web preview
# =========================
def fetch_channel_messages(username: str):
    url = f"https://t.me/s/{username}"
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


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


def get_message_text(message_el) -> str:
    text_el = message_el.find("div", class_="tgme_widget_message_text")
    if not text_el:
        return ""
    return text_el.get_text("\n", strip=True)


def extract_background_image_url(style: str) -> Optional[str]:
    if not style:
        return None
    m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
    return m.group(1) if m else None


def extract_photo_url(message_el) -> Optional[str]:
    # عکس‌ها معمولاً در tgme_widget_message_photo_wrap با background-image می‌آیند
    a = message_el.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
    if not a:
        return None
    return extract_background_image_url(a.get("style", ""))


def extract_document_url(message_el) -> Tuple[Optional[str], Optional[str]]:
    """
    تلاش برای استخراج لینک دانلود فایل (pdf/zip/...) از preview.
    در بعضی کانال‌ها مستقیم لینک CDN می‌دهد، در بعضی موارد نمی‌دهد.
    """
    doc = message_el.find("a", class_=re.compile(r"\btgme_widget_message_document_wrap\b"))
    if not doc:
        return None, None

    href = doc.get("href")
    # بعضی وقت‌ها href لینک کانال/پست است نه CDN؛ باز هم می‌فرستیم به صورت لینک
    filename = None

    name_el = message_el.find("div", class_=re.compile(r"\btgme_widget_message_document_title\b"))
    if name_el:
        filename = name_el.get_text(strip=True)

    return href, filename


def extract_video_url(message_el) -> Optional[str]:
    """
    ویدیوها در preview معمولاً <video> دارند با src یا <a class=...video_wrap>
    اگر src نبود، حداقل لینک پست را می‌فرستیم.
    """
    v = message_el.find("video")
    if v and v.get("src"):
        return v.get("src")

    a = message_el.find("a", class_=re.compile(r"\btgme_widget_message_video_wrap\b"))
    if a and a.get("style"):
        # گاهی thumbnail در style است؛ ولی خود ویدیو لینک جداست و اینجا در نمی‌آید
        # پس اگر src نداریم، None می‌دهیم تا fallback به متن/لینک باشد
        return None

    return None


def parse_telegram_posts(username: str, label: str, messages, seen_keys: List[str]) -> List[Post]:
    posts: List[Post] = []
    now_tehran = datetime.now(TEHRAN_TZ)
    today_start = now_tehran.replace(hour=0, minute=0, second=0, microsecond=0)

    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue
        post_id = data_post.rsplit("/", 1)[-1].strip()
        if not post_id.isdigit():
            continue

        post_time = parse_post_time(msg)

        # اولین اجرا: فقط پست‌های امروز را بگیر که یکهو اسپم نشود
        if not seen_keys:
            if not post_time or post_time < today_start:
                continue

        base_key = f"tg:{username}:{post_id}"
        if base_key in seen_keys:
            continue

        text = get_message_text(msg).strip()
        # fallback لینک پست (اگر فایل مستقیم درنیامد)
        post_link = f"https://t.me/{username}/{post_id}"

        # تشخیص نوع محتوا
        photo_url = extract_photo_url(msg)
        doc_url, doc_name = extract_document_url(msg)
        video_url = extract_video_url(msg)

        if photo_url:
            posts.append(Post(
                key=base_key,
                text=(text if text else post_link),
                media_url=photo_url,
                media_type="photo",
                filename=None
            ))
            continue

        if video_url:
            posts.append(Post(
                key=base_key,
                text=(text if text else post_link),
                media_url=video_url,
                media_type="video",
                filename=None
            ))
            continue

        if doc_url:
            posts.append(Post(
                key=base_key,
                text=(text if text else post_link),
                media_url=doc_url,
                media_type="document",
                filename=doc_name
            ))
            continue

        # فقط متن/لینک
        if text:
            posts.append(Post(key=base_key, text=text, media_url=None, media_type="text"))
        else:
            posts.append(Post(key=base_key, text=post_link, media_url=None, media_type="text"))

    # مرتب‌سازی بر اساس شناسه عددی برای حفظ ترتیب
    def _id_num(k: str) -> int:
        try:
            return int(k.split(":")[-1])
        except Exception:
            return 0

    return sorted(posts, key=lambda p: _id_num(p.key))


# =========================
# یوتیوب RSS (پایدار)
# =========================
def resolve_youtube_channel_id(youtube_url: str) -> Optional[str]:
    """
    از URL کانال/هندل، channel_id را استخراج می‌کند.
    - اگر URL شامل /channel/UC... باشد => مستقیم
    - در غیر این صورت HTML را می‌خوانیم و UC... را پیدا می‌کنیم
    """
    m = re.search(r"/channel/(UC[\w-]+)", youtube_url)
    if m:
        return m.group(1)

    try:
        r = requests.get(youtube_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        html = r.text

        # meta property="og:url" content="https://www.youtube.com/channel/UC...."
        m2 = re.search(r'property="og:url"\s+content="https://www\.youtube\.com/channel/(UC[\w-]+)"', html)
        if m2:
            return m2.group(1)

        # fallback: هرجا UC... دیدیم
        m3 = re.search(r"(UC[\w-]{20,})", html)
        if m3:
            return m3.group(1)

    except Exception as e:
        print(f"خطا در resolve channel_id از {youtube_url}: {e}")

    return None


def fetch_youtube_rss_posts(youtube_url: str, source_key: str, label: str, seen_keys: List[str]) -> List[Post]:
    """
    با RSS آخرین ویدیوها را می‌گیرد (بدون API Key).
    خروجی: Postهای متنی (لینک ویدیو)
    """
    cid = resolve_youtube_channel_id(youtube_url)
    if not cid:
        print(f"⚠️ نتوانستم channel_id یوتیوب را برای {youtube_url} پیدا کنم.")
        return []

    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    try:
        r = requests.get(rss_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            print(f"⚠️ RSS یوتیوب خطا داد: {r.status_code}")
            return []

        soup = BeautifulSoup(r.text, "xml")
        entries = soup.find_all("entry")
        posts: List[Post] = []

        for ent in entries[:10]:
            vid = ent.find("yt:videoId")
            title = ent.find("title")
            link = ent.find("link")
            published = ent.find("published")

            if not vid or not title:
                continue

            video_id = vid.get_text(strip=True)
            key = f"yt:{source_key}:{video_id}"
            if key in seen_keys:
                continue

            video_link = f"https://www.youtube.com/watch?v={video_id}"
            t = title.get_text(strip=True)

            pub_str = published.get_text(strip=True) if published else ""
            text = (
                f"📺 ویدیوی جدید از {label}\n"
                f"• عنوان: {t}\n"
                f"• زمان: {pub_str}\n\n"
                f"🔗 لینک:\n{video_link}"
            )

            posts.append(Post(key=key, text=text, media_url=None, media_type="text"))

        return posts

    except Exception as e:
        print(f"خطا در خواندن RSS یوتیوب: {e}")
        return []


# =========================
# ارسال به تلگرام/بله
# =========================
def format_content(text: str, source_tag: str, is_caption: bool) -> str:
    full = f"{text}\n\n{source_tag}".strip() if text else source_tag
    max_len = MAX_CAPTION_LENGTH if is_caption else MAX_TEXT_LENGTH
    if len(full) > max_len:
        full = full[: max_len - 3].rstrip() + "..."
    return full


def download_to_temp(url: str, suffix: str = "") -> Optional[Path]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        temp = Path(f"temp_{abs(hash(url)) % (10**12)}{suffix}")
        temp.write_bytes(r.content)
        return temp
    except Exception as e:
        print(f"خطا در دانلود فایل: {url} | {e}")
        return None


def send_photo_dest(endpoint, token, chat_id, image_path: Path, caption: str, name: str) -> bool:
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
        ok = (res.status_code == 200)
        if not ok:
            print(f"[{name}] خطا در sendPhoto: {res.status_code} - {res.text}")
        return ok
    except Exception as e:
        print(f"[{name}] استثنا در ارسال تصویر: {e}")
        return False


def send_document_dest(endpoint, token, chat_id, file_path: Path, caption: str, name: str) -> bool:
    if not token or not chat_id:
        return False
    try:
        with file_path.open("rb") as f:
            res = requests.post(
                f"{endpoint}{token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": f},
                timeout=REQUEST_TIMEOUT,
            )
        ok = (res.status_code == 200)
        if not ok:
            print(f"[{name}] خطا در sendDocument: {res.status_code} - {res.text}")
        return ok
    except Exception as e:
        print(f"[{name}] استثنا در ارسال فایل: {e}")
        return False


def send_video_dest(endpoint, token, chat_id, file_path: Path, caption: str, name: str) -> bool:
    if not token or not chat_id:
        return False
    try:
        with file_path.open("rb") as f:
            res = requests.post(
                f"{endpoint}{token}/sendVideo",
                data={"chat_id": chat_id, "caption": caption},
                files={"video": f},
                timeout=REQUEST_TIMEOUT,
            )
        ok = (res.status_code == 200)
        if not ok:
            print(f"[{name}] خطا در sendVideo: {res.status_code} - {res.text}")
        return ok
    except Exception as e:
        print(f"[{name}] استثنا در ارسال ویدیو: {e}")
        return False


def send_message_dest(endpoint, token, chat_id, text: str, name: str) -> bool:
    if not token or not chat_id:
        return False
    try:
        res = requests.post(
            f"{endpoint}{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=REQUEST_TIMEOUT,
        )
        ok = (res.status_code == 200)
        if not ok:
            print(f"[{name}] خطا در sendMessage: {res.status_code} - {res.text}")
        return ok
    except Exception as e:
        print(f"[{name}] استثنا در ارسال متن: {e}")
        return False


def deliver_post(post: Post, source_tag: str) -> bool:
    """
    نکته: از preview تلگرام همیشه لینک مستقیم فایل/ویدیو در نمی‌آید.
    اگر media_url نتواند دانلود شود، fallback به ارسال متن/لینک انجام می‌شود.
    """
    results = []

    if post.media_type == "photo" and post.media_url:
        caption = format_content(post.text, source_tag, is_caption=True)
        tmp = download_to_temp(post.media_url, suffix=".jpg")
        if tmp:
            try:
                r1 = send_photo_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, tmp, caption, "Telegram")
                r2 = send_photo_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, tmp, caption, "Bale")
                results.extend([r1, r2])
            finally:
                tmp.unlink(missing_ok=True)
        else:
            # fallback
            txt = format_content(post.text, source_tag, is_caption=False)
            r1 = send_message_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, txt, "Telegram")
            r2 = send_message_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, txt, "Bale")
            results.extend([r1, r2])

    elif post.media_type in ("document", "video") and post.media_url:
        caption = format_content(post.text, source_tag, is_caption=True)

        # اگر لینک فایل مستقیم نبود یا دانلود شکست خورد، فقط لینک را می‌فرستیم
        tmp = download_to_temp(post.media_url, suffix="")
        if tmp:
            try:
                if post.media_type == "video":
                    r1 = send_video_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, tmp, caption, "Telegram")
                    r2 = send_video_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, tmp, caption, "Bale")
                else:
                    r1 = send_document_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, tmp, caption, "Telegram")
                    r2 = send_document_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, tmp, caption, "Bale")
                results.extend([r1, r2])
            finally:
                tmp.unlink(missing_ok=True)
        else:
            txt = format_content(post.text, source_tag, is_caption=False)
            r1 = send_message_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, txt, "Telegram")
            r2 = send_message_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, txt, "Bale")
            results.extend([r1, r2])

    else:
        txt = format_content(post.text, source_tag, is_caption=False)
        r1 = send_message_dest(TG_BOT_API, BOT_TOKEN, CHANNEL_ID, txt, "Telegram")
        r2 = send_message_dest(BALE_BOT_API, BALE_BOT_TOKEN, BALE_CHANNEL_ID, txt, "Bale")
        results.extend([r1, r2])

    time.sleep(1.5)
    return any(results)


# =========================
# پردازش منابع
# =========================
def process_source(src: Dict, state: Dict) -> Dict:
    username = src["username"]
    label = src["label"]
    is_youtube = src.get("is_youtube", False)

    source_key = username
    seen_keys = get_seen_set(state, source_key)

    print("\n==========================================")
    print(f"بررسی {('YouTube' if is_youtube else 'Telegram')} | {label} | key={source_key} | seen={len(seen_keys)}")

    posts: List[Post] = []
    try:
        if is_youtube:
            posts = fetch_youtube_rss_posts(src["url"], source_key, label, seen_keys)
        else:
            messages = fetch_channel_messages(username)
            posts = parse_telegram_posts(username, label, messages, seen_keys)
    except Exception as e:
        print(f"خطا در دریافت منبع {source_key}: {e}")
        return state

    if not posts:
        print("هیچ مورد جدیدی نبود.")
        return state

    print(f"تعداد {len(posts)} مورد جدید برای ارسال...")
    source_tag = f"📎 منبع: {label} ({'YouTube' if is_youtube else '@'+username})"

    for p in posts:
        print(f"ارسال: {p.key} | type={p.media_type}")
        ok = deliver_post(p, source_tag)
        # حتی اگر ارسال به یکی از مقصدها fail شد، باز هم به عنوان دیده‌شده ثبت می‌کنیم
        # تا روی یک مورد گیر نکنیم و اسپم هم نشود
        seen_keys.append(p.key)

    set_seen_set(state, source_key, seen_keys)
    save_state(state)
    return state


def main():
    state = load_state()
    if not isinstance(state, dict):
        state = {}

    for src in CHANNELS:
        state = process_source(src, state)

    print("\nتمام کانال‌ها و منابع یوتیوب بررسی شدند. وضعیت نهایی ذخیره شد.")


if __name__ == "__main__":
    main()
