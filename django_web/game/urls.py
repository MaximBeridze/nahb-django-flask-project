from django.urls import path
from . import views

urlpatterns = [
    path("", views.story_list, name="story_list"),
    path("stories/<int:story_id>/", views.story_detail, name="story_detail"),
    path("play/<int:story_id>/", views.play_start, name="play_start"),
    path("play/<int:story_id>/page/<int:page_id>/", views.play_page, name="play_page"),
    path("stats/", views.stats, name="stats"),
]
