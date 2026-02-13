from django.contrib import admin
from .models import StoryOwnership, Play, PlaySession, Rating, Report

@admin.register(StoryOwnership)
class StoryOwnershipAdmin(admin.ModelAdmin):
    list_display = ("story_id", "owner", "created_at")
    search_fields = ("story_id", "owner__username")

@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ("user", "story_id", "ending_label", "score", "created_at")
    list_filter = ("story_id", "ending_label")
    search_fields = ("user__username",)

@admin.register(PlaySession)
class PlaySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "story_id", "current_page_id", "score", "updated_at")

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("user", "story_id", "stars", "created_at")
    list_filter = ("stars",)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("user", "story_id", "resolved", "created_at")
    list_filter = ("resolved",)
