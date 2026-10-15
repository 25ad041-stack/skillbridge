from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    college = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    interests = models.CharField(max_length=300, blank=True)
    points = models.PositiveIntegerField(default=0)
    notifications_enabled = models.BooleanField(default=True)
    notification_volume = models.PositiveSmallIntegerField(
        default=45, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class LoginHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_history"
    )
    logged_in_at = models.DateTimeField(auto_now_add=True)
    points_claimed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-logged_in_at"]

    def __str__(self):
        return f"{self.user} logged in at {self.logged_in_at:%Y-%m-%d %H:%M}"


class Skill(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Mode(models.TextChoices):
        TEACH = "teach", "I can teach"
        LEARN = "learn", "I want to learn"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=60)
    level = models.CharField(max_length=15, choices=Level.choices, default=Level.BEGINNER)
    description = models.TextField(max_length=1000)
    mode = models.CharField(max_length=8, choices=Mode.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["mode", "category"])]

    def __str__(self):
        return f"{self.name} ({self.get_mode_display()})"


class Course(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=60, db_index=True)
    description = models.TextField(max_length=800)
    icon = models.CharField(max_length=8, default="✦")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class CourseLesson(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    level = models.CharField(max_length=15, choices=Level.choices)
    title = models.CharField(max_length=160)
    explanation = models.TextField(max_length=2000)
    practice = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["level", "order"]
        constraints = [
            models.UniqueConstraint(fields=["course", "level", "order"], name="unique_course_level_lesson_order")
        ]

    def __str__(self):
        return f"{self.course.name}: {self.title}"


class CourseLessonCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_lesson_completions"
    )
    lesson = models.ForeignKey(
        CourseLesson, on_delete=models.CASCADE, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "lesson"], name="unique_user_course_lesson_completion")
        ]

    def __str__(self):
        return f"{self.user}: {self.lesson.title}"


class LearningRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_learning_requests"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_learning_requests"
    )
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="learning_requests")
    message = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "teacher", "skill"], name="unique_learner_teacher_skill"
            ),
            models.CheckConstraint(condition=~Q(learner=models.F("teacher")), name="request_not_self"),
        ]

    def __str__(self):
        return f"{self.learner} wants to learn {self.skill.name} from {self.teacher}"


class LearningSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    learning_request = models.ForeignKey(
        LearningRequest, on_delete=models.CASCADE, related_name="sessions"
    )
    starts_at = models.DateTimeField()
    details = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.starts_at and self.starts_at < timezone.now():
            raise ValidationError({"starts_at": "Choose a future date and time."})
        if self.learning_request_id and self.learning_request.status != LearningRequest.Status.ACCEPTED:
            raise ValidationError("A session can only be created for an accepted learning request.")

    def __str__(self):
        return f"{self.learning_request.skill.name} on {self.starts_at:%Y-%m-%d %H:%M}"


class LearningProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_progress"
    )
    skill_name = models.CharField(max_length=100)
    current_level = models.CharField(max_length=15, choices=Skill.Level.choices)
    target_level = models.CharField(max_length=15, choices=Skill.Level.choices)
    percent = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["skill_name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "skill_name"], name="unique_user_progress_skill")
        ]

    def __str__(self):
        return f"{self.user}: {self.skill_name} ({self.percent}%)"


class LearningMilestone(models.Model):
    class Stage(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    progress = models.ForeignKey(
        LearningProgress, on_delete=models.CASCADE, related_name="milestones"
    )
    title = models.CharField(max_length=160)
    description = models.CharField(max_length=500)
    stage = models.CharField(max_length=15, choices=Stage.choices)
    order = models.PositiveSmallIntegerField(default=1)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["progress", "order"], name="unique_progress_milestone_order")
        ]

    def __str__(self):
        return self.title


class Badge(models.Model):
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=250)
    points_required = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=8, default="★")

    def __str__(self):
        return self.name


class StudentBadge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="earned_badges"
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="earners")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-earned_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "badge"], name="unique_student_badge")
        ]

    def __str__(self):
        return f"{self.user}: {self.badge.name}"


class RewardEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reward_events"
    )
    source_type = models.CharField(max_length=30)
    source_id = models.PositiveBigIntegerField()
    points = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source_type", "source_id"], name="unique_reward_per_activity"
            )
        ]


class CashbackReward(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cashback_rewards"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="cashback_rewards")
    level = models.CharField(max_length=15, choices=CourseLesson.Level.choices)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course", "level"], name="unique_user_course_level_cashback"
            )
        ]

    def __str__(self):
        return f"{self.user}: ₹{self.amount} for {self.course.name} ({self.level})"


class FriendRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_friend_requests"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver"], name="unique_friend_request_pair"
            ),
            models.CheckConstraint(condition=~Q(sender=models.F("receiver")), name="friend_request_not_self"),
        ]

    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"


class Rating(models.Model):
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name="ratings")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="written_ratings"
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_ratings"
    )
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["session", "reviewer"], name="one_rating_per_session_reviewer"),
            models.CheckConstraint(condition=~Q(reviewer=models.F("reviewee")), name="rating_not_self"),
            models.CheckConstraint(condition=Q(score__gte=1) & Q(score__lte=5), name="rating_score_1_to_5"),
        ]

    def __str__(self):
        return f"{self.score}/5 for {self.reviewee}"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=250)
    url = models.CharField(max_length=250, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
