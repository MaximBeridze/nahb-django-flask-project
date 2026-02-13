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

    # Story 1 - SCP-6767 The King In Yellow

    s = Story(
        title="SCP-6767: The King in Yellow.",
        description="A mysterious document causes a containment breach and anomalous radio transmissions at a remote Foundation site. The player takes on the role of a newly assigned staff member tasked with investigating and containing the anomaly, making critical decisions that lead to multiple possible endings.",
        status="published",
        illustration_url="https://source.unsplash.com/1600x900/?abandoned,lab,horror",
        
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
        illustration_url="https://devforum-uploads.s3.dualstack.us-east-2.amazonaws.com/uploads/optimized/5X/2/3/2/5/232581946f9d3e5a9c27ec9c7b12ab74cfd6ab3e_2_690x388.jpeg",
    )

    p_survivors = add_page(
        "You push deeper into the sector, stepping over shattered glass and discarded respirators. "
        "Near a warped blast door, you hear shallow breathing. Two researchers are wedged behind it, "
        "white-knuckled and shaking, eyes fixed on something you can't see.\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?dark,radio,old,technology,horror",
    )

    p_logs = add_page(
        "You access the terminal to review the incident logs. The screen flickers, then stabilizes—"
        "and your radio crackles to life on its own.\n\n"
        "A voice rides the static. Not words exactly—more like a pattern that tries to settle in your mind.\n\n"
        "What do you do?",
        illustration_url="https://halo.wiki.gallery/images/thumb/9/91/HINF_UNSC_Data_Pad_Audio_Log.png/1200px-HINF_UNSC_Data_Pad_Audio_Log.png",
    )

    p_directive = add_page(
        "By morning, an encrypted directive arrives from Site Command.\n\n"
        "All materials related to SCP-6767 are to be destroyed. Any personnel showing signs of exposure are to be terminated. "
        "No exceptions. No debate.\n\n"
        "Your hands hover over the yellow script in your evidence bag.\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?dark,industrial,incinerator,factory",
    )

    p_containment = add_page(
        "You reach the incineration unit. Heat rolls off the chamber door in slow waves, "
        "turning the air into a shimmering mirage.\n\n"
        "A technician looks up from the console and squints at your clearance badge.\n\n"
        '"What SCP are you disposing of?" they ask—casual, routine, unaware of how loud their voice sounds in the room.\n\n'
        "What do you do?",
        illustration_url="https://i.redd.it/ovy4ny998xod1.png",
    )

    p_knowledge = add_page(
        "Later, you return to the evacuated containment chamber. The door is sealed—"
        "but the locking mechanism hangs open like it gave up.\n\n"
        "Inside, the cell is empty. No restraints torn. No blood. No breach foam. Just absence.\n\n"
        "A faint smell of ozone lingers, and the radio on your chest clicks once, like a throat clearing.\n\n"
        "What do you do?",
        illustration_url="https://i.ytimg.com/vi/Z5XjJwgW2wI/maxresdefault.jpg",
    )

    p_king = add_page(
        "The lights dim. Not a power failure—more like the room decides it doesn't need them.\n\n"
        "A silhouette forms at the edge of your vision: tall, wrong, grotesque in a way your brain refuses to fully render. "
        "You understand with sudden certainty that if you *truly* see it, you will not recover.\n\n"
        "A voice speaks from everywhere and nowhere at once:\n"
        '"Foolish mortal. You have come in search of me. I can grant you infinite knowledge—'
        'but it comes at a cost. Are you ready to become my disciple?"\n\n'
        "What do you do?",
        illustration_url="https://i.ytimg.com/vi/Z5XjJwgW2wI/maxresdefault.jpg",
    )

    p_end_containment = add_page(
        "You watch the last fragment of yellow curl into ash. The air feels lighter immediately, "
        "like pressure released from the walls.\n\n"
        "The breach stabilizes. The anomaly is contained.\n\n"
        "For the first time since you entered Sector C, your radio stays silent.",
        is_ending=True,
        ending_label="Containment Ending",
        illustration_url="https://img.itch.zone/aW1nLzk2NDc1NzMucG5n/original/UatqFC.png",
    )

    p_end_death = add_page(
        "Your refusal lands like an insult.\n\n"
        "The King's presence tightens around you, and the world becomes white heat. You don't even have time to scream.\n\n"
        "When your body fails, your consciousness doesn't get the same mercy.\n\n"
        "You wake up in the static—trapped inside the radio's endless hiss, listening forever to your own fear.",
        is_ending=True,
        ending_label="Death Ending",
        illustration_url="https://static.vecteezy.com/system/resources/thumbnails/011/869/811/small_2x/halloween-human-skull-on-an-old-wooden-table-over-black-background-shape-of-skull-bone-for-death-head-on-halloween-festival-which-show-horror-evil-tooth-fear-and-scary-with-fog-smoke-copy-space-photo.jpg",
    )

    p_end_king = add_page(
        "The King pauses, as if tasting your answer.\n\n"
        "Then it accepts.\n\n"
        "Knowledge floods your mind in a violent torrent—names, coordinates, formulas, histories that never happened and memories that feel older than time. "
        "Your thoughts fracture under the weight.\n\n"
        "When you finally look up, you realize you're smiling.\n\n"
        "You are no longer a person.\n\n"
        "You are one of the King's mindless servants.",
        is_ending=True,
        ending_label="King Ending",
        illustration_url="https://f4.bcbits.com/img/0021886516_71.jpg",
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
    add_choice(p_survivors, "Press them for details about what they saw, prioritizing information over their mental state (-1)", p_directive)

    add_choice(p_logs, "Immediately power down the radio, document the interference, and flag the signal as potential memetic contamination (+1)", p_directive)
    add_choice(p_logs, "Hold the radio closer and listen carefully, trying to understand the pattern hidden inside the static (-1)", p_directive)

    add_choice(p_directive, "Follow the directive without hesitation and move to incinerate the script before exposure spreads further (+1)", p_containment)
    add_choice(p_directive, "Hide the script and falsify your report, convinced there is something valuable hidden inside it (-1)", p_knowledge)

    add_choice(p_containment, "Tell the technician exactly which SCP you are disposing of, trusting protocol and transparency (+1)", p_end_containment)
    add_choice(p_containment, "Refuse to answer and proceed alone, unwilling to let anyone else near the script (-1)", p_end_death)

    add_choice(p_knowledge, "Trigger emergency containment procedures anyway, hoping protocol can still stop whatever escaped (+1)", p_king)
    add_choice(p_knowledge, "Speak into the chamber, demanding that any entity present reveal itself to you (-1)", p_king)

    add_choice(p_king, "Reject the entity outright, refusing knowledge that comes from something so clearly inhuman (+1)", p_end_death)
    add_choice(p_king, "Accept the offer and submit, desperate to understand what lies beyond human knowledge (+1)", p_end_king)

    # Story 2 - Dragon Frontier

    s2 = Story(
        title="Dragon Frontier: The Baby in the Ruins",
        description="Sent by the King to pacify a monster-raided frontier, you discover a baby dragon. Your loyalty will shape war, peace, or ruin.",
        status="published",
        illustration_url="https://source.unsplash.com/1600x900/?destroyed,medieval,village,ruins",
    )
    db.session.add(s2)
    db.session.commit()

    def add_page2(text, is_ending=False, ending_label=None, illustration_url=None):
        p = Page(
            story_id=s2.id,
            text=text,
            is_ending=is_ending,
            ending_label=ending_label,
            illustration_url=illustration_url,
        )
        db.session.add(p)
        db.session.commit()
        return p

    def add_choice2(page, text, nxt):
        c = Choice(page_id=page.id, text=text, next_page_id=nxt.id)
        db.session.add(c)
        db.session.commit()

    p_intro = add_page2(
        "You are the King's most trusted knight.\n\n"
        "At dawn, a sealed directive arrives: the monster raids on the south-eastern frontier have made the region \"unsafe for re-habitation.\" "
        "Your mission is simple on paper—reconnaissance, damage control, and a final solution.\n\n"
        "By dusk, you reach the village.\n"
        "It's not a battlefield anymore—it's an aftermath. Charred beams. Crushed stone. The smell of smoke baked into the earth.\n\n"
        "In the ruins of a home, you find something impossible:\n"
        "a baby dragon—injured, trembling, and far too young to understand hatred.\n\n"
        "What do you do?",
        illustration_url="https://media.gq.com/photos/698cba3d848b4dd435a76854/3:2/w_1920,h_1280,c_limit/A%20knight%20of%20the%20seven%20kingdoms_0013_01_02_AKOTSK_S01%20(1).jpg",
    )

    p_scout = add_page2(
        "You force yourself to look away from the hatchling.\n\n"
        "You circle the village and mark the damage: clawed doorframes, scorched wells, livestock pens torn open. "
        "But you also notice something else—too organized to be \"random monster violence.\"\n\n"
        "Near the treeline, you spot tracks. Small ones. Many.\n"
        "Goblins.\n\n"
        "One thought won't leave you: if goblins are here, something bigger is nearby.\n\n"
        "What do you do?",
        illustration_url="https://cdna.artstation.com/p/assets/images/images/003/485/712/large/kaiyuan-lou-092-02.jpg?1474228242",
    )

    p_survivors = add_page2(
        "You go door to door through the wreckage until you find them—survivors.\n\n"
        "They emerge from hiding like ghosts: soot-stained, starving, furious. "
        "Their story spills out in fragments—night raids, goblin laughter, wings overhead, and fire that didn't care who prayed.\n\n"
        "They curse all monsters as one and beg you to wipe them out.\n"
        "Yet when they speak of the goblins, their anger sounds almost… rehearsed.\n\n"
        "What do you do?",
        illustration_url="https://images.stockcake.com/public/a/0/0/a003ca98-98ce-4219-a12c-514aab6b058f_large/knight-by-firelight-stockcake.jpg",
    )

    p_shelter = add_page2(
        "You build a shelter from broken lumber and salvaged canvas.\n\n"
        "The villagers gather inside, huddled close, watching you like you're the last wall between them and extinction.\n\n"
        "That night, while you stand guard, you hear it again—soft, unfamiliar noises from the ruins.\n"
        "The baby dragon.\n\n"
        "Hungry. Hurt. Alive.\n\n"
        "What do you do?",
        illustration_url="https://www.zbrushcentral.com/uploads/default/original/4X/7/6/4/76404d6b6a2cf4263ee28413ca0c35b668d06026.jpeg",
    )

    p_kings_orders = add_page2(
        "Morning brings a royal messenger—mud on his boots, fear in his eyes.\n\n"
        "\"My lord,\" he says, \"the King has heard rumors… of a dragon.\"\n\n"
        "He lowers his voice as if the air itself might report him.\n"
        "\"The King's law is clear: eliminate it. No survivors. No witnesses.\"\n\n"
        "Then the messenger adds quietly:\n"
        "\"And… be careful. The King has other knights. If you hesitate, they will arrive—and they will not.\"\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?dragon,baby,fantasy,fire",
    )

    p_forest = add_page2(
        "You return to the ruins.\n\n"
        "The baby dragon is gone.\n\n"
        "No blood. No struggle. Just the imprint where it slept—warm ash and tiny claw marks leading toward the forest.\n\n"
        "You follow the trail under the canopy until the air changes.\n"
        "You smell damp earth… and something older.\n\n"
        "Then you see them.\n"
        "A goblin horde clustered around a crude camp, watching over the hatchling like it's treasure.\n\n"
        "And then you hear it.\n"
        "One of the goblins is speaking—slowly, carefully… in your language.\n\n"
        "What do you do?",
        illustration_url="https://imaginarycreatureauthority.wordpress.com/wp-content/uploads/2020/03/goblin6.jpg?w=512",
    )

    p_kill_goblins = add_page2(
        "Steel leaves its scabbard with a sound that turns heads.\n\n"
        "You move fast—too fast for superstition to save them. Goblins fall. The hatchling screams.\n\n"
        "Behind the camp, the underbrush splits.\n"
        "A shadow rises.\n\n"
        "An adult dragon steps into view—ancient, scarred, and furious.\n"
        "Its gaze locks onto you like judgment.\n\n"
        "What do you do?",
        illustration_url="https://media.wired.com/photos/6307febeba2a66af641b11df/3:2/w_2560%2Cc_limit/House-of-the-Dragon-CGI-Culture.jpg",
    )

    p_mercy = add_page2(
        "You hold your blade low.\n\n"
        "\"Talk,\" you demand.\n\n"
        "The goblins flinch—but they don't attack. The one who spoke before swallows and tries again.\n\n"
        "\"This town… was ours. Before humans.\"\n"
        "\"Thirty winters ago… your King sent men. They took the land. They killed almost everyone who lived here.\"\n\n"
        "The goblin gestures toward the hatchling.\n"
        "\"We didn't come for sport. We came for what was stolen.\"\n\n"
        "If they're lying, you are standing in front of an organized ambush.\n"
        "If they're telling the truth… you've been protecting a crime.\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?fantasy,peace,alliance,castle",
    )

    p_alliance = add_page2(
        "You choose belief over reflex.\n\n"
        "The goblins exchange glances—uncertain, suspicious, but not hostile.\n\n"
        "\"Follow,\" the translator says.\n\n"
        "They lead you deeper into the forest, beyond paths your maps refuse to acknowledge.\n\n"
        "In a clearing, you see her.\n"
        "A Great Dragon—massive, regal, and terrifyingly calm.\n\n"
        "The hatchling presses against her, safe.\n\n"
        "The dragon's voice enters your mind like a slow tide.\n"
        "\"Human knight. You smell of law and lies. Why have you come?\"\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?abandoned,lab,horror",
    )

    p_friendly_fire = add_page2(
        "You turn your cloak inside out and return with a story the King wants to hear.\n\n"
        "The court believes you.\n"
        "The banners rise.\n"
        "The army marches.\n\n"
        "But betrayal has a scent.\n\n"
        "The King's spies find the cracks in your report. A second team follows your trail—"
        "not to help you, but to erase you.\n\n"
        "By the time you reach Black Hollow again, the battle has already started.\n"
        "Humans and monsters collide in fire and iron.\n\n"
        "You stand at the center of it, realizing too late that you've lit a fuse you cannot extinguish.\n\n"
        "What do you do?",
        illustration_url="https://source.unsplash.com/1600x900/?containment,facility,industrial,underground",
    )

    p_peace = add_page2(
        "You negotiate.\n\n"
        "Not with pride. Not with threats.\n"
        "With truth.\n\n"
        "You send a messenger to the King carrying terms that could end bloodshed:\n"
        "territory boundaries, reparations, and a promise—no more hunting what was never yours.\n\n"
        "Days pass.\n"
        "Then an answer returns.\n\n"
        "The King agrees—reluctantly.\n"
        "But he makes it clear: if peace fails, the blame is yours.\n\n"
        "For now, the frontier breathes.\n"
        "Humans and monsters share the valley with teeth still bared… but not yet biting.",
        is_ending=True,
        ending_label="Peace Treaty",
        illustration_url="https://cdn.mos.cms.futurecdn.net/49k67SjTD5eyoqCuFKdFcZ.jpg",
    )

    p_end_human = add_page2(
        "You choose the kingdom.\n\n"
        "You strike down the dragons and scatter what remains of the horde. The hatchling's cries fade into the forest smoke.\n\n"
        "The village is saved—rebuilt atop ash and silence.\n\n"
        "The King hears of your victory and rewards you in public.\n"
        "A title. Land. Honor.\n\n"
        "At night, you remember the hatchling's eyes.\n"
        "And you wonder what kind of peace is built from mercy denied.",
        is_ending=True,
        ending_label="Human Victory",
        illustration_url="https://swordoficastrastories.files.wordpress.com/2014/11/dragon6_by_benflores-d84ju1c.jpg?w=580&h=580&crop=1",
    )

    p_end_monster = add_page2(
        "You choose the monsters.\n\n"
        "You sabotage the human advance and turn steel against your own. The Great Dragon's fire becomes your banner.\n\n"
        "The human army breaks.\n"
        "The frontier falls.\n\n"
        "The Great Dragon watches the village burn—not in rage, but in closure.\n\n"
        "When it's done, treasure is placed at your feet like payment for loyalty.\n"
        "Gold and jewelry, warm from the pile.\n\n"
        "And yet you feel no richer.",
        is_ending=True,
        ending_label="Monster Victory",
        illustration_url="https://pyxis.nymag.com/v1/imgs/fe5/d08/5bc8bd12d9b19a13864f6339db0a1345f4-07-got-704.jpg",
    )

    p_gate = add_page2(
        "The valley holds its breath.\n\n"
        "Your choices have already been made. Your intentions—mercy, cruelty, loyalty—have weight.\n\n"
        "The outcome is decided now.",
        is_ending=False,
        illustration_url="https://source.unsplash.com/1600x900/?empty,prison,cell,concrete,dark",
    )

    p_gate.ending_label = (
        f"SCORE_GATE|human:{p_end_human.id}|peace:{p_peace.id}|monster:{p_end_monster.id}"
    )
    db.session.commit()

    s2.start_page_id = p_intro.id
    db.session.commit()


    add_choice2(
        p_intro,
        "Report the hatchling immediately and treat it as a hostile anomaly under royal law (+1)",
        p_scout,
    )
    add_choice2(
        p_intro,
        "Hide the hatchling's existence for now—observe before you condemn (-1)",
        p_scout,
    )


    add_choice2(
        p_scout,
        "Survey the perimeter like a commander: tracks, patterns, weaknesses (+1)",
        p_survivors,
    )
    add_choice2(
        p_scout,
        "Follow the goblin tracks alone, ignoring the risk of an ambush (-1)",
        p_survivors,
    )


    add_choice2(
        p_survivors,
        "Reassure the villagers and promise protection before taking action (+1)",
        p_shelter,
    )
    add_choice2(
        p_survivors,
        "Feed their hatred: swear you will slaughter every monster that comes near (-1)",
        p_shelter,
    )


    add_choice2(
        p_shelter,
        "Warn the survivors about the hatchling and post guards to prevent panic (+1)",
        p_kings_orders,
    )
    add_choice2(
        p_shelter,
        "Secretly leave food for the hatchling and keep its existence quiet (-1)",
        p_kings_orders,
    )


    add_choice2(
        p_kings_orders,
        "Accept the order publicly—buy time by appearing loyal (+1)",
        p_forest,
    )
    add_choice2(
        p_kings_orders,
        "Lie to the messenger: claim there is no dragon, and act alone (-1)",
        p_forest,
    )


    add_choice2(
        p_forest,
        "Attack the goblins before they can react—protect humans by force (+1)",
        p_kill_goblins,
    )
    add_choice2(
        p_forest,
        "Hold your strike and speak—if they know your language, they may know the truth (-1)",
        p_mercy,
    )


    add_choice2(
        p_kill_goblins,
        "Finish it: kill the adult dragon and end the threat permanently (+1)",
        p_gate,
    )
    add_choice2(
        p_kill_goblins,
        "Lower your blade—there has been enough killing today (-1)",
        p_gate,
    )


    add_choice2(
        p_mercy,
        "Believe their story and follow them to the one who commands the dragons (-1)",
        p_alliance,
    )
    add_choice2(
        p_mercy,
        "Call them liars and cut them down before they can manipulate you (+1)",
        p_kill_goblins,
    )


    add_choice2(
        p_alliance,
        "Offer terms: propose a treaty and send a messenger back to the King (-1)",
        p_gate,
    )
    add_choice2(
        p_alliance,
        "Betray the Great Dragon—lead the human army here for an easy victory (+1)",
        p_friendly_fire,
    )


    add_choice2(
        p_friendly_fire,
        "Stand with the Great Dragon and help the monsters break the human army (-1)",
        p_gate,
    )
    add_choice2(
        p_friendly_fire,
        "Turn on the monsters and fight for the humans in the name of justice (+1)",
        p_gate,
    )


@app.before_request
def init_db():
    if not hasattr(init_db, "initialized"):
        db.create_all()
        storyseed()
        init_db.initialized = True


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)
