from django.db import models

class Play(models.Model):
    story_id = models.IntegerField()
    ending_page_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Play(story={self.story_id}, ending={self.ending_page_id})"
