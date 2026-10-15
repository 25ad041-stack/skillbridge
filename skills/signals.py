from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import LoginHistory


@receiver(user_logged_in, dispatch_uid="skills.record_login_history")
def record_login_history(user, **_):
    LoginHistory.objects.create(user=user)