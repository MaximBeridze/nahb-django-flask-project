import os
from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
db_url = os.getenv("DATABASE_URL", "sqlite:///nahb_content.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

API_KEY = os.getenv("API_KEY", "").strip()


def require_api_key():
    if not API_KEY:
        return
    if request.headers.get("X-API-KEY") != API_KEY:
        abort(401)


class Story(db.Model):
    __tablename__ = "stories"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(20), nullable=False, default="draft"
    )
    start_page_id = db.Column(db.Integer, db.ForeignKey("pages.id"), nullable=True)
    illustration_url = db.Column(db.String(500), nullable=True)

    pages = db.relationship(
        "Page", backref="story", lazy=True, foreign_keys="Page.story_id"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "start_page_id": self.start_page_id,
            "illustration_url": self.illustration_url,
        }


class Page(db.Model):
    __tablename__ = "pages"
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_ending = db.Column(db.Boolean, default=False)
    ending_label = db.Column(db.String(120), nullable=True)
    illustration_url = db.Column(db.String(500), nullable=True)

    choices = db.relationship(
        "Choice", backref="page", lazy=True, foreign_keys="Choice.page_id"
    )

    def to_dict(self, include_choices=False):
        data = {
            "id": self.id,
            "story_id": self.story_id,
            "text": self.text,
            "is_ending": bool(self.is_ending),
            "ending_label": self.ending_label,
            "illustration_url": self.illustration_url,
        }
        if include_choices:
            data["choices"] = [c.to_dict() for c in self.choices]
        return data


class Choice(db.Model):
    __tablename__ = "choices"
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("pages.id"), nullable=False)
    text = db.Column(db.String(240), nullable=False)
    next_page_id = db.Column(db.Integer, db.ForeignKey("pages.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "page_id": self.page_id,
            "text": self.text,
            "next_page_id": self.next_page_id,
        }


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/stories")
def list_stories():
    status = request.args.get("status")
    q = Story.query
    if status:
        q = q.filter_by(status=status)
    stories = q.order_by(Story.id.asc()).all()
    return jsonify([s.to_dict() for s in stories])


@app.get("/stories/<int:story_id>")
def get_story(story_id: int):
    s = Story.query.get_or_404(story_id)
    return jsonify(s.to_dict())


@app.get("/stories/<int:story_id>/start")
def get_story_start(story_id: int):
    s = Story.query.get_or_404(story_id)
    if not s.start_page_id:
        abort(404, description="Story has no start_page_id")
    p = Page.query.get_or_404(s.start_page_id)
    return jsonify(p.to_dict(include_choices=True))


@app.get("/stories/<int:story_id>/pages")
def list_story_pages(story_id: int):
    Story.query.get_or_404(story_id)
    pages = Page.query.filter_by(story_id=story_id).order_by(Page.id.asc()).all()
    return jsonify([p.to_dict(include_choices=True) for p in pages])


@app.get("/pages/<int:page_id>")
def get_page(page_id: int):
    p = Page.query.get_or_404(page_id)
    return jsonify(p.to_dict(include_choices=True))


@app.post("/stories")
def create_story():
    require_api_key()
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        abort(400, description="title is required")
    s = Story(
        title=title,
        description=(data.get("description") or "").strip(),
        status=(data.get("status") or "draft").strip(),
        start_page_id=data.get("start_page_id"),
        illustration_url=(data.get("illustration_url") or None),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@app.put("/stories/<int:story_id>")
def update_story(story_id: int):
    require_api_key()
    s = Story.query.get_or_404(story_id)
    data = request.get_json(force=True, silent=True) or {}
    for key in ("title", "description", "status", "start_page_id", "illustration_url"):
        if key in data:
            setattr(s, key, data[key])
    db.session.commit()
    return jsonify(s.to_dict())


@app.delete("/stories/<int:story_id>")
def delete_story(story_id: int):
    require_api_key()
    s = Story.query.get_or_404(story_id)
    pages = Page.query.filter_by(story_id=s.id).all()
    for p in pages:
        Choice.query.filter_by(page_id=p.id).delete()
        db.session.delete(p)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"deleted": True})


@app.post("/stories/<int:story_id>/pages")
def create_page(story_id: int):
    require_api_key()
    Story.query.get_or_404(story_id)
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        abort(400, description="text is required")
    p = Page(
        story_id=story_id,
        text=text,
        is_ending=bool(data.get("is_ending", False)),
        ending_label=(data.get("ending_label") or None),
        illustration_url=(data.get("illustration_url") or None),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@app.put("/pages/<int:page_id>")
def update_page(page_id: int):
    require_api_key()
    p = Page.query.get_or_404(page_id)
    data = request.get_json(force=True, silent=True) or {}
    for key in ("text", "is_ending", "ending_label", "illustration_url"):
        if key in data:
            setattr(p, key, data[key])
    db.session.commit()
    return jsonify(p.to_dict())


@app.delete("/pages/<int:page_id>")
def delete_page(page_id: int):
    require_api_key()
    p = Page.query.get_or_404(page_id)
    Choice.query.filter_by(page_id=p.id).delete()
    db.session.delete(p)
    db.session.commit()
    return jsonify({"deleted": True})


@app.post("/pages/<int:page_id>/choices")
def create_choice(page_id: int):
    require_api_key()
    Page.query.get_or_404(page_id)
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    next_page_id = data.get("next_page_id")
    if not text or not next_page_id:
        abort(400, description="text and next_page_id are required")
    Page.query.get_or_404(int(next_page_id))
    c = Choice(page_id=page_id, text=text, next_page_id=int(next_page_id))
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@app.delete("/choices/<int:choice_id>")
def delete_choice(choice_id: int):
    require_api_key()
    c = Choice.query.get_or_404(choice_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"deleted": True})

def storyseed():
    if Story.query.count() > 0:
        return

    # Story 1 - SCP Escape

    s = Story(
        title="SCP-6767: The King in Yellow.",
        description="A mysterious document causes a containment breach and anomalous radio transmissions at a remote Foundation site. The player takes on the role of a newly assigned staff member tasked with investigating and containing the anomaly, making critical decisions that lead to multiple possible endings.",
        status="published",
        illustration_url="https://picsum.photos/seed/scp6767/900/500",
    )
    db.session.add(s)
    db.session.commit()

    def add_page(text, is_ending=False, ending_label=None, illustration_url=None):
        p = Page(
            story_id=s.id,
            text=text,
            is_ending=is_ending,
            ending_label=ending_label,
            illustration_url=illustration_url,
        )
        db.session.add(p)
        db.session.commit()
        return p

    p_start = add_page(
        "You have been ordered to assist in damage control and reconnaissance. "
        "At Sector C, several containment rooms have been evacuated in a hurry—"
        "gurneys left mid-hallway, lights strobing, alarms long dead but still ringing in your head. "
        "Among the debris, you spot a thin strip of yellow script, partially burned, still warm to the touch.\n\n"
        "What do you do?",
        illustration_url="https://picsum.photos/seed/yellowscript/800/450",
    )

    p_survivors = add_page(
        "You push deeper into the sector, stepping over shattered glass and discarded respirators. "
        "Near a warped blast door, you hear shallow breathing. Two researchers are wedged behind it, "
        "white-knuckled and shaking, eyes fixed on something you can’t see.\n\n"
        "What do you do?",
        illustration_url="https://picsum.photos/seed/survivors/800/450",
    )

    p_logs = add_page(
        "You access the terminal to review the incident logs. The screen flickers, then stabilizes—"
        "and your radio crackles to life on its own.\n\n"
        "A voice rides the static. Not words exactly—more like a pattern that tries to settle in your mind.\n\n"
        "What do you do?",
        illustration_url="https://picsum.photos/seed/radio/800/450",
    )

    p_directive = add_page(
        "By morning, an encrypted directive arrives from Site Command.\n\n"
        "All materials related to SCP-6767 are to be destroyed. Any personnel showing signs of exposure are to be terminated. "
        "No exceptions. No debate.\n\n"
        "Your hands hover over the yellow script in your evidence bag.\n\n"
        "What do you do?",
        illustration_url="https://picsum.photos/seed/directive/800/450",
    )

    p_containment = add_page(
        "You reach the incineration unit. Heat rolls off the chamber door in slow waves, "
        "turning the air into a shimmering mirage.\n\n"
        "A technician looks up from the console and squints at your clearance badge.\n\n"
        '"What SCP are you disposing of?" they ask—casual, routine, unaware of how loud their voice sounds in the room.\n\n'
        "What do you do?",
        illustration_url="https://picsum.photos/seed/incinerator/800/450",
    )

    p_knowledge = add_page(
        "Later, you return to the evacuated containment chamber. The door is sealed—"
        "but the locking mechanism hangs open like it gave up.\n\n"
        "Inside, the cell is empty. No restraints torn. No blood. No breach foam. Just absence.\n\n"
        "A faint smell of ozone lingers, and the radio on your chest clicks once, like a throat clearing.\n\n"
        "What do you do?",
        illustration_url="https://picsum.photos/seed/emptycell/800/450",
    )

    p_king = add_page(
        "The lights dim. Not a power failure—more like the room decides it doesn’t need them.\n\n"
        "A silhouette forms at the edge of your vision: tall, wrong, grotesque in a way your brain refuses to fully render. "
        "You understand with sudden certainty that if you *truly* see it, you will not recover.\n\n"
        "A voice speaks from everywhere and nowhere at once:\n"
        '"Foolish mortal. You have come in search of me. I can grant you infinite knowledge—'
        'but it comes at a cost. Are you ready to become my disciple?"\n\n'
        "What do you do?",
        illustration_url="https://picsum.photos/seed/theking/800/450",
    )

    p_end_containment = add_page(
        "You watch the last fragment of yellow curl into ash. The air feels lighter immediately, "
        "like pressure released from the walls.\n\n"
        "The breach stabilizes. The anomaly is contained.\n\n"
        "For the first time since you entered Sector C, your radio stays silent.",
        is_ending=True,
        ending_label="Containment Ending",
        illustration_url="https://picsum.photos/seed/contained/800/450",
    )

    p_end_death = add_page(
        "Your refusal lands like an insult.\n\n"
        "The King’s presence tightens around you, and the world becomes white heat. You don’t even have time to scream.\n\n"
        "When your body fails, your consciousness doesn’t get the same mercy.\n\n"
        "You wake up in the static—trapped inside the radio’s endless hiss, listening forever to your own fear.",
        is_ending=True,
        ending_label="Death Ending",
        illustration_url="https://picsum.photos/seed/death/800/450",
    )

    p_end_king = add_page(
        "The King pauses, as if tasting your answer.\n\n"
        "Then it accepts.\n\n"
        "Knowledge floods your mind in a violent torrent—names, coordinates, formulas, histories that never happened and memories that feel older than time. "
        "Your thoughts fracture under the weight.\n\n"
        "When you finally look up, you realize you’re smiling.\n\n"
        "You are no longer a person.\n\n"
        "You are one of the King’s mindless servants.",
        is_ending=True,
        ending_label="King Ending",
        illustration_url="https://picsum.photos/seed/madness/800/450",
    )

    s.start_page_id = p_start.id
    db.session.commit()

    def add_choice(page, text, nxt):
        c = Choice(page_id=page.id, text=text, next_page_id=nxt.id)
        db.session.add(c)
        db.session.commit()

    add_choice(p_start, "Carefully secure the yellow script in an evidence sleeve and report its discovery to Site Command immediately (+1)", p_survivors)
    add_choice(p_start, "Ignore protocol for a moment and skim the script, trying to identify the anomaly yourself before anyone else arrives (-1)", p_logs)
    
    add_choice(p_survivors, "Lower your voice, steady their breathing, and promise the anomaly will be contained and they will survive this (+1)", p_directive)
    add_choice(p_survivors, "Press them for details about what they saw, prioritizing information over their mental state (-1)", p_directive,)

    add_choice(p_logs, "Immediately power down the radio, document the interference, and flag the signal as potential memetic contamination (+1)", p_directive,)
    add_choice(p_logs, "Hold the radio closer and listen carefully, trying to understand the pattern hidden inside the static (-1)", p_directive,)

    add_choice(p_directive, "Follow the directive without hesitation and move to incinerate the script before exposure spreads further (+1)", p_containment,)
    add_choice(p_directive, "Hide the script and falsify your report, convinced there is something valuable hidden inside it (-1)", p_knowledge,)

    add_choice(p_containment, "Tell the technician exactly which SCP you are disposing of, trusting protocol and transparency (+1)", p_end_containment,)
    add_choice(p_containment, "Refuse to answer and proceed alone, unwilling to let anyone else near the script (-1)", p_end_death,)

    add_choice(p_knowledge, "Trigger emergency containment procedures anyway, hoping protocol can still stop whatever escaped (+1)", p_king,)
    add_choice(p_knowledge, "Speak into the chamber, demanding that any entity present reveal itself to you (-1)", p_king,)

    add_choice(p_king, "Reject the entity outright, refusing knowledge that comes from something so clearly inhuman (+1)", p_end_death,)
    add_choice(p_king, "Accept the offer and submit, desperate to understand what lies beyond human knowledge (+1)", p_end_king,)


@app.before_request
def init_db():
    if not hasattr(init_db, "initialized"):
        db.create_all()
        storyseed()
        init_db.initialized = True


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)
