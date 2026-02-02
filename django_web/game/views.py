from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count
from .models import Play
from . import services


def story_list(request: HttpRequest) -> HttpResponse:
    stories = []
    error = None
    try:
        stories = services.get_published_stories()
    except Exception as e:
        error = str(e)
    return render(request, "game/story_list.html", {"stories": stories, "error": error})


def story_detail(request: HttpRequest, story_id: int) -> HttpResponse:
    story = None
    error = None
    try:
        story = services.get_story(story_id)
    except Exception as e:
        error = str(e)
    return render(request, "game/story_detail.html", {"story": story, "error": error})


def play_start(request: HttpRequest, story_id: int) -> HttpResponse:
    try:
        payload = services.get_start(story_id)
        page_id = payload["page"]["id"]
        return redirect("play_page", story_id=story_id, page_id=page_id)
    except Exception as e:
        return render(request, "game/error.html", {"message": f"Cannot start story: {e}"})


def play_page(request: HttpRequest, story_id: int, page_id: int) -> HttpResponse:
    # Fetch page + choices
    try:
        payload = services.get_page(page_id)
    except Exception as e:
        return render(request, "game/error.html", {"message": f"Cannot load page: {e}"})

    page = payload["page"]
    choices = payload.get("choices", [])

    # If ending -> record play (anonymous Level 10)
    if page.get("is_ending"):
        Play.objects.create(story_id=story_id, ending_page_id=page_id)
        return render(request, "game/ending.html", {"story_id": story_id, "page": page})

    return render(request, "game/play.html", {"story_id": story_id, "page": page, "choices": choices})


def stats(request: HttpRequest) -> HttpResponse:
    # Plays per story
    per_story = list(
        Play.objects.values("story_id")
        .annotate(total=Count("id"))
        .order_by("story_id")
    )

    # Endings reached
    endings = list(
        Play.objects.values("story_id", "ending_page_id")
        .annotate(total=Count("id"))
        .order_by("story_id", "ending_page_id")
    )

    # Try to enrich story titles from Flask (best-effort)
    story_titles = {}
    try:
        for s in services.get_published_stories():
            story_titles[s["id"]] = s["title"]
    except Exception:
        pass

    for row in per_story:
        row["title"] = story_titles.get(row["story_id"], f"Story #{row['story_id']}")
    for row in endings:
        row["title"] = story_titles.get(row["story_id"], f"Story #{row['story_id']}")

    return render(request, "game/stats.html", {"per_story": per_story, "endings": endings})
