from datetime import timedelta

from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .models import (
    LearningProgress,
    LearningRequest,
    LearningSession,
    LoginHistory,
    CashbackReward,
    Course,
    CourseLesson,
    CourseLessonCompletion,
    FriendRequest,
    Notification,
    Rating,
    Badge,
    RewardEvent,
    Skill,
    StudentBadge,
    StudentProfile,
)
from .services import award_points, get_recommendations, notify


class SkillBridgeTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user("learner", password="StrongPass123!", first_name="Learn")
        self.teacher = User.objects.create_user("teacher", password="StrongPass123!", first_name="Teach")
        StudentProfile.objects.create(user=self.learner, interests="python design")
        StudentProfile.objects.create(user=self.teacher)

    def test_registration_creates_profile_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "New Student",
                "username": "newstudent",
                "email": "new@example.com",
                "password1": "StrongPass123!x",
                "password2": "StrongPass123!x",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(StudentProfile.objects.filter(user__username="newstudent").exists())
        self.assertEqual(LoginHistory.objects.filter(user__username="newstudent").count(), 1)

    def test_successful_login_is_saved_to_private_login_history(self):
        self.learner.set_password("StrongPass123!x")
        self.learner.save(update_fields=["password"])

        response = self.client.post(
            reverse("login"),
            {"username": "learner", "password": "StrongPass123!x"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(LoginHistory.objects.filter(user=self.learner).count(), 1)
        activity_history = self.client.get(reverse("history"))
        self.assertContains(activity_history, "Review completed learning, course lessons, and rewards.")
        self.assertNotContains(activity_history, "Successful login")

        self.client.force_login(self.teacher)
        self.assertContains(
            self.client.get(reverse("history")),
            "Review completed learning, course lessons, and rewards.",
        )

    def test_history_shows_one_empty_state_when_account_has_no_activity(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("history"))
        self.assertContains(response, "No history yet.")
        self.assertNotContains(response, "Completed sessions")
        self.assertNotContains(response, "Login history")

    def test_own_profile_hides_account_name(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Your profile")
        self.assertNotContains(response, "Learn’s profile")
        self.assertNotContains(response, "<h1>Learn</h1>")

    def test_friends_page_can_search_students_and_send_friend_request(self):
        self.client.force_login(self.learner)
        friends_page = self.client.get(reverse("friends"))
        self.assertContains(friends_page, "Find students")
        self.assertContains(friends_page, "Add friend")
        self.assertContains(friends_page, "teacher")

        search_results = self.client.get(reverse("friends"), {"q": "teach"})
        self.assertContains(search_results, "teacher")
        self.assertNotContains(search_results, "learner")

        response = self.client.post(
            reverse("friend_request_create", args=[self.teacher.username])
        )
        self.assertRedirects(
            response, reverse("student_profile", args=[self.teacher.username])
        )
        friend_request = FriendRequest.objects.get(sender=self.learner, receiver=self.teacher)
        self.assertEqual(friend_request.status, FriendRequest.Status.PENDING)
        self.assertNotContains(self.client.get(reverse("friends")), "Add friend")

    def test_login_bonus_can_only_be_claimed_once(self):
        self.client.force_login(self.learner)
        login_event = LoginHistory.objects.filter(
            user=self.learner, points_claimed=False
        ).first()
        self.assertIsNotNone(login_event)

        claim_url = reverse("claim_login_points", args=[login_event.pk])
        response = self.client.post(claim_url)
        self.assertRedirects(response, reverse("rewards"))
        self.learner.student_profile.refresh_from_db()
        login_event.refresh_from_db()
        self.assertEqual(self.learner.student_profile.points, 5)
        self.assertTrue(login_event.points_claimed)
        self.assertEqual(
            RewardEvent.objects.filter(
                user=self.learner, source_type="login", source_id=login_event.pk
            ).count(),
            1,
        )

        self.client.post(claim_url)
        self.learner.student_profile.refresh_from_db()
        self.assertEqual(self.learner.student_profile.points, 5)
        self.assertEqual(
            RewardEvent.objects.filter(
                user=self.learner, source_type="login", source_id=login_event.pk
            ).count(),
            1,
        )

    def test_course_level_cashback_unlocks_and_is_credited_once(self):
        course = Course.objects.create(
            name="Cashback Python",
            slug="cashback-python",
            category="Programming",
            description="Learn Python with cashback.",
        )
        lessons = [
            CourseLesson.objects.create(
                course=course,
                level=CourseLesson.Level.BEGINNER,
                title=f"Python lesson {number}",
                explanation="Lesson explanation.",
                practice="Practice this lesson.",
                order=number,
            )
            for number in (1, 2)
        ]
        self.client.force_login(self.learner)

        self.client.post(
            reverse("course_lesson_toggle", args=[course.slug, lessons[0].pk]),
            {"level": CourseLesson.Level.BEGINNER},
        )
        self.assertFalse(CashbackReward.objects.filter(user=self.learner).exists())
        self.client.post(
            reverse("course_lesson_toggle", args=[course.slug, lessons[1].pk]),
            {"level": CourseLesson.Level.BEGINNER},
        )
        cashback = CashbackReward.objects.get(user=self.learner, course=course)
        self.assertEqual(cashback.amount, 500)
        self.assertIsNone(cashback.claimed_at)

        claim_url = reverse("claim_cashback", args=[cashback.pk])
        response = self.client.post(claim_url)
        self.assertRedirects(response, reverse("rewards"))
        cashback.refresh_from_db()
        self.assertIsNotNone(cashback.claimed_at)
        self.assertContains(self.client.get(reverse("rewards")), "₹500")

        self.client.post(claim_url)
        self.assertEqual(CashbackReward.objects.filter(user=self.learner, course=course).count(), 1)
        self.assertEqual(
            sum(
                reward.amount
                for reward in CashbackReward.objects.filter(
                    user=self.learner, claimed_at__isnull=False
                )
            ),
            500,
        )

    def test_authenticated_pages_render(self):
        self.client.force_login(self.learner)
        for route in (
            "dashboard",
            "rewards",
            "history",
            "profile",
            "profile_edit",
            "account_settings",
            "manage_account",
            "password_change",
            "password_reset",
            "password_reset_done",
            "skill_list",
            "my_skills",
            "recommendations",
            "requests",
            "sessions",
            "progress",
            "roadmap",
            "ratings",
            "notifications",
            "leaderboard",
        ):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)

    def test_login_shows_password_recovery_and_google_button(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("password_reset"))
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "Google OAuth setup is required")

    def test_password_reset_email_and_confirmation_flow(self):
        self.learner.email = "learner@example.com"
        self.learner.save(update_fields=["email"])
        response = self.client.post(
            reverse("password_reset"), {"email": "learner@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset/", mail.outbox[0].body)

        uid = urlsafe_base64_encode(force_bytes(self.learner.pk))
        token = default_token_generator.make_token(self.learner)
        confirmation_url = reverse("password_reset_confirm", args=[uid, token])
        response = self.client.get(confirmation_url)
        self.assertRedirects(response, reverse("password_reset_confirm", args=[uid, "set-password"]))
        response = self.client.post(
            response.url,
            {
                "new_password1": "ResetStrongPass123!",
                "new_password2": "ResetStrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.learner.refresh_from_db()
        self.assertTrue(self.learner.check_password("ResetStrongPass123!"))

    def test_learning_history_is_visible_only_on_own_profile(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python lessons",
            mode=Skill.Mode.TEACH,
        )
        learning_request = LearningRequest.objects.create(
            learner=self.learner,
            teacher=self.teacher,
            skill=skill,
            status=LearningRequest.Status.COMPLETED,
        )
        LearningSession.objects.create(
            learning_request=learning_request,
            starts_at=timezone.now() - timedelta(days=1),
            status=LearningSession.Status.COMPLETED,
        )
        self.client.force_login(self.learner)
        own_profile = self.client.get(reverse("profile"))
        self.assertContains(own_profile, "Learning history")
        self.assertContains(own_profile, "Python session completed")
        other_profile = self.client.get(reverse("student_profile", args=["teacher"]))
        self.assertNotContains(other_profile, "Python session completed")

    def test_account_menu_is_rendered_for_signed_in_users(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, 'id="account-trigger"')
        self.assertContains(response, "Edit profile")
        self.assertContains(response, "Settings")
        self.assertContains(response, "Change password")
        self.assertContains(response, "Manage account")

    def test_navigation_highlights_current_page(self):
        self.client.force_login(self.learner)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, 'href="/dashboard/" class="nav-active"')
        self.assertContains(dashboard, 'href="/rewards/">Rewards</a>')
        self.assertContains(dashboard, 'href="/rewards/">Explore your rewards →</a>')
        self.assertContains(dashboard, 'href="/history/">History</a>')
        explore = self.client.get(reverse("skill_list"))
        self.assertContains(explore, 'href="/skills/" class="nav-active"')
        self.assertNotContains(explore, 'href="/dashboard/" class="nav-active"')
        rewards = self.client.get(reverse("rewards"))
        self.assertContains(rewards, 'href="/rewards/" class="nav-active"')
        history = self.client.get(reverse("history"))
        self.assertContains(history, 'href="/history/" class="nav-active"')

    def test_rewards_page_shows_points_badges_and_reward_history(self):
        self.client.force_login(self.learner)
        self.learner.student_profile.points = 10
        self.learner.student_profile.save(update_fields=["points"])
        earned_badge = Badge.objects.get(name="Copper")
        StudentBadge.objects.create(user=self.learner, badge=earned_badge)
        RewardEvent.objects.create(
            user=self.learner, source_type="session", source_id=1, points=10
        )

        response = self.client.get(reverse("rewards"))
        self.assertContains(response, "10")
        self.assertContains(response, "Copper")
        self.assertContains(response, "Silver")
        self.assertContains(response, "Gold")
        self.assertContains(response, "500 points")
        self.assertContains(response, "1500 points")
        self.assertContains(response, "3000 points")
        self.assertContains(response, "Completed a learning session")
        self.assertContains(response, "+10 pts")
        self.assertContains(response, "Beginner")
        self.assertContains(response, "₹500")
        self.assertContains(response, "₹1000")
        self.assertContains(response, "₹2000")

    def test_point_tier_badges_unlock_at_copper_silver_and_gold_thresholds(self):
        award_points(self.learner, "test", 101, 500)
        self.assertQuerySetEqual(
            StudentBadge.objects.filter(user=self.learner).order_by("badge__points_required"),
            Badge.objects.filter(name="Copper").order_by("points_required"),
            transform=lambda earned: earned.badge,
        )

        award_points(self.learner, "test", 102, 1000)
        self.assertEqual(
            set(StudentBadge.objects.filter(user=self.learner).values_list("badge__name", flat=True)),
            {"Copper", "Silver"},
        )

        award_points(self.learner, "test", 103, 1500)
        self.assertEqual(
            set(StudentBadge.objects.filter(user=self.learner).values_list("badge__name", flat=True)),
            {"Copper", "Silver", "Gold"},
        )

    def test_explore_category_filter_lists_matching_courses(self):
        python = Course.objects.create(
            name="Python",
            slug="python",
            category="Programming",
            description="Learn Python",
        )
        Course.objects.create(
            name="Figma for Beginners",
            slug="figma",
            category="Design",
            description="Learn design",
        )
        self.client.force_login(self.learner)
        response = self.client.get(reverse("skill_list"), {"category": "Programming"})
        self.assertEqual(list(response.context["courses"]), [python])
        self.assertContains(response, "Python")
        self.assertNotContains(response, "Figma for Beginners")

    def test_course_level_syllabus_and_lesson_progress(self):
        course = Course.objects.create(
            name="Python",
            slug="python",
            category="Programming",
            description="Learn Python",
        )
        beginner_lesson = CourseLesson.objects.create(
            course=course,
            level=CourseLesson.Level.BEGINNER,
            title="Variables and values",
            explanation="Learn names and values.",
            practice="Create three variables.",
            order=1,
        )
        advanced_lesson = CourseLesson.objects.create(
            course=course,
            level=CourseLesson.Level.ADVANCED,
            title="Advanced Python packages",
            explanation="Organize a package.",
            practice="Build a package.",
            order=1,
        )
        self.client.force_login(self.learner)
        beginner = self.client.get(reverse("course_detail", args=[course.slug]))
        self.assertContains(beginner, "Variables and values")
        self.assertNotContains(beginner, "Advanced Python packages")
        self.client.post(
            reverse("course_lesson_toggle", args=[course.slug, beginner_lesson.pk]),
            {"level": CourseLesson.Level.BEGINNER},
        )
        self.assertTrue(
            CourseLessonCompletion.objects.filter(user=self.learner, lesson=beginner_lesson).exists()
        )
        own_profile = self.client.get(reverse("profile"))
        self.assertContains(own_profile, "Completed course lessons")
        self.assertContains(own_profile, "Variables and values")
        teacher_profile = self.client.get(reverse("student_profile", args=["teacher"]))
        self.assertNotContains(teacher_profile, "Variables and values")
        catalog = self.client.get(reverse("skill_list"), {"category": "Programming"})
        self.assertEqual(catalog.context["courses"][0].completed_count, 1)
        self.assertEqual(catalog.context["courses"][0].progress_percent, 50)
        advanced = self.client.get(
            reverse("course_detail", args=[course.slug]), {"level": CourseLesson.Level.ADVANCED}
        )
        self.assertContains(advanced, "Advanced Python packages")
        self.assertNotContains(advanced, "Variables and values")
        self.assertEqual(advanced.context["completed_count"], 0)

    def test_incoming_and_sent_request_boxes_filter_the_lists(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Teach Python",
            mode=Skill.Mode.TEACH,
        )
        LearningRequest.objects.create(
            learner=self.learner,
            teacher=self.teacher,
            skill=skill,
            message="Please teach me Python",
        )
        self.client.force_login(self.teacher)
        incoming = self.client.get(reverse("requests"), {"box": "incoming"})
        self.assertContains(incoming, "Please teach me Python")
        self.assertContains(incoming, "Learn")
        self.assertContains(incoming, "Incoming requests")
        self.client.force_login(self.learner)
        sent = self.client.get(reverse("requests"), {"box": "sent"})
        self.assertContains(sent, "Requests you sent")
        self.assertContains(sent, "Teach")
        self.assertContains(sent, "Please teach me Python")

    def test_notification_settings_control_delivery_and_sound_volume(self):
        self.client.force_login(self.learner)
        response = self.client.post(
            reverse("account_settings"), {"notification_volume": "72"}
        )
        self.assertRedirects(response, reverse("account_settings"))
        self.learner.student_profile.refresh_from_db()
        self.assertFalse(self.learner.student_profile.notifications_enabled)
        self.assertEqual(self.learner.student_profile.notification_volume, 72)
        self.assertIsNone(notify(self.learner, "Should not be saved"))
        self.assertFalse(Notification.objects.filter(recipient=self.learner).exists())
        status = self.client.get(reverse("notification_status")).json()
        self.assertFalse(status["enabled"])
        self.assertEqual(status["volume"], 72)

        self.client.post(
            reverse("account_settings"),
            {"notifications_enabled": "on", "notification_volume": "25"},
        )
        created = notify(self.learner, "Notifications are on")
        self.assertIsNotNone(created)
        status = self.client.get(reverse("notification_status")).json()
        self.assertTrue(status["enabled"])
        self.assertEqual(status["volume"], 25)
        self.assertEqual(status["latest_id"], created.pk)

    def test_student_can_change_password(self):
        self.client.force_login(self.learner)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "StrongPass123!",
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))
        self.learner.refresh_from_db()
        self.assertTrue(self.learner.check_password("NewStrongPass123!"))

    def test_accepted_request_can_be_scheduled(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python",
            mode=Skill.Mode.TEACH,
        )
        learning_request = LearningRequest.objects.create(
            learner=self.learner,
            teacher=self.teacher,
            skill=skill,
            status=LearningRequest.Status.ACCEPTED,
        )
        self.client.force_login(self.learner)
        starts_at = (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("session_create", args=[learning_request.pk]),
            {"starts_at": starts_at, "details": "Bring a laptop"},
        )
        self.assertRedirects(response, reverse("sessions"))
        self.assertEqual(LearningSession.objects.filter(learning_request=learning_request).count(), 1)

    def test_skill_crud_is_limited_to_owner(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python tutoring",
            mode=Skill.Mode.TEACH,
        )
        self.client.force_login(self.learner)
        response = self.client.get(reverse("skill_edit", args=[skill.pk]))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.learner)
        response = self.client.post(reverse("skill_delete", args=[skill.pk]))
        self.assertEqual(response.status_code, 403)

    def test_search_filters_skill_marketplace(self):
        Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python tutoring",
            mode=Skill.Mode.TEACH,
        )
        self.client.force_login(self.learner)
        response = self.client.get(reverse("skill_list"), {"q": "python", "category": "Programming"})
        self.assertContains(response, "Python")

    def test_recommendation_explains_matching_score(self):
        Skill.objects.create(
            owner=self.learner,
            name="Python",
            category="Programming",
            level=Skill.Level.INTERMEDIATE,
            description="I want to learn Python",
            mode=Skill.Mode.LEARN,
        )
        taught = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.INTERMEDIATE,
            description="I teach Python",
            mode=Skill.Mode.TEACH,
        )
        recommendations = get_recommendations(self.learner)
        self.assertEqual(recommendations[0]["skill"], taught)
        self.assertEqual(recommendations[0]["score"], 90)
        self.assertTrue(recommendations[0]["reasons"])

    def test_learning_request_and_notification(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python",
            mode=Skill.Mode.TEACH,
        )
        self.client.force_login(self.learner)
        response = self.client.post(reverse("request_create", args=[skill.pk]), {"message": "Please teach me"})
        self.assertRedirects(response, reverse("requests"))
        self.assertTrue(LearningRequest.objects.filter(learner=self.learner).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.teacher).exists())

    def test_completed_session_rewards_once_and_can_be_rated(self):
        skill = Skill.objects.create(
            owner=self.teacher,
            name="Python",
            category="Programming",
            level=Skill.Level.ADVANCED,
            description="Python",
            mode=Skill.Mode.TEACH,
        )
        learning_request = LearningRequest.objects.create(
            learner=self.learner,
            teacher=self.teacher,
            skill=skill,
            status=LearningRequest.Status.ACCEPTED,
        )
        session = LearningSession.objects.create(
            learning_request=learning_request,
            starts_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_login(self.learner)
        response = self.client.post(reverse("session_update", args=[session.pk, "completed"]))
        self.assertRedirects(response, reverse("sessions"))
        self.learner.student_profile.refresh_from_db()
        self.assertEqual(self.learner.student_profile.points, 10)
        self.client.post(reverse("session_update", args=[session.pk, "completed"]))
        self.learner.student_profile.refresh_from_db()
        self.assertEqual(self.learner.student_profile.points, 10)
        self.client.post(reverse("rating_create", args=[session.pk]), {"score": 5, "feedback": "Great"})
        self.assertTrue(Rating.objects.filter(session=session, reviewer=self.learner).exists())

    def test_progress_and_rule_based_roadmap(self):
        self.client.force_login(self.learner)
        response = self.client.post(
            reverse("progress"),
            {"skill_name": "Python", "current_level": "beginner", "target_level": "advanced", "percent": 20},
        )
        self.assertRedirects(response, reverse("progress"))
        response = self.client.get(reverse("roadmap"))
        progress = LearningProgress.objects.get(user=self.learner)
        self.assertContains(response, "Learn Python fundamentals")
        self.assertEqual(progress.milestones.count(), 6)

    def test_notification_page_marks_only_users_notifications_read(self):
        notification = Notification.objects.create(recipient=self.learner, message="Hello")
        self.client.force_login(self.learner)
        self.client.get(reverse("notifications"))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
