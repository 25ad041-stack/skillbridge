from django.db import transaction

from .models import (
    Badge,
    CashbackReward,
    CourseLesson,
    CourseLessonCompletion,
    Notification,
    RewardEvent,
    StudentBadge,
    StudentProfile,
)


COURSE_LEVEL_CASHBACK = {
    CourseLesson.Level.BEGINNER: 500,
    CourseLesson.Level.INTERMEDIATE: 1000,
    CourseLesson.Level.ADVANCED: 2000,
}


def notify(recipient, message, url=""):
    notifications_enabled = StudentProfile.objects.filter(user=recipient).values_list(
        "notifications_enabled", flat=True
    ).first()
    if notifications_enabled is False:
        return None
    return Notification.objects.create(recipient=recipient, message=message, url=url)


@transaction.atomic
def award_points(user, source_type, source_id, points):
    event, created = RewardEvent.objects.get_or_create(
        user=user,
        source_type=source_type,
        source_id=source_id,
        defaults={"points": points},
    )
    if created:
        profile, _ = StudentProfile.objects.get_or_create(user=user)
        profile.points += points
        profile.save(update_fields=["points", "updated_at"])
        for badge in Badge.objects.filter(points_required__lte=profile.points):
            StudentBadge.objects.get_or_create(user=user, badge=badge)
    return created


@transaction.atomic
def create_cashback_reward_if_level_complete(user, course, level):
    lesson_count = CourseLesson.objects.filter(course=course, level=level).count()
    if not lesson_count:
        return None

    completed_count = CourseLessonCompletion.objects.filter(
        user=user, lesson__course=course, lesson__level=level
    ).count()
    if completed_count != lesson_count:
        return None

    return CashbackReward.objects.get_or_create(
        user=user,
        course=course,
        level=level,
        defaults={"amount": COURSE_LEVEL_CASHBACK[level]},
    )


def get_recommendations(user, limit=8):
    """Score teach listings against the user's learn listings and stated interests."""
    from .models import Skill

    goals = list(Skill.objects.filter(owner=user, mode=Skill.Mode.LEARN))
    profile = getattr(user, "student_profile", None)
    interests = set((profile.interests if profile else "").lower().replace(",", " ").split())
    results = []
    for offered in Skill.objects.filter(mode=Skill.Mode.TEACH).exclude(owner=user).select_related("owner"):
        best_score = 0
        best_reasons = []
        for goal in goals:
            score = 0
            reasons = []
            if goal.name.casefold() == offered.name.casefold():
                score += 55
                reasons.append("exact skill goal")
            elif goal.category.casefold() == offered.category.casefold():
                score += 25
                reasons.append("same skill category")
            if goal.level == offered.level:
                score += 15
                reasons.append("matches your selected level")
            if goal.name.casefold() == offered.name.casefold() and offered.level in {
                Skill.Level.INTERMEDIATE,
                Skill.Level.ADVANCED,
            }:
                score += 10
                reasons.append("teacher has experience beyond beginner level")
            if score > best_score:
                best_score, best_reasons = score, reasons
        interest_words = set(offered.name.lower().replace(",", " ").split())
        overlap = interests & interest_words
        if overlap:
            best_score += 10
            best_reasons.append("matches your interests: " + ", ".join(sorted(overlap)))
        if best_score:
            results.append(
                {
                    "skill": offered,
                    "student": offered.owner,
                    "score": min(best_score, 100),
                    "reasons": best_reasons,
                }
            )
    results.sort(key=lambda item: (-item["score"], item["skill"].name.casefold()))
    return results[:limit]
