from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

class StoryOwnership(models.Model):
    story_id = models.IntegerField(unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_stories")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StoryOwnership(story={self.story_id}, owner={self.owner_id})"

class Play(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plays")
    story_id = models.IntegerField()
    ending_page_id = models.IntegerField()
    ending_label = models.CharField(max_length=120, blank=True, default="")
    score = models.IntegerField(default=0)
    path = models.JSONField(default=list)  # list of page_ids visited in order
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Play(user={self.user_id}, story={self.story_id}, ending={self.ending_label or self.ending_page_id})"

class PlaySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="play_sessions")
    story_id = models.IntegerField()
    current_page_id = models.IntegerField()
    score = models.IntegerField(default=0)
    path = models.JSONField(default=list)
    last_roll = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class Rating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    story_id = models.IntegerField(db_index=True)
    stars = models.IntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "story_id")

class Report(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    story_id = models.IntegerField(db_index=True)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
