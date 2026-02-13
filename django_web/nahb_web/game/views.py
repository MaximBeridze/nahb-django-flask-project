import json
import random
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Avg
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Play, PlaySession, StoryOwnership, Rating, Report
from .forms import StoryForm, PageForm, ChoiceForm, RatingForm, ReportForm
from .services import api_get, api_post, api_put, api_delete, parse_score_delta


def author_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_author(request.user):
            return HttpResponseForbidden(
                "You need Author access to view this page. "
                "Ask an admin to add your account to the Authors group."
            )
        return view_func(request, *args, **kwargs)
    _wrapped.__name__ = view_func.__name__
    return _wrapped


def admin_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            return HttpResponseForbidden("Staff access required.")
        return view_func(request, *args, **kwargs)
    _wrapped.__name__ = view_func.__name__
    return _wrapped


def parse_score_gate(label: str):
    parts = (label or "").split("|")
    if not parts or parts[0] != "SCORE_GATE":
        return None
    out = {}
    for chunk in parts[1:]:
        if ":" in chunk:
            k, v = chunk.split(":", 1)
            if v.isdigit():
                out[k] = int(v)
    return out if {"human", "peace", "monster"} <= set(out.keys()) else None


def is_author(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="Authors").exists())


def is_admin(user):
    return user.is_authenticated and user.is_staff


def require_story_owner_or_admin(user, story_id: int) -> bool:
    if user.is_staff:
        return True
    return StoryOwnership.objects.filter(story_id=story_id, owner=user).exists()


def story_list(request):
    q = request.GET.get("q", "").strip()
    stories = api_get("/stories", params={"status": "published"})
    if q:
        stories = [s for s in stories if q.lower() in (s.get("title","").lower() + " " + s.get("description","").lower())]
    ids = [s["id"] for s in stories]
    rating_map = {r["story_id"]: r for r in Rating.objects.filter(story_id__in=ids).values("story_id").annotate(avg=Avg("stars"), count=Count("id"))}
    for s in stories:
        agg = rating_map.get(s["id"])
        s["rating_avg"] = float(agg["avg"]) if agg and agg["avg"] is not None else None
        s["rating_count"] = int(agg["count"]) if agg else 0
    return render(request, "story_list.html", {"stories": stories, "q": q})


def story_detail(request, story_id: int):
    story = api_get(f"/stories/{story_id}")
    if story.get("status") != "published" and not (request.user.is_authenticated and require_story_owner_or_admin(request.user, story_id)):
        raise Http404("Story not available")

    rating_agg = Rating.objects.filter(story_id=story_id).aggregate(avg=Avg("stars"), count=Count("id"))
    my_rating = None
    if request.user.is_authenticated:
        my_rating = Rating.objects.filter(story_id=story_id, user=request.user).first()

    return render(request, "story_detail.html", {
        "story": story,
        "rating_avg": rating_agg["avg"],
        "rating_count": rating_agg["count"],
        "my_rating": my_rating,
    })


@require_http_methods(["GET","POST"])
def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created.")
        return redirect("story_list")
    return render(request, "register.html", {"form": form})


@login_required
def play_start(request, story_id: int):
    story = api_get(f"/stories/{story_id}")
    if story.get("status") != "published":
        raise Http404("Story not published")
    page = api_get(f"/stories/{story_id}/start")

    sess, _ = PlaySession.objects.update_or_create(
        user=request.user, story_id=story_id,
        defaults={
            "current_page_id": page["id"],
            "score": 0,
            "path": [page["id"]],
            "last_roll": None,
        },
    )
    return redirect("play_page", story_id=story_id, page_id=page["id"])


@login_required
def play_resume(request, story_id: int):
    sess = PlaySession.objects.filter(user=request.user, story_id=story_id).first()
    if not sess:
        return redirect("play_start", story_id=story_id)
    try:
        page = api_get(f"/pages/{sess.current_page_id}")
        if parse_score_gate(page.get("ending_label")) or page.get("is_ending"):
            sess.delete()
            return redirect("play_start", story_id=story_id)
    except Exception:
        pass
    return redirect("play_page", story_id=story_id, page_id=sess.current_page_id)


def _choice_allowed_by_roll(choice_text: str, roll: int | None) -> bool:
    if roll is None:
        return "[roll>=" not in (choice_text or "").lower()
    m = None
    try:
        m = __import__("re").search(r"\[roll\s*>=\s*(\d)\]", choice_text or "", flags=__import__("re").I)
    except Exception:
        m = None
    if not m:
        return True
    need = int(m.group(1))
    return roll >= need


@login_required
@require_http_methods(["GET","POST"])
def play_page(request, story_id: int, page_id: int):
    sess = PlaySession.objects.filter(user=request.user, story_id=story_id).first()
    if not sess:
        return redirect("play_start", story_id=story_id)

    page = api_get(f"/pages/{page_id}")
    gate = parse_score_gate(page.get("ending_label"))
    if gate:
        if sess.score >= 3:
            target_id = gate["human"]
        elif sess.score <= -3:
            target_id = gate["monster"]
        else:
            target_id = gate["peace"]

        ending_page = api_get(f"/pages/{target_id}")
        final_score = sess.score
        final_path = (sess.path or []) + [target_id]

        Play.objects.create(
            user=request.user,
            story_id=story_id,
            ending_page_id=target_id,
            ending_label=ending_page.get("ending_label") or "",
            score=final_score,
            path=final_path,
        )
        sess.delete()
        return render(request, "ending.html", {
            "story_id": story_id,
            "page": ending_page,
            "score": final_score,
        })


    if page.get("is_ending"):
        final_score = sess.score
        final_path = sess.path or []
        Play.objects.create(
            user=request.user,
            story_id=story_id,
            ending_page_id=page_id,
            ending_label=page.get("ending_label") or "",
            score=final_score,
            path=final_path,
        )
        sess.delete()
        return render(request, "ending.html", {
            "story_id": story_id,
            "page": page,
            "score": final_score,
        })

    if request.method == "POST" and request.POST.get("action") == "roll":
        sess.last_roll = random.randint(1, 6)
        sess.save()
        messages.info(request, f"You rolled a {sess.last_roll}.")
        return redirect("play_page", story_id=story_id, page_id=page_id)

    choices = page.get("choices", [])
    choices = [c for c in choices if _choice_allowed_by_roll(c.get("text",""), sess.last_roll)]

    if request.method == "POST" and request.POST.get("action") == "choose":
        if sess.current_page_id != page_id:
            return redirect("play_page", story_id=story_id, page_id=sess.current_page_id)

        raw_choice_id = request.POST.get("choice_id")
        if not raw_choice_id:
            return redirect("play_page", story_id=story_id, page_id=page_id)
        choice_id = int(raw_choice_id)
        chosen = next((c for c in choices if c["id"] == choice_id), None)
        if not chosen:
            raise Http404("Choice not found")

        delta = parse_score_delta(chosen.get("text",""))
        next_page_id = int(chosen["next_page_id"])

        sess.current_page_id = next_page_id
        sess.score = sess.score + delta
        sess.path = (sess.path or []) + [next_page_id]
        sess.last_roll = None
        sess.save()

        next_page = api_get(f"/pages/{next_page_id}")

        next_gate = parse_score_gate(next_page.get("ending_label"))
        if next_gate:
            if sess.score >= 3:
                target_id = next_gate["human"]
            elif sess.score <= -3:
                target_id = next_gate["monster"]
            else:
                target_id = next_gate["peace"]

            ending_page = api_get(f"/pages/{target_id}")
            final_score = sess.score
            final_path = (sess.path or []) + [target_id]

            Play.objects.create(
                user=request.user,
                story_id=story_id,
                ending_page_id=target_id,
                ending_label=ending_page.get("ending_label") or "",
                score=final_score,
                path=final_path,
            )
            sess.delete()
            return render(request, "ending.html", {
                "story_id": story_id,
                "page": ending_page,
                "score": final_score,
            })

        if next_page.get("is_ending"):
            final_score = sess.score
            final_path = sess.path or []

            Play.objects.create(
                user=request.user,
                story_id=story_id,
                ending_page_id=next_page_id,
                ending_label=next_page.get("ending_label") or "",
                score=final_score,
                path=final_path,
            )

            sess.delete()
            return render(request, "ending.html", {"story_id": story_id, "page": next_page, "score": final_score})

        return redirect("play_page", story_id=story_id, page_id=next_page_id)

    needs_roll = any("[roll>=" in (c.get("text","").lower()) for c in page.get("choices", []))
    return render(request, "play_page.html", {
        "story_id": story_id,
        "page": page,
        "choices": choices,
        "score": sess.score,
        "last_roll": sess.last_roll,
        "needs_roll": needs_roll,
    })


@login_required
@require_http_methods(["GET","POST"])
def rate_story(request, story_id: int):
    story = api_get(f"/stories/{story_id}")
    if story.get("status") != "published":
        raise Http404("Story not published")
    existing = Rating.objects.filter(user=request.user, story_id=story_id).first()
    form = RatingForm(request.POST or None, initial={
        "stars": existing.stars if existing else 5,
        "comment": existing.comment if existing else "",
    })
    if request.method == "POST" and form.is_valid():
        Rating.objects.update_or_create(
            user=request.user, story_id=story_id,
            defaults={"stars": form.cleaned_data["stars"], "comment": form.cleaned_data["comment"]},
        )
        messages.success(request, "Rating saved.")
        return redirect("story_detail", story_id=story_id)
    return render(request, "rate_story.html", {"story": story, "form": form})


@login_required
@require_http_methods(["GET","POST"])
def report_story(request, story_id: int):
    story = api_get(f"/stories/{story_id}")
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Report.objects.create(user=request.user, story_id=story_id, reason=form.cleaned_data["reason"])
        messages.success(request, "Report submitted. Thank you.")
        return redirect("story_detail", story_id=story_id)
    return render(request, "report_story.html", {"story": story, "form": form})


@login_required
def my_history(request):
    plays = Play.objects.filter(user=request.user).order_by("-created_at")[:200]
    return render(request, "my_history.html", {"plays": plays})


def stats(request):
    if request.user.is_authenticated and not request.user.is_staff:
        plays_per_story = (Play.objects.filter(user=request.user).values("story_id").annotate(count=Count("id")).order_by("-count"))
        endings = (Play.objects.filter(user=request.user).values("story_id","ending_label").annotate(count=Count("id")).order_by("story_id","-count"))
        scope = "Your stats"
    else:
        plays_per_story = (Play.objects.values("story_id").annotate(count=Count("id")).order_by("-count"))
        endings = (Play.objects.values("story_id","ending_label").annotate(count=Count("id")).order_by("story_id","-count"))
        scope = "Global stats"
    return render(request, "stats.html", {"plays_per_story": plays_per_story, "endings": endings, "scope": scope})


@author_required
def author_dashboard(request):
    stories = api_get("/stories")
    if not request.user.is_staff:
        owned_ids = set(StoryOwnership.objects.filter(owner=request.user).values_list("story_id", flat=True))
        stories = [s for s in stories if s["id"] in owned_ids]
    return render(request, "author_dashboard.html", {"stories": stories})


@author_required
@require_http_methods(["GET","POST"])
def story_create(request):
    form = StoryForm(request.POST or None, initial={"status":"draft"})
    if request.method == "POST" and form.is_valid():
        s = api_post("/stories", form.cleaned_data)
        StoryOwnership.objects.get_or_create(story_id=s["id"], owner=request.user)
        return redirect("story_edit", story_id=s["id"])
    return render(request, "story_form.html", {"form": form, "mode": "create"})


@author_required
@require_http_methods(["GET","POST"])
def story_edit(request, story_id: int):
    if not require_story_owner_or_admin(request.user, story_id):
        return HttpResponseForbidden("Not your story.")
    story = api_get(f"/stories/{story_id}")
    pages = api_get(f"/stories/{story_id}/pages")
    form = StoryForm(request.POST or None, initial=story)
    if request.method == "POST" and form.is_valid():
        api_put(f"/stories/{story_id}", form.cleaned_data)
        messages.success(request, "Story updated.")
        return redirect("story_edit", story_id=story_id)
    return render(request, "story_edit.html", {"story": story, "form": form, "pages": pages})


@author_required
@require_http_methods(["POST"])
def story_delete(request, story_id: int):
    if not require_story_owner_or_admin(request.user, story_id):
        return HttpResponseForbidden("Not your story.")
    api_delete(f"/stories/{story_id}")
    StoryOwnership.objects.filter(story_id=story_id).delete()
    messages.success(request, "Story deleted.")
    return redirect("author_dashboard")


@author_required
@require_http_methods(["GET","POST"])
def page_create(request, story_id: int):
    if not require_story_owner_or_admin(request.user, story_id):
        return HttpResponseForbidden("Not your story.")
    story = api_get(f"/stories/{story_id}")
    form = PageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        p = api_post(f"/stories/{story_id}/pages", form.cleaned_data)
        if not story.get("start_page_id"):
            api_put(f"/stories/{story_id}", {"start_page_id": p["id"]})
        messages.success(request, "Page created.")
        return redirect("story_edit", story_id=story_id)
    return render(request, "page_form.html", {"story": story, "form": form})


@author_required
@require_http_methods(["GET","POST"])
def page_edit(request, page_id: int):
    page = api_get(f"/pages/{page_id}")
    if not require_story_owner_or_admin(request.user, page["story_id"]):
        return HttpResponseForbidden("Not your story.")
    form = PageForm(request.POST or None, initial=page)
    if request.method == "POST" and form.is_valid():
        api_put(f"/pages/{page_id}", form.cleaned_data)
        messages.success(request, "Page updated.")
        return redirect("story_edit", story_id=page["story_id"])
    return render(request, "page_edit.html", {"page": page, "form": form})


@author_required
@require_http_methods(["POST"])
def page_delete(request, page_id: int):
    page = api_get(f"/pages/{page_id}")
    if not require_story_owner_or_admin(request.user, page["story_id"]):
        return HttpResponseForbidden("Not your story.")
    api_delete(f"/pages/{page_id}")
    messages.success(request, "Page deleted.")
    return redirect("story_edit", story_id=page["story_id"])


@author_required
@require_http_methods(["GET","POST"])
def choice_create(request, page_id: int):
    page = api_get(f"/pages/{page_id}")
    if not require_story_owner_or_admin(request.user, page["story_id"]):
        return HttpResponseForbidden("Not your story.")
    form = ChoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        api_post(f"/pages/{page_id}/choices", form.cleaned_data)
        messages.success(request, "Choice created.")
        return redirect("story_edit", story_id=page["story_id"])
    return render(request, "choice_form.html", {"page": page, "form": form})


@author_required
@require_http_methods(["POST"])
def choice_delete(request, choice_id: int, story_id: int):
    if not require_story_owner_or_admin(request.user, story_id):
        return HttpResponseForbidden("Not your story.")
    api_delete(f"/choices/{choice_id}")
    messages.success(request, "Choice deleted.")
    return redirect("story_edit", story_id=story_id)


@admin_required
def moderation(request):
    stories = api_get("/stories")
    reports = Report.objects.order_by("-created_at")[:200]
    return render(request, "moderation.html", {"stories": stories, "reports": reports})


@admin_required
@require_http_methods(["POST"])
def set_story_status(request, story_id: int):
    status = request.POST.get("status")
    if status not in ("draft", "published", "suspended"):
        raise Http404()
    api_put(f"/stories/{story_id}", {"status": status})
    messages.success(request, f"Story status set to {status}.")
    return redirect("moderation")


@admin_required
@require_http_methods(["POST"])
def resolve_report(request, report_id: int):
    r = get_object_or_404(Report, id=report_id)
    r.resolved = True
    r.save()
    messages.success(request, "Report resolved.")
    return redirect("moderation")


def story_graph(request, story_id: int):
    story = api_get(f"/stories/{story_id}")
    pages = api_get(f"/stories/{story_id}/pages")
    nodes = []
    edges = []
    for p in pages:
        label = f"{p['id']}"
        if p.get("is_ending"):
            label += "\n(END)"
        elif parse_score_gate(p.get("ending_label")):
            label += "\n(GATE)"
        nodes.append({"id": p["id"], "label": label})
        for c in p.get("choices", []):
            edges.append({"from": p["id"], "to": c["next_page_id"], "label": c.get("text","")[:28]})
    return render(request, "story_graph.html", {"story": story, "nodes_json": json.dumps(nodes), "edges_json": json.dumps(edges)})


@login_required
def play_path(request, play_id: int):
    play = get_object_or_404(Play, id=play_id, user=request.user)
    story = api_get(f"/stories/{play.story_id}")
    pages = api_get(f"/stories/{play.story_id}/pages")
    path_set = set(play.path or [])
    nodes=[]
    edges=[]
    for p in pages:
        nodes.append({"id": p["id"], "label": str(p["id"]), "inPath": (p["id"] in path_set)})
        for c in p.get("choices", []):
            edges.append({"from": p["id"], "to": c["next_page_id"]})
    return render(request, "play_path.html", {
        "story": story,
        "play": play,
        "nodes_json": json.dumps(nodes),
        "edges_json": json.dumps(edges),
        "path_json": json.dumps(play.path or []),
    })
