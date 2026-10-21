import os
import json
import time
import requests
import subprocess
from bs4 import BeautifulSoup

STATE_FILE = "channels_state.json"

# تنظیمات بات‌ها از Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("CHANNEL_ID")

BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID")

# ۲۴ کانال تلگرام شما
TELEGRAM_CHANNELS = [
    {"username": "MetaWave", "label": "متاسپات"},
    {"username": "crypto_signals", "label": "سیگنال کریپتو"},
    # ... (سایر کانال‌های تلگرامی شما)
]

# ۳ کانال یوتیوب شما (آدرس‌های فید یا صفحه کانال)
YOUTUBE_CHANNELS = [
    {"url": "https://www.youtube.com/@feghtesad", "label": "اقتصاد"},
    {"url": "https://www.youtube.com/@BashgahPol", "label": "باشگاه پول"},
    {"url": "https://www.youtube.com/@aliichii-tube", "label": "علیچی"}
]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    temp_file = STATE_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, STATE_FILE)


def send_telegram_video(video_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption[:1024], "parse_mode": "HTML"}
            res = requests.post(url, data=data, files=files, timeout=120)
            return res.json().get("ok", False)
    except Exception as e:
        print(f"Telegram video send error: {e}")
        return False


def send_bale_video(video_path, caption):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return False
    url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": BALE_CHANNEL_ID, "caption": caption[:1024]}
            res = requests.post(url, data=data, files=files, timeout=120)
            return res.json().get("ok", False)
    except Exception as e:
        print(f"Bale video send error: {e}")
        return False


def process_youtube_channels(state):
    for yt in YOUTUBE_CHANNELS:
        url = yt["url"]
        label = yt["label"]
        print(f"Checking YouTube channel: {label} ({url})")

        # استفاده از yt-dlp برای استخراج آخرین ویدیو بدون دانلود کامل ابتدا
        try:
            cmd = ["yt-dlp", "--print", "%(id)s||%(title)s||%(webpage_url)s", "--playlist-end", "1", url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0 or not result.stdout.strip():
                print(f"Could not fetch info for {label}")
                continue

            parts = result.stdout.strip().split("||")
            if len(parts) < 3:
                continue
            video_id, title, video_url = parts[0], parts[1], parts[2]

            # بررسی وضعیت برای جلوگیری از ارسال تکراری
            last_sent_id = state.get(f"yt_{url}", "")
            if last_sent_id == video_id:
                print(f"No new video for {label}. Latest is already sent.")
                continue

            print(f"New video found for {label}: {title} ({video_id})")

            # دانلود ویدیو با فرمت زیر ۴۸ مگابایت و کیفیت مناسب
            output_template = "downloads/downloaded_video.mp4"
            os.makedirs("downloads", exist_ok=True)
            
            download_cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
                "--max-filesize", "48m",
                "-o", output_template,
                video_url
            ]
            dl_res = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
            
            if dl_res.returncode == 0 and os.path.exists(output_template):
                caption = f"🎥 {label}: {title}\n🔗 {video_url}"
                
                # ارسال به تلگرام و بله
                send_telegram_video(output_template, caption)
                send_bale_video(output_template, caption)

                # آپدیت وضعیت به عنوان ارسال شده
                state[f"yt_{url}"] = video_id
                save_state(state)
                
                # پاک کردن فایل موقت
                try:
                    os.remove(output_template)
                except:
                    pass
            else:
                print(f"Failed to download video for {label} or file too large.")

        except Exception as e:
            print(f"Error processing YouTube channel {label}: {e}")


def main():
    state = load_state()
    print("Starting master channel forwarder (Telegram + YouTube)...")
    
    # پردازش کانال‌های یوتیوب و ارسال آخرین ویدیوی جدید (غیرتکراری)
    process_youtube_channels(state)
    
    # بخش کانال‌های تلگرامی شما به قوت خود باقیست...
    print("Finished checking channels run.")


if __name__ == "__main__":
    main()
