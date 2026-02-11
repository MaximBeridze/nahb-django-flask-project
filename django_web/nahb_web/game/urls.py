from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.story_list, name="story_list"),
    path("stories/<int:story_id>/", views.story_detail, name="story_detail"),
    path("stories/<int:story_id>/graph/", views.story_graph, name="story_graph"),

    # auth
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # play
    path("play/<int:story_id>/start/", views.play_start, name="play_start"),
    path("play/<int:story_id>/resume/", views.play_resume, name="play_resume"),
    path("play/<int:story_id>/page/<int:page_id>/", views.play_page, name="play_page"),
    path("plays/<int:play_id>/path/", views.play_path, name="play_path"),

    # community
    path("stories/<int:story_id>/rate/", views.rate_story, name="rate_story"),
    path("stories/<int:story_id>/report/", views.report_story, name="report_story"),
    path("me/history/", views.my_history, name="my_history"),

    path("stats/", views.stats, name="stats"),

    # Author tools
    path("author/", views.author_dashboard, name="author_dashboard"),
    path("author/stories/new/", views.story_create, name="story_create"),
    path("author/stories/<int:story_id>/edit/", views.story_edit, name="story_edit"),
    path("author/stories/<int:story_id>/delete/", views.story_delete, name="story_delete"),
    path("author/stories/<int:story_id>/pages/new/", views.page_create, name="page_create"),
    path("author/pages/<int:page_id>/edit/", views.page_edit, name="page_edit"),
    path("author/pages/<int:page_id>/delete/", views.page_delete, name="page_delete"),
    path("author/pages/<int:page_id>/choices/new/", views.choice_create, name="choice_create"),
    path("author/choices/<int:choice_id>/delete/<int:story_id>/", views.choice_delete, name="choice_delete"),

    # moderation
    path("moderation/", views.moderation, name="moderation"),
    path("moderation/stories/<int:story_id>/status/", views.set_story_status, name="set_story_status"),
    path("moderation/reports/<int:report_id>/resolve/", views.resolve_report, name="resolve_report"),
]
