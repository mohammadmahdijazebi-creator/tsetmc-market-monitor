import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CHANNEL_USERNAME = "option_cofe"
CHANNEL_LABEL = "کافه آپشن"

STATE_FILE = Path("option_cofe_state.json")
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


def load_state():
    if not STATE_FILE.exists():
        return 0
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return int(data.get("last_id", 0))
    except Exception:
        return 0


def save_state(last_id):
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(
        json.dumps({"last_id": last_id}, ensure_ascii=False, indent=2),
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


def fetch_channel_messages():
    url = f"https://t.me/s/{CHANNEL_USERNAME}"
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


def parse_posts(messages, last_id):
    posts = []
    for msg in messages:
        data_post = msg.get("data-post", "")
        if "/" not in data_post:
            continue

        try:
            msg_id = int(data_post.rsplit("/", 1)[-1])
        except ValueError:
            continue

        if msg_id <= last_id:
            continue

        photo_el = msg.find("a", class_=re.compile(r"\btgme_widget_message_photo_wrap\b"))
        image_url = extract_image_url(photo_el)
        text = get_message_text(msg)

        # اگر پست نه عکس داشت و نه متن (مثلاً پیام سرویسی یا خالی)، رد شود
        if not image_url and not text:
            continue

        posts.append({
            "id": msg_id,
            "image_url": image_url,
            "text": text,
        })

    return sorted(posts, key=lambda x: x["id"])


def format_content(text, is_photo=False):
    source_tag = f"📎 منبع: @{CHANNEL_USERNAME} ({CHANNEL_LABEL})"
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
        print(f"[{name}] عکس پست با موفقیت ارسال شد.")
        return True
    except Exception as e:
        print(f"[{name}] خطا در ارسال عکس: {e}")
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
        print(f"[{name}] متن پست با موفقیت ارسال شد.")
        return True
    except Exception as e:
        print(f"[{name}] خطا در ارسال متن: {e}")
        return False


def deliver_post(post):
    is_photo = bool(post["image_url"])
    caption_or_text = format_content(post["text"], is_photo=is_photo)
    results = []

    if is_photo:
        temp_img = Path(f"cofe_{post['id']}.jpg")
        try:
            r = requests.get(post["image_url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            temp_img.write_bytes(r.content)

            # ارسال عکس به تلگرام و بله
            r1 = send_photo_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, temp_img, caption_or_text, "Telegram")
            r2 = send_photo_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, temp_img, caption_or_text, "Bale")
            results.extend([r1, r2])
        except Exception as e:
            print(f"خطا در دانلود عکس پست {post['id']}: {e}")
            return False
        finally:
            temp_img.unlink(missing_ok=True)
    else:
        # ارسال پیام متنی به تلگرام و بله
        r1 = send_message_dest("https://api.telegram.org/bot", BOT_TOKEN, CHANNEL_ID, caption_or_text, "Telegram")
        r2 = send_message_dest("https://tapi.bale.ai/bot", BALE_BOT_TOKEN, BALE_CHANNEL_ID, caption_or_text, "Bale")
        results.extend([r1, r2])

    return any(results)


def main():
    last_id = load_state()
    print(f"بررسی کانال @{CHANNEL_USERNAME} | آخرین پست ثبت‌شده: {last_id}")

    try:
        messages = fetch_channel_messages()
        posts = parse_posts(messages, last_id)
    except Exception as e:
        print(f"خطا در دریافت صفحه کانال: {e}")
        return

    # در اولین اجرا برای جلوگیری از ارسال کل آرشیو گذشته کانال
    if last_id == 0:
        if posts:
            new_id = posts[-1]["id"]
            save_state(new_id)
            print(f"اجرای اول: آخرین شناسه ({new_id}) ذخیره شد. ارسال از پست‌های بعدی آغاز می‌شود.")
        return

    new_last_id = last_id
    for post in posts:
        print(f"در حال پردازش پست شماره {post['id']}...")
        ok = deliver_post(post)
        if ok:
            new_last_id = max(new_last_id, post["id"])
            save_state(new_last_id)
        else:
            print(f"پست {post['id']} ارسال نشد؛ شناسه ذخیره نمی‌شود.")

    print("پایان پردازش کافه آپشن.")


if __name__ == "__main__":
    main()
