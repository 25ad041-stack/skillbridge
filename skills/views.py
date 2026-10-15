from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    LearningRequestForm,
    NotificationPreferencesForm,
    ProfileForm,
    ProgressForm,
    RatingForm,
    RegistrationForm,
    SessionForm,
    SkillForm,
)
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
    LoginHistory,
    Notification,
    Rating,
    RewardEvent,
    Skill,
    StudentBadge,
    StudentProfile,
)
from .services import (
    COURSE_LEVEL_CASHBACK,
    award_points,
    create_cashback_reward_if_level_complete,
    get_recommendations,
    notify,
)


def home(request):
    return render(request, "skills/home.html", {"skill_count": Skill.objects.count()})


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        StudentProfile.objects.create(user=user)
        login(request, user)
        messages.success(request, "Welcome to SkillBridge AI. Your account is ready.")
        return redirect("dashboard")
    return render(request, "skills/form_page.html", {"form": form, "title": "Create your account"})


@login_required
def dashboard(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    sessions = LearningSession.objects.filter(
        Q(learning_request__learner=request.user) | Q(learning_request__teacher=request.user)
    ).select_related("learning_request__skill", "learning_request__learner", "learning_request__teacher")
    context = {
        "profile": profile,
        "skill_count": Skill.objects.filter(owner=request.user).count(),
        "request_count": LearningRequest.objects.filter(
            Q(learner=request.user) | Q(teacher=request.user)
        ).count(),
        "upcoming_count": sessions.filter(
            status=LearningSession.Status.SCHEDULED, starts_at__gte=timezone.now()
        ).count(),
        "upcoming": sessions.filter(status=LearningSession.Status.SCHEDULED, starts_at__gte=timezone.now())[:5],
        "completed_count": sessions.filter(status=LearningSession.Status.COMPLETED).count(),
        "progress_items": LearningProgress.objects.filter(user=request.user)[:4],
        "badges": StudentBadge.objects.filter(user=request.user).select_related("badge")[:4],
        "recommendations": get_recommendations(request.user, 3),
        "notifications": Notification.objects.filter(recipient=request.user)[:4],
        "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
    }
    return render(request, "skills/dashboard.html", context)


@login_required
def rewards(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    earned_badges = StudentBadge.objects.filter(user=request.user).select_related("badge")
    context = {
        "profile": profile,
        "earned_badges": earned_badges,
        "available_badges": Badge.objects.exclude(
            earners__user=request.user
        ).order_by("points_required", "name"),
        "reward_events": RewardEvent.objects.filter(user=request.user).order_by("-created_at")[:10],
        "claimable_logins": LoginHistory.objects.filter(
            user=request.user, points_claimed=False
        ),
        "cashback_rewards": CashbackReward.objects.filter(user=request.user).select_related("course"),
        "cashback_balance": sum(
            reward.amount
            for reward in CashbackReward.objects.filter(
                user=request.user, claimed_at__isnull=False
            ).only("amount")
        ),
        "cashback_tiers": COURSE_LEVEL_CASHBACK,
    }
    return render(request, "skills/rewards.html", context)


@login_required
def history(request):
    completed_sessions = LearningSession.objects.filter(
        Q(learning_request__learner=request.user) | Q(learning_request__teacher=request.user),
        status=LearningSession.Status.COMPLETED,
    ).select_related("learning_request__skill").order_by("-starts_at")
    completed_milestones = LearningMilestone.objects.filter(
        progress__user=request.user, completed=True
    ).select_related("progress").order_by("-completed_at")
    completed_lessons = CourseLessonCompletion.objects.filter(
        user=request.user
    ).select_related("lesson__course").order_by("-completed_at")
    reward_events = RewardEvent.objects.filter(user=request.user).order_by("-created_at")
    cashback_rewards = CashbackReward.objects.filter(user=request.user).select_related(
        "course"
    )
    context = {
        "completed_sessions": completed_sessions,
        "completed_milestones": completed_milestones,
        "completed_lessons": completed_lessons,
        "reward_events": reward_events,
        "cashback_rewards": cashback_rewards,
        "has_history": any(
            queryset.exists()
            for queryset in (
                completed_sessions,
                completed_milestones,
                completed_lessons,
                reward_events,
                cashback_rewards,
            )
        ),
    }
    return render(request, "skills/history.html", context)


@login_required
@require_POST
def claim_login_points(request, login_id):
    with transaction.atomic():
        login_reward = get_object_or_404(
            LoginHistory.objects.select_for_update(), pk=login_id, user=request.user
        )
        if login_reward.points_claimed:
            messages.info(request, "You already claimed points for this login.")
        else:
            award_points(request.user, "login", login_reward.pk, 5)
            login_reward.points_claimed = True
            login_reward.save(update_fields=["points_claimed"])
            messages.success(request, "5 login points added to your rewards.")
    return redirect("rewards")


@login_required
@require_POST
def claim_cashback(request, cashback_id):
    with transaction.atomic():
        cashback = get_object_or_404(
            CashbackReward.objects.select_for_update(),
            pk=cashback_id,
            user=request.user,
        )
        if cashback.claimed_at:
            messages.info(request, "This course cashback is already in your app balance.")
        else:
            cashback.claimed_at = timezone.now()
            cashback.save(update_fields=["claimed_at"])
            messages.success(
                request,
                f"₹{cashback.amount} cashback was added to your in-app balance.",
            )
    return redirect("rewards")


@login_required
def profile(request, username=None):
    student = get_object_or_404(User, username=username) if username else request.user
    student_profile, _ = StudentProfile.objects.get_or_create(user=student)
    ratings = Rating.objects.filter(reviewee=student).select_related("reviewer")
    is_own_profile = student.pk == request.user.pk
    context = {
        "student": student,
        "profile": student_profile,
        "skills": Skill.objects.filter(owner=student),
        "badges": StudentBadge.objects.filter(user=student).select_related("badge"),
        "rating_average": ratings.aggregate(value=Avg("score"))["value"],
        "rating_count": ratings.count(),
        "ratings": ratings[:5],
        "is_own_profile": is_own_profile,
    }
    if not is_own_profile:
        context["friend_request"] = FriendRequest.objects.filter(
            Q(sender=request.user, receiver=student) | Q(sender=student, receiver=request.user)
        ).first()
    if is_own_profile:
        context["history_sessions"] = (
            LearningSession.objects.filter(
                Q(learning_request__learner=student) | Q(learning_request__teacher=student),
                status=LearningSession.Status.COMPLETED,
            )
            .select_related("learning_request__skill")
            .order_by("-starts_at")[:10]
        )
        context["history_milestones"] = (
            LearningMilestone.objects.filter(
                progress__user=student, completed=True
            )
            .select_related("progress")
            .order_by("-completed_at")[:10]
        )
        context["history_course_lessons"] = (
            CourseLessonCompletion.objects.filter(user=student)
            .select_related("lesson__course")
            .order_by("-completed_at")[:10]
        )
    return render(request, "skills/profile.html", context)


@login_required
def friends(request):
    query = request.GET.get("q", "").strip()
    incoming_requests = FriendRequest.objects.filter(
        receiver=request.user, status=FriendRequest.Status.PENDING
    ).select_related("sender")
    outgoing_requests = FriendRequest.objects.filter(
        sender=request.user, status=FriendRequest.Status.PENDING
    ).select_related("receiver")
    accepted_requests = FriendRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status=FriendRequest.Status.ACCEPTED,
    ).select_related("sender", "receiver")
    friend_users = [
        item.receiver if item.sender_id == request.user.id else item.sender
        for item in accepted_requests
    ]
    students = User.objects.exclude(pk=request.user.pk).exclude(
        Q(sent_friend_requests__receiver=request.user)
        | Q(received_friend_requests__sender=request.user)
    )
    if query:
        students = students.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return render(
        request,
        "skills/friends.html",
        {
            "incoming_requests": incoming_requests,
            "outgoing_requests": outgoing_requests,
            "friend_users": friend_users,
            "students": students.order_by("first_name", "username")[:12],
            "student_query": query,
        },
    )


@login_required
@require_POST
def friend_request_create(request, username):
    recipient = get_object_or_404(User, username=username)
    if recipient.pk == request.user.pk:
        raise PermissionDenied
    existing = FriendRequest.objects.filter(
        Q(sender=request.user, receiver=recipient) | Q(sender=recipient, receiver=request.user)
    ).first()
    if existing and existing.status == FriendRequest.Status.ACCEPTED:
        messages.info(request, "You are already friends.")
    elif existing and existing.status == FriendRequest.Status.PENDING:
        messages.info(request, "A friend request is already waiting for a response.")
    elif existing:
        existing.sender = request.user
        existing.receiver = recipient
        existing.status = FriendRequest.Status.PENDING
        existing.save(update_fields=["sender", "receiver", "status", "created_at", "updated_at"])
        notify(recipient, "You have a new friend request.", "/friends/")
        messages.success(request, "Friend request sent.")
    else:
        FriendRequest.objects.create(sender=request.user, receiver=recipient)
        notify(recipient, "You have a new friend request.", "/friends/")
        messages.success(request, "Friend request sent.")
    return redirect("student_profile", username=recipient.username)


@login_required
@require_POST
def friend_request_update(request, request_id, action):
    if action not in {"accept", "decline"}:
        raise PermissionDenied
    friend_request = get_object_or_404(
        FriendRequest, pk=request_id, receiver=request.user, status=FriendRequest.Status.PENDING
    )
    if action == "accept":
        friend_request.status = FriendRequest.Status.ACCEPTED
        message = "Friend request accepted."
        notify(friend_request.sender, "Your friend request was accepted.", "/friends/")
    else:
        friend_request.status = FriendRequest.Status.DECLINED
        message = "Friend request declined."
    friend_request.save(update_fields=["status", "updated_at"])
    messages.success(request, message)
    return redirect("friends")


@login_required
def profile_edit(request):
    profile_obj, _ = StudentProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile_obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")
    return render(request, "skills/form_page.html", {"form": form, "title": "Edit your profile"})


@login_required
def account_settings(request):
    profile_obj, _ = StudentProfile.objects.get_or_create(user=request.user)
    form = NotificationPreferencesForm(request.POST or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your notification preferences have been saved.")
        return redirect("account_settings")
    return render(
        request,
        "skills/account_settings.html",
        {"profile": profile_obj, "notification_form": form},
    )


@login_required
def manage_account(request):
    profile_obj, _ = StudentProfile.objects.get_or_create(user=request.user)
    return render(request, "skills/manage_account.html", {"profile": profile_obj})


@login_required
def skill_list(request):
    skills = Skill.objects.select_related("owner", "owner__student_profile").exclude(owner=request.user)
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    level = request.GET.get("level", "").strip()
    mode = request.GET.get("mode", "").strip()
    if query:
        skills = skills.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        skills = skills.filter(category__iexact=category)
    if level in Skill.Level.values:
        skills = skills.filter(level=level)
    if mode in Skill.Mode.values:
        skills = skills.filter(mode=mode)
    categories = sorted(
        set(Skill.objects.values_list("category", flat=True).distinct())
        | set(Course.objects.values_list("category", flat=True).distinct()),
        key=str.casefold,
    )
    courses = Course.objects.annotate(
        lesson_count=Count("lessons", distinct=True),
        completed_count=Count(
            "lessons__completions",
            filter=Q(lessons__completions__user=request.user),
            distinct=True,
        ),
    )
    if query:
        courses = courses.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        courses = courses.filter(category__iexact=category)
    selected_courses = list(courses)
    for course in selected_courses:
        course.progress_percent = (
            round(course.completed_count * 100 / course.lesson_count)
            if course.lesson_count
            else 0
        )
    return render(
        request,
        "skills/skill_list.html",
        {
            "skills": skills,
            "courses": selected_courses,
            "course_count": len(selected_courses),
            "query": query,
            "selected_category": category,
            "selected_level": level,
            "selected_mode": mode,
            "categories": categories,
            "levels": Skill.Level.choices,
            "modes": Skill.Mode.choices,
        },
    )


@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    level = request.GET.get("level", CourseLesson.Level.BEGINNER)
    if level not in CourseLesson.Level.values:
        level = CourseLesson.Level.BEGINNER
    lessons = list(course.lessons.filter(level=level))
    completed_ids = set(
        CourseLessonCompletion.objects.filter(
            user=request.user, lesson__course=course, lesson__level=level
        ).values_list("lesson_id", flat=True)
    )
    for lesson in lessons:
        lesson.is_completed = lesson.pk in completed_ids
    return render(
        request,
        "skills/course_detail.html",
        {
            "course": course,
            "lessons": lessons,
            "selected_level": level,
            "levels": CourseLesson.Level.choices,
            "completed_count": len(completed_ids),
        },
    )


@login_required
@require_POST
def course_lesson_toggle(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug)
    lesson = get_object_or_404(CourseLesson, pk=lesson_id, course=course)
    completion, created = CourseLessonCompletion.objects.get_or_create(
        user=request.user, lesson=lesson
    )
    if not created:
        completion.delete()
        messages.success(request, "Lesson marked as not completed.")
    else:
        messages.success(request, "Lesson completed. Your course progress is saved.")
        reward_result = create_cashback_reward_if_level_complete(
            request.user, course, lesson.level
        )
        if reward_result and reward_result[1]:
            cashback = reward_result[0]
            messages.success(
                request,
                f"{lesson.get_level_display()} level complete! Claim your ₹{cashback.amount} cashback on Rewards.",
            )
    level = request.POST.get("level", CourseLesson.Level.BEGINNER)
    if level not in CourseLesson.Level.values:
        level = CourseLesson.Level.BEGINNER
    return redirect(f"{reverse('course_detail', args=[course.slug])}?level={level}")


@login_required
def my_skills(request):
    return render(request, "skills/my_skills.html", {"skills": Skill.objects.filter(owner=request.user)})


@login_required
def skill_create(request):
    form = SkillForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        skill = form.save(commit=False)
        skill.owner = request.user
        skill.save()
        messages.success(request, "Your skill listing has been added.")
        return redirect("my_skills")
    return render(request, "skills/form_page.html", {"form": form, "title": "Add a skill"})


@login_required
def skill_edit(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if skill.owner_id != request.user.id:
        raise PermissionDenied
    form = SkillForm(request.POST or None, instance=skill)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your skill listing has been updated.")
        return redirect("my_skills")
    return render(request, "skills/form_page.html", {"form": form, "title": "Edit skill"})


@login_required
@require_POST
def skill_delete(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if skill.owner_id != request.user.id:
        raise PermissionDenied
    skill.delete()
    messages.success(request, "Your skill listing has been deleted.")
    return redirect("my_skills")


@login_required
def recommendations(request):
    return render(
        request,
        "skills/recommendations.html",
        {"recommendations": get_recommendations(request.user), "my_goals": Skill.objects.filter(owner=request.user, mode=Skill.Mode.LEARN)},
    )


@login_required
def request_create(request, skill_id):
    skill = get_object_or_404(Skill, pk=skill_id, mode=Skill.Mode.TEACH)
    if skill.owner_id == request.user.id:
        raise PermissionDenied
    form = LearningRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            learning_request = form.save(commit=False)
            learning_request.learner = request.user
            learning_request.teacher = skill.owner
            learning_request.skill = skill
            learning_request.save()
        except IntegrityError:
            messages.error(request, "You already sent a request for this skill to this student.")
        else:
            notify(skill.owner, f"{request.user.get_full_name() or request.user.username} wants to learn {skill.name}.", "/requests/")
            messages.success(request, "Your learning request has been sent.")
        return redirect("requests")
    return render(
        request, "skills/form_page.html", {"form": form, "title": f"Request to learn {skill.name}", "subtitle": f"From {skill.owner.get_full_name() or skill.owner.username}"}
    )


@login_required
def requests_list(request):
    received = LearningRequest.objects.filter(teacher=request.user).select_related("learner", "skill")
    sent = LearningRequest.objects.filter(learner=request.user).select_related("teacher", "skill")
    box = request.GET.get("box", "incoming")
    if box not in {"incoming", "sent"}:
        box = "incoming"
    return render(
        request,
        "skills/requests.html",
        {
            "received": received,
            "sent": sent,
            "active_box": box,
            "incoming_count": received.count(),
            "sent_count": sent.count(),
        },
    )


@login_required
@require_POST
def request_update(request, pk, action):
    learning_request = get_object_or_404(LearningRequest, pk=pk)
    if learning_request.teacher_id != request.user.id:
        raise PermissionDenied
    if learning_request.status != LearningRequest.Status.PENDING or action not in {"accept", "reject"}:
        messages.error(request, "This request can no longer be changed.")
        return redirect("requests")
    learning_request.status = (
        LearningRequest.Status.ACCEPTED if action == "accept" else LearningRequest.Status.REJECTED
    )
    learning_request.save(update_fields=["status", "updated_at"])
    notify(learning_request.learner, f"Your request to learn {learning_request.skill.name} was {learning_request.status}.", "/requests/")
    messages.success(request, f"Request {learning_request.status}.")
    return redirect("requests")


@login_required
def sessions_list(request):
    sessions = LearningSession.objects.filter(
        Q(learning_request__learner=request.user) | Q(learning_request__teacher=request.user)
    ).select_related("learning_request__skill", "learning_request__learner", "learning_request__teacher")
    return render(request, "skills/sessions.html", {"sessions": sessions})


@login_required
def session_create(request, request_id):
    learning_request = get_object_or_404(
        LearningRequest, pk=request_id, status=LearningRequest.Status.ACCEPTED
    )
    if request.user.id not in {learning_request.learner_id, learning_request.teacher_id}:
        raise PermissionDenied
    form = SessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.learning_request = learning_request
        try:
            session.full_clean()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            session.save()
            other = learning_request.teacher if request.user == learning_request.learner else learning_request.learner
            notify(other, f"A session for {learning_request.skill.name} was scheduled.", "/sessions/")
            messages.success(request, "Your learning session has been scheduled.")
            return redirect("sessions")
    return render(request, "skills/form_page.html", {"form": form, "title": "Schedule a learning session"})


@login_required
@require_POST
def session_update(request, pk, status):
    session = get_object_or_404(
        LearningSession.objects.select_related("learning_request"), pk=pk
    )
    participants = {session.learning_request.learner_id, session.learning_request.teacher_id}
    if request.user.id not in participants:
        raise PermissionDenied
    if status not in {LearningSession.Status.COMPLETED, LearningSession.Status.CANCELLED}:
        raise PermissionDenied
    if session.status != LearningSession.Status.SCHEDULED:
        messages.error(request, "Only scheduled sessions can be updated.")
        return redirect("sessions")
    session.status = status
    session.save(update_fields=["status", "updated_at"])
    if status == LearningSession.Status.COMPLETED:
        learning_request = session.learning_request
        learning_request.status = LearningRequest.Status.COMPLETED
        learning_request.save(update_fields=["status", "updated_at"])
        award_points(learning_request.learner, "session", session.pk, 10)
        award_points(learning_request.teacher, "session", session.pk, 10)
        notify(learning_request.learner, f"Session completed. You earned 10 points for {learning_request.skill.name}.", "/progress/")
        notify(learning_request.teacher, f"Session completed. You earned 10 points for teaching {learning_request.skill.name}.", "/progress/")
    else:
        other_id = session.learning_request.teacher_id if request.user.id == session.learning_request.learner_id else session.learning_request.learner_id
        notify(User.objects.get(pk=other_id), f"A session for {session.learning_request.skill.name} was cancelled.", "/sessions/")
    messages.success(request, f"Session marked {status}.")
    return redirect("sessions")


@login_required
def progress_list(request):
    form = ProgressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        progress, created = LearningProgress.objects.get_or_create(
            user=request.user,
            skill_name=form.cleaned_data["skill_name"],
            defaults={
                "current_level": form.cleaned_data["current_level"],
                "target_level": form.cleaned_data["target_level"],
                "percent": form.cleaned_data["percent"],
            },
        )
        if not created:
            progress.current_level = form.cleaned_data["current_level"]
            progress.target_level = form.cleaned_data["target_level"]
            progress.percent = form.cleaned_data["percent"]
            progress.save()
        messages.success(request, "Learning progress saved.")
        return redirect("progress")
    return render(
        request,
        "skills/progress.html",
        {
            "form": form,
            "progress_items": LearningProgress.objects.filter(user=request.user).prefetch_related("milestones"),
            "levels": Skill.Level.choices,
        },
    )


@login_required
@require_POST
def progress_update(request, pk):
    progress = get_object_or_404(LearningProgress, pk=pk, user=request.user)
    form = ProgressForm(request.POST)
    if form.is_valid():
        progress.current_level = form.cleaned_data["current_level"]
        progress.target_level = form.cleaned_data["target_level"]
        progress.percent = form.cleaned_data["percent"]
        progress.save()
        messages.success(request, "Your progress has been updated.")
    else:
        messages.error(request, "Please enter a valid progress percentage and levels.")
    return redirect("progress")


@login_required
def roadmap(request):
    progress_items = LearningProgress.objects.filter(user=request.user).prefetch_related("milestones")
    for progress in progress_items:
        if not progress.milestones.exists():
            _create_milestones(progress)
            progress._prefetched_objects_cache.pop("milestones", None)
    return render(request, "skills/roadmap.html", {"progress_items": progress_items})


def _create_milestones(progress):
    name = progress.skill_name
    definitions = [
        ("beginner", f"Learn {name} fundamentals", f"Study the basic concepts and vocabulary of {name}."),
        ("beginner", f"Practice basic {name}", f"Complete a small guided exercise using {name}."),
        ("intermediate", f"Build a {name} mini-project", f"Apply core {name} techniques in a small project."),
        ("intermediate", f"Review and improve your {name} project", f"Test your work and use feedback to improve it."),
        ("advanced", f"Create an independent {name} project", f"Plan and complete a larger project using {name}."),
        ("advanced", f"Share your {name} knowledge", f"Explain what you learned or help another student."),
    ]
    LearningMilestone.objects.bulk_create(
        [
            LearningMilestone(progress=progress, title=title, description=description, stage=stage, order=index)
            for index, (stage, title, description) in enumerate(definitions, start=1)
        ]
    )


@login_required
@require_POST
def milestone_toggle(request, pk):
    milestone = get_object_or_404(LearningMilestone, pk=pk, progress__user=request.user)
    milestone.completed = not milestone.completed
    milestone.completed_at = timezone.now() if milestone.completed else None
    milestone.save(update_fields=["completed", "completed_at"])
    total = milestone.progress.milestones.count()
    completed = milestone.progress.milestones.filter(completed=True).count()
    milestone.progress.percent = round(completed * 100 / total) if total else 0
    milestone.progress.save(update_fields=["percent", "updated_at"])
    if milestone.completed:
        award_points(request.user, "milestone", milestone.pk, 5)
        messages.success(request, "Milestone completed. You earned 5 points.")
    else:
        messages.success(request, "Milestone marked incomplete.")
    return redirect("roadmap")


@login_required
def ratings(request):
    sessions = LearningSession.objects.filter(
        status=LearningSession.Status.COMPLETED
    ).filter(Q(learning_request__learner=request.user) | Q(learning_request__teacher=request.user)).select_related(
        "learning_request__skill", "learning_request__learner", "learning_request__teacher"
    )
    ratings_by_session = {
        rating.session_id: rating
        for rating in Rating.objects.filter(reviewer=request.user, session__in=sessions)
    }
    for session in sessions:
        session.existing_rating = ratings_by_session.get(session.pk)
        session.partner = (
            session.learning_request.teacher
            if session.learning_request.learner_id == request.user.id
            else session.learning_request.learner
        )
    return render(request, "skills/ratings.html", {"sessions": sessions, "form": RatingForm()})


@login_required
@require_POST
def rating_create(request, session_id):
    session = get_object_or_404(LearningSession, pk=session_id, status=LearningSession.Status.COMPLETED)
    learning_request = session.learning_request
    participants = {learning_request.learner_id, learning_request.teacher_id}
    if request.user.id not in participants:
        raise PermissionDenied
    reviewee = learning_request.teacher if request.user == learning_request.learner else learning_request.learner
    form = RatingForm(request.POST)
    if form.is_valid():
        try:
            Rating.objects.create(
                session=session,
                reviewer=request.user,
                reviewee=reviewee,
                score=form.cleaned_data["score"],
                feedback=form.cleaned_data["feedback"],
            )
        except IntegrityError:
            messages.error(request, "You have already rated this session.")
        else:
            notify(reviewee, f"{request.user.get_full_name() or request.user.username} left feedback for your learning session.", "/ratings/")
            messages.success(request, "Your rating and feedback have been submitted.")
    else:
        messages.error(request, "Please select a valid rating from 1 to 5.")
    return redirect("ratings")


@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user)
    items.filter(is_read=False).update(is_read=True)
    return render(request, "skills/notifications.html", {"notifications": items})


@login_required
def notification_status(request):
    profile = getattr(request.user, "student_profile", None)
    enabled = profile.notifications_enabled if profile else True
    volume = profile.notification_volume if profile else 45
    latest_id = (
        Notification.objects.filter(recipient=request.user)
        .order_by("-pk")
        .values_list("pk", flat=True)
        .first()
        or 0
    )
    response = JsonResponse(
        {"enabled": enabled, "volume": volume, "latest_id": latest_id}
    )
    response["Cache-Control"] = "no-store"
    return response


@login_required
def leaderboard(request):
    profiles = StudentProfile.objects.select_related("user").order_by("-points", "user__username")[:20]
    return render(request, "skills/leaderboard.html", {"profiles": profiles})
