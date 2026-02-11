import re
import requests
from django.conf import settings

SCORE_RE = re.compile(r"\((?P<sign>[+-])(?P<num>\d+)\)")

def api_headers():
    h = {"Accept": "application/json"}
    if settings.FLASK_API_KEY:
        h["X-API-KEY"] = settings.FLASK_API_KEY
    return h

def api_get(path: str, params=None):
    url = f"{settings.FLASK_API_BASE}{path}"
    r = requests.get(url, params=params, headers=api_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def api_post(path: str, payload: dict):
    url = f"{settings.FLASK_API_BASE}{path}"
    r = requests.post(url, json=payload, headers=api_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def api_put(path: str, payload: dict):
    url = f"{settings.FLASK_API_BASE}{path}"
    r = requests.put(url, json=payload, headers=api_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def api_delete(path: str):
    url = f"{settings.FLASK_API_BASE}{path}"
    r = requests.delete(url, headers=api_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def parse_score_delta(choice_text: str) -> int:
    m = SCORE_RE.search(choice_text or "")
    if not m:
        return 0
    sign = 1 if m.group("sign") == "+" else -1
    return sign * int(m.group("num"))
