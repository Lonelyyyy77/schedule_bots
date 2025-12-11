import json
import os

URLS_FILE = "C:\\Users\\G5\\VSCode_projects\\schedule_bots\\src\\core\\data\\user_urls.json"


def load_urls() -> dict:
    if not os.path.exists(URLS_FILE):
        return {}
    try:
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_urls(urls: dict):
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=4, ensure_ascii=False)


def get_user_url(user_id: int) -> str | None:
    urls = load_urls()
    return urls.get(str(user_id))


def set_user_url(user_id: int, url: str):
    urls = load_urls()
    urls[str(user_id)] = url
    save_urls(urls)
