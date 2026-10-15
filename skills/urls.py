from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="skills/login.html"), name="login"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("rewards/", views.rewards, name="rewards"),
    path("history/", views.history, name="history"),
    path("friends/", views.friends, name="friends"),
    path("friends/<int:request_id>/<str:action>/", views.friend_request_update, name="friend_request_update"),
    path("students/<str:username>/friend-request/", views.friend_request_create, name="friend_request_create"),
    path("rewards/login/<int:login_id>/claim/", views.claim_login_points, name="claim_login_points"),
    path(
        "rewards/cashback/<int:cashback_id>/claim/",
        views.claim_cashback,
        name="claim_cashback",
    ),
    path("profile/", views.profile, name="profile"),
    path("students/<str:username>/", views.profile, name="student_profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("account/settings/", views.account_settings, name="account_settings"),
    path("account/manage/", views.manage_account, name="manage_account"),
    path(
        "account/password/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url="/account/password/done/",
        ),
        name="password_change",
    ),
    path(
        "account/password/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("skills/", views.skill_list, name="skill_list"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path(
        "courses/<slug:slug>/lessons/<int:lesson_id>/toggle/",
        views.course_lesson_toggle,
        name="course_lesson_toggle",
    ),
    path("my-skills/", views.my_skills, name="my_skills"),
    path("skills/add/", views.skill_create, name="skill_create"),
    path("skills/<int:pk>/edit/", views.skill_edit, name="skill_edit"),
    path("skills/<int:pk>/delete/", views.skill_delete, name="skill_delete"),
    path("skills/<int:skill_id>/request/", views.request_create, name="request_create"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("requests/", views.requests_list, name="requests"),
    path("requests/<int:request_id>/schedule/", views.session_create, name="session_create"),
    path("requests/<int:pk>/<str:action>/", views.request_update, name="request_update"),
    path("sessions/", views.sessions_list, name="sessions"),
    path("sessions/<int:session_id>/rate/", views.rating_create, name="rating_create"),
    path("sessions/<int:pk>/<str:status>/", views.session_update, name="session_update"),
    path("progress/", views.progress_list, name="progress"),
    path("progress/<int:pk>/update/", views.progress_update, name="progress_update"),
    path("roadmap/", views.roadmap, name="roadmap"),
    path("milestones/<int:pk>/toggle/", views.milestone_toggle, name="milestone_toggle"),
    path("ratings/", views.ratings, name="ratings"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/status/", views.notification_status, name="notification_status"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
