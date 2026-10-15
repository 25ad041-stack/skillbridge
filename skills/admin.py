from django.contrib import admin

from .models import (
    Badge,
    CashbackReward,
    Course,
    CourseLesson,
    CourseLessonCompletion,
    FriendRequest,
    LearningMilestone,
    LearningProgress,
    LearningRequest,
    LearningSession,
    Notification,
    Rating,
    RewardEvent,
    Skill,
    StudentBadge,
    StudentProfile,
)

admin.site.register(
    [
        StudentProfile,
        Skill,
        Course,
        CourseLesson,
        CourseLessonCompletion,
        FriendRequest,
        LearningRequest,
        LearningSession,
        LearningProgress,
        LearningMilestone,
        Badge,
        CashbackReward,
        StudentBadge,
        RewardEvent,
        Rating,
        Notification,
    ]
)
