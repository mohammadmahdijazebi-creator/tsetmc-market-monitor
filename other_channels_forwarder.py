import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


CHANNELS = {
    "rasadkhoneh": "رصدخونه",
    "MarketSummary": "خلاصه بازار",
}

STATE_FILE = Path("other_channels_state.json")
MAX_CAPTION_LENGTH = 1024
REQUEST_TIMEOUT = 45

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
        return {}

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(value, dict):
        return {}

    return {
        username: int(value.get(username, 0))
        for username in CHANNELS
        if str(value.get(username, "")).isdigit()
    }


def save_state(state):
    temporary_file = STATE_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary_file.replace(STATE_FILE)


def extract_image_url(photo_element):
    style = photo_element.get("style", "")
    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
    return match.group(1) if match else None


def get_caption(message):
    text_element = message.find("div", class_="tgme_widget_message_text")
    if not text_element:
        return ""

    return text_element.get_text("\n", strip=True)


def fetch_channel_messages(username):
    response = requests.get(
        f"https://t.me/s/{username}",
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find_all("div", class_=re.compile(r"\btgme_widget_message\b"))


def parse_image_posts(messages, last_id):
    posts = []

    for message in messages:
        data_post = message.get("data-post", "")
        if "/" not in data_post:
            continue

        try:
            message_id = int(data_post.rsplit("/", 1)[-1])
        except ValueError:
            continue

        if message_id <= last_id:
            continue

        photo_element = message.find(
            "a",
            class_=re.compile(r"\btgme_widget_message_photo_wrap\b"),
        )
        if not photo_element:
            continue

        image_url = extract_image_url(photo_element)
        if not image_url:
            continue

        posts.append(
            {
                "id": message_id,
                "image_url": image_url,
                "caption": get_caption(message),
            }
        )

    return sorted(posts, key=lambda post: post["id"])


def make_caption(username, channel_title, caption):
    source = f"📎 منبع: @{username} ({channel_title})"
    result = f"{caption}\n\n{source}" if caption else source

    if len(result) > MAX_CAPTION_LENGTH:
        result = result[: MAX_CAPTION_LENGTH - 3].rstrip() + "..."

    return result


def send_photo(endpoint, token, chat_id, image_path, caption, label):
    if not token or not chat_id:
        print(f"{label}: credentials are not configured; skipped.")
        return False

    try:
        with image_path.open("rb") as image_file:
            response = requests.post(
                f"{endpoint}{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": image_file},
                timeout=REQUEST_TIMEOUT,
            )
        response.raise_for_status()
        print(f"{label}: image sent successfully.")
        return True
    except requests.RequestException as error:
        print(f"{label}: send failed: {error}")
        return False


def send_to_destinations(image_path, caption):
    results = []

    results.append(
        send_photo(
            "https://api.telegram.org/bot",
            BOT_TOKEN,
            CHANNEL_ID,
            image_path,
            caption,
            "Telegram",
        )
    )
    results.append(
        send_photo(
            "https://tapi.bale.ai/bot",
            BALE_BOT_TOKEN,
            BALE_CHANNEL_ID,
            image_path,
            caption,
            "Bale",
        )
    )

    return any(results)


def process_channel(username, channel_title, state):
    last_id = state.get(username, 0)
    print(f"Checking @{username}; last processed image ID: {last_id}")

    try:
        messages = fetch_channel_messages(username)
        posts = parse_image_posts(messages, last_id)
    except requests.RequestException as error:
        print(f"@{username}: channel fetch failed: {error}")
        return

    # On the first run, avoid replaying the whole visible channel history.
    if last_id == 0 and len(posts) > 1:
        posts = posts[-1:]

    for post in posts:
        image_path = Path(f"other_{username}_{post['id']}.jpg")

        try:
            response = requests.get(
                post["image_url"],
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            image_path.write_bytes(response.content)

            caption = make_caption(
                username,
                channel_title,
                post["caption"],
            )

            delivered = send_to_destinations(image_path, caption)
            if not delivered:
                print(
                    f"@{username} post {post['id']}: "
                    "no destination accepted the image; state not advanced."
                )
                continue

            state[username] = max(state.get(username, 0), post["id"])
            print(f"@{username}: processed image post {post['id']}")
        except (OSError, requests.RequestException) as error:
            print(f"@{username} post {post['id']}: processing failed: {error}")
        finally:
            image_path.unlink(missing_ok=True)


def main():
    state = load_state()

    for username, channel_title in CHANNELS.items():
        process_channel(username, channel_title, state)

    save_state(state)
    print("Other-channel forwarder completed.")


if __name__ == "__main__":
    main()
