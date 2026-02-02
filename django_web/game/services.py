from __future__ import annotations
import requests
from django.conf import settings

def api_url(path: str) -> str:
    base = settings.FLASK_API_BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path

def get_published_stories() -> list[dict]:
    r = requests.get(api_url("/stories"), params={"status": "published"}, timeout=5)
    r.raise_for_status()
    return r.json()

def get_story(story_id: int) -> dict:
    r = requests.get(api_url(f"/stories/{story_id}"), timeout=5)
    r.raise_for_status()
    return r.json()

def get_start(story_id: int) -> dict:
    r = requests.get(api_url(f"/stories/{story_id}/start"), timeout=5)
    r.raise_for_status()
    return r.json()

def get_page(page_id: int) -> dict:
    r = requests.get(api_url(f"/pages/{page_id}"), timeout=5)
    r.raise_for_status()
    return r.json()
