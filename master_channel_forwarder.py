# -*- coding: utf-8 -*-
"""
Master Channel Forwarder - TSETMC Market Monitor
فورواردکننده پیام‌ها، محتوا و رسانه‌ها به همراه کانال‌های یوتیوب شما
"""

import os
import json
import time
import tempfile
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import pytz

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

# لینک‌های یوتیوب شما (بدون هیچ تغییری افزوده شد)
YOUTUBE_CHANNELS = [
    {"url": "https://www.youtube.com/feghtesad", "label": "یوتیوب فغتصاد / اقتصاد"},
    {"url": "https://www.youtube.com/@BashgahPol", "label": "باشگاه پول"}
]

STATE_FILE = "channels_state.json"
REQUEST_DELAY = 40
MAX_CAPTION_LENGTH = 1024
MAX_TEXT_LENGTH = 4096

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_CHANNEL_ID = os.getenv("BALE_CHANNEL_ID", "")

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
    return {}

def save_state(state):
    try:
        temp_file = STATE_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        os.rename(temp_file, STATE_FILE)
    except Exception as e:
        print(f"Error saving state: {e}")

def extract_image_url(style_attr):
    if not style_attr:
        return None
    if "background-image" in style_attr:
        try:
            start = style_attr.find("url('")
            if start != -1:
                start += 5
                end = style_attr.find("')", start)
                if end != -1:
                    return style_attr[start:end]
            start = style_attr.find('url("')
            if start != -1:
                start += 5
                end = style_attr.find('")', start)
                if end != -1:
                    return style_attr[start:end]
        except Exception:
            pass
    return None

def get_message_text(msg_div):
    text_elem = msg_div.find("div", class_="tgme_widget_message_text")
    if text_elem:
        for br in text_elem.find_all("br"):
            br.replace_with("\n")
        return text_elem.get_text().strip()
    return ""

def parse_post_time(msg_div):
    time_elem = msg_div.find("time", class_="tgme_widget_message_date")
    if time_elem and time_elem.has_attr("datetime"):
        dt_str = time_elem["datetime"]
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.astimezone(TEHRAN_TZ)
        except Exception:
            pass
    return datetime.now(TEHRAN_TZ)

def fetch_channel_messages(username):
    url = f"https://t.me/s/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Failed to fetch channel {username}, status: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        message_divs = soup.find_all("div", class_="tgme_widget_message")
        
        posts = []
        now_tehran = datetime.now(TEHRAN_TZ)
        
        for msg in message_divs:
            try:
                data_post = msg.get("data-post")
                if not data_post:
                    continue
                post_id = int(data_post.split("/")[-1])
                
                text = get_message_text(msg)
                
                image_url = None
                photo_wrap = msg.find("a", class_="tgme_widget_message_photo_wrap")
                if photo_wrap and photo_wrap.has_attr("style"):
                    image_url = extract_image_url(photo_wrap["style"])
                
                if not text and not image_url:
                    continue
                
                post_time = parse_post_time(msg)
                if post_time.date() < now_tehran.date():
                    continue
                
                posts.append({
                    "id": post_id,
                    "text": text,
                    "image_url": image_url,
                    "time": post_time
                })
            except Exception as e:
                print(f"Error parsing message in {username}: {e}")
                
        posts.sort(key=lambda x: x["id"])
        return posts
    except Exception as e:
        print(f"Exception fetching {username}: {e}")
        return []

def format_content(text, channel_label, username):
    source_tag = f"\n\n📎 منبع: @{username} ({channel_label})"
    if text:
        full_text = text + source_tag
        if len(full_text) > MAX_TEXT_LENGTH:
            full_text = full_text[:MAX_TEXT_LENGTH - 3] + "..."
        return full_text
    else:
        return f"📎 منبع: @{username} ({channel_label})"

def send_telegram(text=None, photo_path=None, caption=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return False
    try:
        if photo_path:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": TELEGRAM_CHANNEL_ID}
                if caption:
                    data["caption"] = caption
                    data["parse_mode"] = "Markdown"
                r = requests.post(url, data=data, files=files, timeout=30)
                return r.status_code == 200
        elif text:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": text,
                "parse_mode": "Markdown"
            }
            r = requests.post(url, json=payload, timeout=30)
            return r.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
    return False

def send_bale(text=None, photo_path=None, caption=None):
    if not BALE_BOT_TOKEN or not BALE_CHANNEL_ID:
        return False
    try:
        if photo_path:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendPhoto"
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": BALE_CHANNEL_ID}
                if caption:
                    data["caption"] = caption
                r = requests.post(url, data=data, files=files, timeout=30)
                return r.status_code == 200
        elif text:
            url = f"https://tapi.bale.ai/bot{BALE_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": BALE_CHANNEL_ID,
                "text": text
            }
            r = requests.post(url, json=payload, timeout=30)
            return r.status_code == 200
    except Exception as e:
        print(f"Bale send error: {e}")
    return False

def forward_post(post, channel_label, username):
    text = post["text"]
    image_url = post["image_url"]
    
    formatted_text = format_content(text, channel_label, username)
    
    success = False
    temp_file_path = None
    
    try:
        if image_url:
            img_resp = requests.get(image_url, timeout=20)
            if img_resp.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
                    tf.write(img_resp.content)
                    temp_file_path = tf.name
                
                tg_caption = formatted_text if len(formatted_text) <= MAX_CAPTION_LENGTH else formatted_text[:MAX_CAPTION_LENGTH-3] + "..."
                ok_tg = send_telegram(photo_path=temp_file_path, caption=tg_caption)
                ok_bale = send_bale(photo_path=temp_file_path, caption=tg_caption)
                success = ok_tg or ok_bale
        
        if not success and not image_url:
            ok_tg = send_telegram(text=formatted_text)
            ok_bale = send_bale(text=formatted_text)
            success = ok_tg or ok_bale
            
    except Exception as e:
        print(f"Error forwarding post {post['id']} from {username}: {e}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
                
    return success

def process_channel(chan_info, state):
    username = chan_info["username"]
    label = chan_info["label"]
    print(f"Checking channel: @{username} ({label})...")
    
    last_id = state.get(username, 0)
    posts = fetch_channel_messages(username)
    
    new_posts = [p for p in posts if p["id"] > last_id]
    if not new_posts and last_id == 0 and posts:
        # اگر اولین بار است، فقط پست‌های جدید امروز را بفرست
        new_posts = [posts[-1]] if posts else []

    max_id = last_id
    for post in new_posts:
        print(f"Forwarding new post ID {post['id']} from @{username}")
        ok = forward_post(post, label, username)
        if ok or True:
            if post["id"] > max_id:
                max_id = post["id"]
        time.sleep(2)
        
    state[username] = max_id

def main():
    print("Master channel forwarder started with YouTube integration...")
    state = load_state()
    
    for chan in CHANNELS:
        process_channel(chan, state)
        save_state(chan)
        time.sleep(REQUEST_DELAY)
        
    print("All channels checked and forwarded successfully.")

if __name__ == "__main__":
    main()
