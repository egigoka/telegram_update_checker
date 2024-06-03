import os
import time
import random
import requests
import difflib
from datetime import datetime
from commands import JsonList
from secrets import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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

def generate_diff(old_content, new_content):
    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile='old_content',
        tofile='new_content',
        lineterm=''
    )
    return '\n'.join(diff)

def send_to_telegram(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()

def main():
    while True:
        for url in URLS:
            try:
                content = fetch_url_content(url)
                filename = os.path.join(CONTENT_DIR, f"{url.replace('https://', '').replace('/', '_')}.txt")
                
                previous_content = read_previous_content(filename)
                if previous_content != content:
                    diff = generate_diff(previous_content, content)
                    if diff:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        message = f"*Changes detected at {timestamp} for {url}*\n\n```\n{diff}\n```"
                        send_to_telegram(message)
                        save_content(filename, content)
            except Exception as e:
                print(f"Error processing {url}: {e}")

        # Sleep for a random time around the CHECK_INTERVAL to avoid pattern detection
        sleep_time = CHECK_INTERVAL + random.uniform(-CHECK_INTERVAL / 2, CHECK_INTERVAL / 2)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
