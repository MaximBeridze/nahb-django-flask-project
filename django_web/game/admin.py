from django.contrib import admin
from .models import Play

@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ("id", "story_id", "ending_page_id", "created_at")
    list_filter = ("story_id", "ending_page_id")
    ordering = ("-created_at",)
