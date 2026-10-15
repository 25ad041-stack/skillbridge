# SkillBridge AI

A student-to-student skill-sharing site built with Django and SQLite. It includes accounts, skill listings, local explainable skill matches, learning requests, scheduling, progress roadmaps, points, badges, ratings, notifications, and a leaderboard.

**The matching is a small, transparent Python scoring rule.** This project does not use a trained AI model, paid service, or external AI API. Notifications are stored in the app database and shown in the signed-in student's pages; they are not emails or push messages.

The login/register screen includes a Google button as a **frontend preview only**. Google authentication is not connected; enabling it needs OAuth client credentials and an OAuth callback configuration. Password recovery uses Django's one-time reset links. In local development, the email message is printed in the terminal running the development server; configure a real email backend before deploying.

## 1. Check Python and Django

Open the VS Code terminal in this folder (**Terminal → New Terminal**) and run:

```powershell
py --version
py -m django --version
```

This project uses Django 6.1 and Python 3.14. If `py` is not found, install Python from [python.org](https://www.python.org/downloads/windows/) and select **Add Python to PATH** in the installer. If Django is not found, continue with the virtual-environment setup below.

## 2. Create and activate a virtual environment

Run these commands in the VS Code PowerShell terminal from the `Skill learning` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell says script execution is disabled, run this once in that terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

You can use Command Prompt instead: run `py -m venv .venv`, then `.venv\Scripts\activate.bat`, followed by the two `python -m pip` commands above. In VS Code, select the interpreter at `.venv\Scripts\python.exe` using **Python: Select Interpreter**.

## 3. Create and migrate the database

```powershell
python manage.py check
python manage.py makemigrations skills
python manage.py migrate
python manage.py seed_courses
```

`makemigrations` creates a migration in `skills\migrations\` from the models. `migrate` creates `db.sqlite3` and its tables. Keep migration files in your project; the SQLite database itself is excluded from source control. `seed_courses` adds 19 curated courses, including 12 Programming courses, each with beginner, intermediate, and advanced syllabus lessons. It is safe to run again.

## 4. Create demo data and an administrator (optional)

```powershell
python manage.py seed_demo
python manage.py createsuperuser
```

The demo command creates two student accounts and matching Python listings. Demo login: `maya_demo` / `DemoPass123!`. Change or delete demo accounts before using this site with real students. The admin account is separate and can manage records at `/admin/`.

## 5. Run and test

```powershell
python manage.py test skills
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser. Stop the server with **Ctrl+C**.

## Project structure

```text
Skill learning/
├── manage.py                         # Django command-line entry point
├── requirements.txt                  # Django dependency
├── README.md                         # Setup guide and model explanations
├── config/
│   ├── __init__.py
│   ├── settings.py                   # Apps, SQLite, templates, static files
│   ├── urls.py                       # Admin and app URL routing
│   ├── asgi.py
│   └── wsgi.py
├── skills/
│   ├── __init__.py
│   ├── admin.py                      # Models available to Django admin
│   ├── apps.py
│   ├── context_processors.py         # Unread notification count in navigation
│   ├── forms.py                      # Server-validated forms
│   ├── models.py                     # Database tables and constraints
│   ├── services.py                   # Matching, notifications, idempotent rewards
│   ├── tests.py                      # Automated feature tests
│   ├── urls.py                       # Application routes
│   ├── views.py                      # Page and feature behavior
│   ├── management/
│   │   └── commands/
│   │       ├── seed_demo.py          # Optional sample students and skills
│   │       └── seed_courses.py       # Add course catalog and level-based lessons
│   └── migrations/                   # Generated with makemigrations
├── templates/
│   └── skills/                       # HTML pages
├── static/
│   ├── css/styles.css                # Responsive light theme
│   └── js/app.js                     # Mobile navigation and confirmations
└── db.sqlite3                        # Created by migrate; local database
```

`manage.py`, `config/`, `skills/`, and the standard Django files are normally created by `django-admin startproject config .` and `python manage.py startapp skills`. The templates, static assets, forms, service helpers, tests, demo command, and README are application files. In this workspace the project files have already been created for you. Run the migration commands above to generate the migration for your installed Django version.

## Pages and features

| Page | URL | What it does |
| --- | --- | --- |
| Home | `/` | Explains the student skill exchange |
| Registration / login / logout | `/register/`, `/login/`, POST `/logout/` | Django account creation and password authentication |
| Continue with Google | Login and registration forms | Frontend button only; Google OAuth credentials and callback configuration are needed for real sign-in |
| Dashboard | `/dashboard/` | Skill, request, session, progress, points, badges, matches, and notification summary, with a Rewards shortcut |
| Rewards | `/rewards/` | Claim 5 points per sign-in, unlock Copper (500), Silver (1,500), and Gold (3,000) point badges, and claim course-level cashback (₹500 beginner, ₹1,000 intermediate, ₹2,000 advanced) |
| History | `/history/` | Review completed sessions, courses, milestones, claimed points, and cashback; login dates are not shown |
| Profile | `/profile/`, `/students/<username>/` | Student details, listed skills, badges, and received ratings |
| Learning history | `/profile/` on your own account | Your completed sessions, roadmap milestones, and course lessons; private to you |
| Account menu | Click the circular avatar in the top navigation | Open profile, profile editing, settings, password change, account management, and logout |
| Account settings / management | `/account/settings/`, `/account/manage/` | Review student interests, turn in-app notifications on/off, adjust alert volume, and manage account details |
| Change password | `/account/password/` | Change your password with Django's authenticated password form |
| Add / edit / delete skills | `/skills/add/`, `/skills/<id>/edit/` | Manage only the signed-in student's listings |
| Explore courses and skills | `/skills/` | Browse the course catalog, filter courses by category, and search course or peer listings |
| Course syllabus | `/courses/<course>/` | Choose beginner/intermediate/advanced syllabus, study lessons and save completed lessons |
| My skills | `/my-skills/` | Manage the signed-in student's listings |
| Recommendations | `/recommendations/` | Local matching scores and explanations |
| Requests | `/requests/` | Send, view, accept, and decline learning requests |
| Sessions | `/sessions/` | Schedule an accepted request and mark sessions complete/cancelled |
| Progress | `/progress/` | Create learning goals and update levels/percent |
| Roadmap | `/roadmap/` | Rule-based beginner/intermediate/advanced milestones |
| Ratings | `/ratings/` | Rate a completed session with optional written feedback |
| Notifications | `/notifications/` | View and mark your in-app notifications read |
| Leaderboard | `/leaderboard/` | Rank students by points |

## Database models, in plain English

Every model also has an automatically generated numeric `id` primary key. Timestamps use the configured local timezone for display and are stored timezone-aware.

* **StudentProfile** — one-to-one extension of Django's `User`. `user` identifies the account; `college`, `bio`, and `interests` are optional profile details; `points` is the earned score; `notifications_enabled` controls whether new in-app alerts are saved; `notification_volume` stores a sound level from 0 (mute) to 100; `created_at` and `updated_at` record profile history.
* **Skill** — a student's teach/learn listing. `owner` is its student; `name`, `category`, and `description` describe the skill; `level` is beginner/intermediate/advanced; `mode` is teach or learn; timestamps record listing changes. A database index helps mode/category browsing.
* **Course** — a self-paced catalog item. `name` and unique `slug` identify it; `category` powers the Explore category filter; `description` and `icon` describe it; `created_at` records its creation.
* **CourseLesson** — one ordered syllabus lesson in a course and `level`. `title`, `explanation`, and `practice` provide the lesson content; `order` keeps that level's syllabus in sequence. A constraint prevents duplicate positions at the same course level.
* **CourseLessonCompletion** — a student's completion record for a `lesson`. `user` identifies the learner and `completed_at` records when they finished; a unique user/lesson constraint keeps progress from double-counting. Completed lessons also appear in the student's private profile history.
* **LearningRequest** — a learner's request to a teacher for one offered `skill`. `learner` and `teacher` point to the two accounts; `message` is optional; `status` is pending/accepted/rejected/completed; timestamps track it. Constraints prevent requesting from yourself and duplicate learner/teacher/skill requests.
* **LearningSession** — a scheduled meeting attached to an accepted `learning_request`. `starts_at` is its date and time; `details` are optional notes; `status` is scheduled/completed/cancelled; timestamps track updates. Validation rejects past dates and unaccepted requests.
* **LearningProgress** — one student's goal for a skill. `user`, `skill_name`, `current_level`, and `target_level` describe the goal; `percent` is 0–100; timestamps record updates. A uniqueness constraint allows one goal per user and skill name.
* **LearningMilestone** — one rule-based roadmap step belonging to a `progress` goal. `title`, `description`, `stage`, and `order` show what to do and when; `completed` and optional `completed_at` track it. A constraint prevents duplicate order numbers within one goal.
* **Badge** — a point threshold achievement. `name` is unique; Copper unlocks at 500 points, Silver at 1,500, and Gold at 3,000.
* **StudentBadge** — an earned badge link between `user` and `badge`; `earned_at` records when. A constraint prevents awarding the same badge twice to the same student.
* **RewardEvent** — an audit record for points granted to a `user`. `source_type` and `source_id` identify the activity; `points` records its value; `created_at` records the award. A uniqueness constraint ensures each user receives a reward at most once for one activity.
* **Rating** — feedback for a completed `session`. `reviewer` and `reviewee` are the participants; `score` is 1–5; `feedback` is optional written feedback; `created_at` records submission. Constraints prevent self-ratings, duplicate ratings per reviewer/session, and out-of-range scores.
* **Notification** — an in-app message for a `recipient`. `message` is its text, `url` is an optional destination, `is_read` tracks unread status, and `created_at` records creation.

Django's built-in `User` model stores username, name, email, and securely hashed password; it is intentionally reused rather than storing passwords in a custom model.

## How matching works

Add one or more skills with **I want to learn** as your goals. Matching compares these goals with other students' **I can teach** listings. The best matching goal is used for each teacher listing:

* Exact skill name: 55 points.
* Otherwise, same category: 25 points.
* Same selected proficiency level: 15 points.
* Exact skill with an intermediate/advanced teacher: 10 points.
* An offered skill name overlapping a word in your profile interests: 10 points.

The displayed score is capped at 100. Reasons are shown next to the score. This is a simple deterministic matching heuristic, not machine learning. Update your profile interests and learning goals to improve results.

## Points, badges, and notifications

Each participant receives 10 points when a session is marked completed; a completed roadmap milestone grants its owner 5 points. Reward event database constraints prevent repeat awards for the same session/milestone. Add badge thresholds from `/admin/` (or the `Badge` model) to award badges automatically after new points are earned. When notifications are enabled, alerts are database records for request, session, completion, and feedback updates; turning them off prevents new in-app alert records. Visiting the notifications page marks saved alerts read. While a page is open, the app checks for new alerts every 20 seconds and plays a short browser-generated tone at the chosen volume. Use **Test sound** on Account settings to preview it; browser audio permissions/user interaction may be required. App alerts are not email, SMS, or browser push.

The current section (Dashboard, Explore, Matches, Requests, or Alerts) is shown in the navigation with darker bold text and an underline.

Password-reset email is separate from app notifications. In local development, Django's console email backend prints the reset link in the terminal. Configure and verify a production email backend before deploying password recovery.

## Manual test checklist

Use two browser sessions (or a normal and private window) to test interactions between students.

1. **Register, log in, log out:** Create a student with a unique email, log out, log in with the new password, then use the navigation logout button. The password is handled by Django authentication; a profile is created automatically.
2. **Forgot password:** From Log in, choose “Forgot your password?”, submit the email used by the account, and follow the one-time reset link printed in the development-server terminal. Set a new password and log in. The Google button is frontend-only and displays a message explaining that OAuth setup is required.
3. **Explore and course syllabus:** Open Explore and select Programming; the programming course cards appear. Open Python, choose Beginner/Intermediate/Advanced, read that level's lessons and practice exercises, and mark a lesson complete. Return to Explore; the course progress bar updates for your account. The completed lesson also appears in your private profile history.
4. **Skill CRUD and ownership:** Add a teach skill and a learn skill from My Skills; edit each; delete one. Log in as the other student and attempt to open the first student's edit/delete endpoint. The site returns HTTP 403 and does not change their listing.
5. **Search and filters:** In Explore, search for a course or peer skill and test category, proficiency, and teach/learn filters. The category filters both course cards and peer listings.
6. **Requests inbox and sent box:** As a learner, send a request to a teacher. The teacher opens Requests → Incoming and sees the sender, skill, message, and actions. The learner opens Requests → Sent and sees the teacher and request status.
7. **Recommendations:** Add a matching learn goal, and add a corresponding teach listing for another student. Recommendations should show a score and a reason. No matches appear until there is a learning goal and a compatible listing.
8. **Schedule:** Accept a request, then schedule a future date/time as either participant. Past times and requests not accepted by a teacher are rejected. The other participant receives a notification.
9. **Progress and roadmap:** Add a skill goal and percent. Change its percent from the progress page. Open Roadmap and complete a milestone; the bar updates and five points are granted once.
10. **Points and badges:** Complete a scheduled session; both participants receive ten points. Add a badge threshold in `/admin/` and earn enough points; it appears on the student's profile. Trying to complete the same session again does not award points twice.
11. **Ratings:** Mark a session complete, then submit a 1–5 rating and optional feedback. Both participants can rate once; a non-participant or a session not completed cannot be rated.
12. **Notifications and dashboard:** Trigger a request/session event; check the unread count and notification page. Visiting Notifications marks the signed-in student's alerts read. Dashboard stats reflect skills, requests, sessions, progress, points, matches, and badges.
13. **Profile history:** Complete a learning session or a roadmap milestone, then open your own profile. The completed activity appears in Learning history. Another student's profile does not show your private learning history.
14. **Notification settings and sound:** Open the avatar menu → Settings. Turn in-app notifications off and save; a test request should not create a new alert for that student. Turn it on again, select a sound volume and save; use Test sound to preview. A new alert received while signed in should play the short tone at the selected level.
15. **Navigation highlight:** Click Dashboard, Explore, Matches, Requests, or Alerts. The current section should have darker bold text and an underline; course and skill pages continue to highlight Explore.

Automated tests cover account creation, password recovery, account pages, profile-history privacy, skill ownership, search, recommendation scoring, learning request notification, reward deduplication, feedback, roadmaps, and read notifications. Run them with `python manage.py test skills`.

## Security and local-development notes

Forms use Django CSRF tokens and server-side validation; protected pages require login; skill edits/deletes and feedback are restricted to eligible users. SQLite is suitable for local development and small demos. The checked-in settings use a development-only fallback secret and enable debug by default so a beginner can run locally. **Do not deploy those defaults.** Before deployment set a private `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=0`, configure `DJANGO_ALLOWED_HOSTS`, use HTTPS, and review Django's deployment checklist. Never commit a real secret.

## Abstract and project summary

**Abstract:** SkillBridge AI is a campus learning platform that helps students exchange knowledge with peers. Students list teaching strengths and learning goals, discover explainable rule-based partner recommendations, coordinate sessions, track milestones, and recognize contributions through points and badges.

**Problem:** Students often lack a simple way to discover peers who can teach a skill they want to learn, organize learning, and follow progress.

**Proposed solution:** A Django application combines student profiles, searchable skills, local compatibility scoring, learning requests, sessions, progress roadmaps, ratings, notifications, and a points leaderboard in one responsive interface.

**Modules:** Accounts/profile; skill listings/search; matching; requests; session scheduling; progress and milestones; rewards; ratings; notifications; dashboard and leaderboard.

**Possible future enhancements:** College email verification; calendar integration; group sessions; richer matching with student feedback; email notifications; moderator tools; accessibility and localization improvements; deployment with PostgreSQL and a production web server.
