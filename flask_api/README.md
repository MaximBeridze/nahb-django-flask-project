# NAHB Flask API (Story Content)

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

API base: `http://localhost:5001`

## Notes
- Story content is stored **only** here.
- If `API_KEY` is set in `.env`, write endpoints require header: `X-API-KEY: <secret>`.
- A demo story is auto-seeded on first run (based on your storyboard).
