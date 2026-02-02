# NAHB Demo (Bare Minimum) — Flask API + Django Web

This is a **tiny, runnable demo** of the NAHB architecture:

- **Flask**: REST API storing story content (SQLite)
- **Django**: Web UI + gameplay tracking (SQLite) that **consumes the Flask API**

It implements enough to **create/play** a small story and see **basic stats**.

---

## 0) Prerequisites

- Python 3.10+ recommended
- Two terminals

---

## 1) Run Flask API

### Install
```bash
cd flask_api
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

### Start
```bash
python app.py
```

Flask starts on: `http://127.0.0.1:5001`

On first launch, it creates `flask_api.sqlite` and **seeds** a demo story.

---

## 2) Run Django Web

### Install
```bash
cd django_web
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

### Configure API URL (optional)
By default it uses:
- `FLASK_API_BASE_URL=http://127.0.0.1:5001`

You can override with an env var:
```bash
export FLASK_API_BASE_URL="http://127.0.0.1:5001"
```

### Migrate & start
```bash
python manage.py migrate
python manage.py runserver
```

Open: `http://127.0.0.1:8000`

---

## 3) What to click

- **Stories**: `/` — list published stories (from Flask)
- **Play**: click a story then "Play"
- **Stats**: `/stats/` — shows plays per story + endings reached (from Django DB)

---

## 4) Minimal API Contract Implemented

### Read
- `GET /stories?status=published`
- `GET /stories/<id>`
- `GET /stories/<id>/start`
- `GET /pages/<id>`

### Write (Level 10: open)
- `POST /stories`
- `PUT /stories/<id>`
- `DELETE /stories/<id>`
- `POST /stories/<id>/pages`
- `POST /pages/<id>/choices`

---

## 5) Notes

- This is **not** production-ready; it’s only meant to show the expected **look/feel** and architecture.
- Level 16 security (API key + auth) is intentionally not included.
