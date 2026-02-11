# NAHB Django Web (UI + Game Engine + Community)

This Django app:
- renders the UI for readers/authors/admins
- tracks gameplay (plays, autosave sessions, paths)
- stores community data (ratings/comments, reports)
- consumes the Flask REST API for story content

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

Open: http://localhost:8000

## Roles
- **Reader**: default after register (can play, rate, report, view own history)
- **Author**: put the user in the **Authors** group (via Django admin)
- **Admin**: `is_staff` (moderation + global stats)

## Notes
- Author tools are protected and enforce **ownership** (authors can edit only their own stories).
- Flask write endpoints can be protected via `FLASK_API_KEY` / `API_KEY` env vars.
- Graph pages use `vis-network` (CDN) for story tree + player path visualization.
