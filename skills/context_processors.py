from .models import Notification


def navigation(request):
    unread_count = 0
    latest_notification_id = 0
    notification_volume = 0
    notifications_enabled = False
    if request.user.is_authenticated:
        profile = getattr(request.user, "student_profile", None)
        notifications_enabled = profile.notifications_enabled if profile else True
        notification_volume = profile.notification_volume if profile else 45
        notifications = Notification.objects.filter(recipient=request.user)
        unread_count = notifications.filter(is_read=False).count()
        latest_notification_id = notifications.order_by("-pk").values_list("pk", flat=True).first() or 0
    return {
        "unread_count": unread_count,
        "latest_notification_id": latest_notification_id,
        "notifications_enabled": notifications_enabled,
        "notification_volume": notification_volume,
    }
