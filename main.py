import os
import time
import random
import requests
import difflib
from datetime import datetime
from bs4 import BeautifulSoup
import telegrame
from commands import JsonList, Json, Threading, newline
from secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

try:
    import telebot
except ImportError:
    print("Install dependency via 'pip install pytelegrambotapi'")
    import telebot

__version__ = "0.1.1"

# Configuration
CHECK_INTERVAL = 3600  # Check every hour

# Directory to store previous content
CONTENT_DIR = 'url_contents'
os.makedirs(CONTENT_DIR, exist_ok=True)


def fetch_url_content(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def read_previous_content(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    return ""


def save_content(filename, content):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)


def format_html(html):
    """Formats HTML string using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.prettify()


def generate_diff(a, b):
    """Generates a diff between two HTML strings, showing only the differences."""
    formatted_a = format_html(a)
    formatted_b = format_html(b)

    diff = difflib.unified_diff(
        formatted_a.splitlines(keepends=True),
        formatted_b.splitlines(keepends=True),
        fromfile='a.html',
        tofile='b.html',
        lineterm='',
        n=0  # This reduces the context lines to zero, showing only the differences.
    )

    # Filter the diff to include only the changes
    filtered_diff = []
    for line in diff:
        if line.startswith('@@') or line.startswith('+') or line.startswith('-'):
            filtered_diff.append(line)

    return ''.join(filtered_diff)


def send_to_telegram(telegram_api, message):
    telegrame.send_message(telegram_api, TELEGRAM_CHAT_ID, message)


def get_urls():
    jsonlist = JsonList("urls.json")
    jsonlist.load()
    return jsonlist.string


def set_urls(urls):
    jsonlist = JsonList("urls.json")
    jsonlist.string = urls
    jsonlist.save()


def set_offset(offset):
    jsonlist = Json("offset.json")
    jsonlist.string = offset
    jsonlist.save()


def get_offset():
    jsonlist = Json("offset.json")
    jsonlist.load()
    return jsonlist.string


def get_messages(offset=None):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates'
    payload = {
        'offset': offset
    }
    response = requests.get(url, json=payload)
    if response.status_code == 200:
        if response.json()['ok']:
            return response.json()['result']


def url_checker(once=False):
    telegram_api = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

    while True:
        for url in get_urls():
            try:
                content = fetch_url_content(url)
                filename = os.path.join(CONTENT_DIR, f"{url.replace('https://', '').replace('/', '_')}.txt")

                previous_content = read_previous_content(filename)
                if previous_content != content:
                    diff = generate_diff(previous_content, content)
                    if len(diff) > 3500:
                        diff = diff[:3500] + "\n\n... (diff too long, truncated)"
                    if diff:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        message = f"Change detected in {url} at {timestamp}:\n{diff}"
                        send_to_telegram(telegram_api, message)
                        save_content(filename, content)
            except Exception as e:
                send_to_telegram(telegram_api, f"Error processing {url}: {e}")

        if once:
            break

        # Sleep for a random time around the CHECK_INTERVAL to avoid pattern detection
        sleep_time = CHECK_INTERVAL + random.uniform(-CHECK_INTERVAL / 2, CHECK_INTERVAL / 2)
        time.sleep(sleep_time)


def message_receiver():
    offset = get_offset()
    telegram_api = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

    while True:

        messages = get_messages(offset=offset)

        if not messages:
            time.sleep(1)
            continue

        for message in messages:

            offset = message['update_id'] + 1
            set_offset(offset)

            if not message['message']['chat']['id'] == TELEGRAM_CHAT_ID:
                continue
            if message['message']['text'] == '/start':
                send_to_telegram(telegram_api, "Hello! I am a bot to check the changes in the website.")
            elif message['message']['text'].lower().startswith('add '):
                url = message['message']['text'][4:]
                urls = get_urls()
                urls.append(url)
                set_urls(urls)
                send_to_telegram(telegram_api, f"URL {url} added successfully.")
            elif message['message']['text'].lower().startswith('remove '):
                url = message['message']['text'][7:]
                urls = get_urls()
                for url in get_urls():
                    if url == url:
                        urls.pop(urls.index(url))
                        send_to_telegram(telegram_api, f"URL {url} removed successfully.")
                        break
                send_to_telegram(telegram_api, f"URL {url} not found.")
            elif message['message']['text'].lower().startswith('print'):
                urls = get_urls()
                send_to_telegram(telegram_api, f"URLs: {newline.join(urls)}")
            elif message['message']['text'].lower().startswith('check'):
                send_to_telegram(telegram_api, "Checking...")
                url_checker(once=True)
                send_to_telegram(telegram_api, "Done.")
            else:
                send_to_telegram(telegram_api,
                                 "Invalid command. "
                                 "Please use /start, add <url>, remove <url>, print or check.")


def main():

    threads = Threading()

    # threads.add(telegrame.very_safe_start_bot, args=(message_receiver,), name="Receiver")
    # threads.add(telegrame.very_safe_start_bot, args=(url_checker,), name="Sender")
    message_receiver()

    threads.start()


if __name__ == "__main__":
    main()
