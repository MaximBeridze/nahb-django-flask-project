from __future__ import annotations

from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("FLASK_DB_URI", "sqlite:///flask_api.sqlite")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Story(db.Model):
    __tablename__ = "stories"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft/published/suspended
    start_page_id = db.Column(db.Integer, nullable=True)


class Page(db.Model):
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    is_ending = db.Column(db.Boolean, nullable=False, default=False)
    ending_label = db.Column(db.String(120), nullable=True)  # level 13+ optional


class Choice(db.Model):
    __tablename__ = "choices"
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, nullable=False, index=True)
    text = db.Column(db.String(200), nullable=False)
    next_page_id = db.Column(db.Integer, nullable=False)


def story_to_dict(s: Story) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "description": s.description,
        "status": s.status,
        "start_page_id": s.start_page_id,
    }


def page_to_dict(p: Page) -> dict:
    return {
        "id": p.id,
        "story_id": p.story_id,
        "text": p.text,
        "is_ending": bool(p.is_ending),
        "ending_label": p.ending_label,
    }


def choice_to_dict(c: Choice) -> dict:
    return {
        "id": c.id,
        "page_id": c.page_id,
        "text": c.text,
        "next_page_id": c.next_page_id,
    }


@app.get("/health")
def health():
    return {"ok": True}


# ---------------------------
# Reading endpoints
# ---------------------------

@app.get("/stories")
def list_stories():
    status = request.args.get("status")
    q = Story.query
    if status:
        q = q.filter_by(status=status)
    stories = q.order_by(Story.id.asc()).all()
    return jsonify([story_to_dict(s) for s in stories])


@app.get("/stories/<int:story_id>")
def get_story(story_id: int):
    s = Story.query.get_or_404(story_id)
    return jsonify(story_to_dict(s))


@app.get("/stories/<int:story_id>/start")
def story_start(story_id: int):
    s = Story.query.get_or_404(story_id)
    if not s.start_page_id:
        abort(409, description="Story has no start_page_id yet.")
    p = Page.query.get_or_404(s.start_page_id)
    choices = Choice.query.filter_by(page_id=p.id).order_by(Choice.id.asc()).all()
    return jsonify({
        "story": story_to_dict(s),
        "page": page_to_dict(p),
        "choices": [choice_to_dict(c) for c in choices],
    })


@app.get("/pages/<int:page_id>")
def get_page(page_id: int):
    p = Page.query.get_or_404(page_id)
    choices = Choice.query.filter_by(page_id=p.id).order_by(Choice.id.asc()).all()
    return jsonify({
        "page": page_to_dict(p),
        "choices": [choice_to_dict(c) for c in choices],
    })


# ---------------------------
# Writing endpoints (open at Level 10)
# ---------------------------

@app.post("/stories")
def create_story():
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        abort(400, description="Missing 'title'")
    s = Story(
        title=title,
        description=(data.get("description") or "").strip(),
        status=(data.get("status") or "draft").strip(),
        start_page_id=data.get("start_page_id"),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(story_to_dict(s)), 201


@app.put("/stories/<int:story_id>")
def update_story(story_id: int):
    s = Story.query.get_or_404(story_id)
    data = request.get_json(force=True, silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            abort(400, description="title cannot be empty")
        s.title = title
    if "description" in data:
        s.description = (data.get("description") or "").strip()
    if "status" in data:
        s.status = (data.get("status") or "draft").strip()
    if "start_page_id" in data:
        s.start_page_id = data.get("start_page_id")

    db.session.commit()
    return jsonify(story_to_dict(s))


@app.delete("/stories/<int:story_id>")
def delete_story(story_id: int):
    s = Story.query.get_or_404(story_id)

    # naive cascade delete for demo
    pages = Page.query.filter_by(story_id=s.id).all()
    page_ids = [p.id for p in pages]
    if page_ids:
        Choice.query.filter(Choice.page_id.in_(page_ids)).delete(synchronize_session=False)
        Page.query.filter(Page.id.in_(page_ids)).delete(synchronize_session=False)

    db.session.delete(s)
    db.session.commit()
    return "", 204


@app.post("/stories/<int:story_id>/pages")
def create_page(story_id: int):
    Story.query.get_or_404(story_id)
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        abort(400, description="Missing 'text'")
    p = Page(
        story_id=story_id,
        text=text,
        is_ending=bool(data.get("is_ending", False)),
        ending_label=(data.get("ending_label") or None),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(page_to_dict(p)), 201


@app.post("/pages/<int:page_id>/choices")
def create_choice(page_id: int):
    Page.query.get_or_404(page_id)
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    next_page_id = data.get("next_page_id")
    if not text:
        abort(400, description="Missing 'text'")
    if not isinstance(next_page_id, int):
        abort(400, description="Missing/invalid 'next_page_id' (must be int)")
    # ensure target page exists
    Page.query.get_or_404(next_page_id)

    c = Choice(page_id=page_id, text=text, next_page_id=next_page_id)
    db.session.add(c)
    db.session.commit()
    return jsonify(choice_to_dict(c)), 201


# ---------------------------
# Seed demo content
# ---------------------------

def seed_demo():
    existing = Story.query.count()
    if existing:
        return

    s = Story(title="The Metro at Midnight", description="You missed the last train. Or did you?", status="published")
    db.session.add(s)
    db.session.flush()  # get s.id

    p1 = Page(story_id=s.id, text="You arrive at the platform. The lights flicker.", is_ending=False)
    p2 = Page(story_id=s.id, text="A silent train arrives. Doors open.", is_ending=False)
    p3 = Page(story_id=s.id, text="You walk away. The station feels safer.", is_ending=True)
    p4 = Page(story_id=s.id, text="Inside the train, everything is… wrong.", is_ending=True)

    db.session.add_all([p1, p2, p3, p4])
    db.session.flush()

    s.start_page_id = p1.id

    c1 = Choice(page_id=p1.id, text="Enter the train", next_page_id=p2.id)
    c2 = Choice(page_id=p1.id, text="Leave the station", next_page_id=p3.id)
    c3 = Choice(page_id=p2.id, text="Sit down", next_page_id=p4.id)
    c4 = Choice(page_id=p2.id, text="Get off immediately", next_page_id=p3.id)

    db.session.add_all([c1, c2, c3, c4])
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_demo()

    app.run(host="127.0.0.1", port=5001, debug=True)
