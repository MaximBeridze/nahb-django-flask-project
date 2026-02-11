from django.apps import AppConfig

class GameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nahb_web.game"

    def ready(self):
        from django.db.models.signals import post_migrate
        from django.dispatch import receiver

        @receiver(post_migrate, sender=self)
        def ensure_groups(sender, **kwargs):
            try:
                from django.contrib.auth.models import Group
                Group.objects.get_or_create(name="Authors")
            except Exception:
                pass
