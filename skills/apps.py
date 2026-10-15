from importlib import import_module

from django.apps import AppConfig


class SkillsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "skills"

    def ready(self):
        import_module("skills.signals")
