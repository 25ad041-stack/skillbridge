from django.core.management.base import BaseCommand
from django.utils.text import slugify

from skills.models import Course, CourseLesson


CATALOG = {
    "Programming": [
        ("Python", "Learn Python syntax, problem solving, and build useful command-line and web projects.", "Py", [
            ["Install Python and run your first program", "Variables, values, and basic data types", "Input, output, and simple calculations"],
            ["Conditions, loops, and reusable functions", "Lists, dictionaries, and working with collections", "Read and write files; handle common errors"],
            ["Organize code with modules and packages", "Build and test a small application", "Use APIs, databases, and deployment basics"],
        ]),
        ("C Programming", "Start with C fundamentals, then practice memory, data structures, and systems programming.", "C", [
            ["Set up a compiler and write a first C program", "Variables, data types, and formatted input/output", "Operators and expressions"],
            ["Conditions, loops, and functions", "Arrays, strings, and pointers", "Structures, files, and error checking"],
            ["Dynamic memory and linked data structures", "Modular projects and debugging", "Build a small systems programming project"],
        ]),
        ("C++", "Learn modern C++ fundamentals, object-oriented design, and the standard library.", "++", [
            ["Compile a first C++ program", "Variables, types, and console input/output", "Conditions and loops"],
            ["Functions, references, and arrays", "Classes, objects, and constructors", "Strings and standard library containers"],
            ["Templates and generic programming", "Resource safety and smart pointers", "Build a modular C++ application"],
        ]),
        ("Java", "Build a foundation in Java, object-oriented programming, collections, and application design.", "J", [
            ["Install the JDK and run a Java class", "Variables, types, and operators", "Conditions, loops, and methods"],
            ["Classes, objects, and encapsulation", "Arrays and collections", "Exceptions and file input/output"],
            ["Interfaces, generics, and design principles", "Unit testing and debugging", "Build a small Java application"],
        ]),
        ("JavaScript", "Learn JavaScript from language basics through browser interactions and asynchronous code.", "JS", [
            ["Run JavaScript in the browser console", "Variables, values, and operators", "Conditions, loops, and functions"],
            ["Arrays, objects, and array methods", "DOM selection and event handling", "Modules and asynchronous fetch"],
            ["Promises, async/await, and error handling", "Organize and test a front-end application", "Build a complete interactive web project"],
        ]),
        ("HTML", "Structure accessible web pages using semantic HTML, forms, and modern document features.", "H", [
            ["Create a valid HTML document", "Headings, paragraphs, links, and images", "Lists and semantic page sections"],
            ["Tables and accessible data markup", "Forms, labels, and useful input types", "Metadata and accessible page structure"],
            ["Reusable page structure and embedded media", "Accessibility checks and validation", "Plan and build a multi-page website"],
        ]),
        ("CSS", "Style responsive interfaces with layout, typography, reusable patterns, and animations.", "C", [
            ["Connect a stylesheet and select elements", "Colors, typography, and the box model", "Spacing, borders, and simple selectors"],
            ["Flexbox alignment and navigation", "CSS Grid and responsive layouts", "Reusable classes, states, and forms"],
            ["Responsive design systems and accessibility", "Transitions, animation, and maintainable CSS", "Design and implement a polished page"],
        ]),
        ("SQL and Databases", "Learn to query relational data, combine tables, and design reliable database schemas.", "DB", [
            ["Understand tables, rows, and columns", "Select, filter, and sort records", "Insert, update, and delete data safely"],
            ["Aggregate data with GROUP BY", "Join related tables", "Design keys and basic relational schemas"],
            ["Subqueries, views, and transactions", "Indexes and query performance basics", "Build a small data-backed application"],
        ]),
        ("Django Web Development", "Create database-backed websites with Django models, forms, templates, and authentication.", "Dj", [
            ["Create a Django project and application", "URLs, views, and HTML templates", "Models and your first migration"],
            ["Forms, validation, and CRUD views", "Authentication, permissions, and CSRF", "Relationships and querying with the ORM"],
            ["Testing, deployment settings, and security", "Build an API-ready application structure", "Plan and deploy a complete Django project"],
        ]),
        ("React", "Build interactive interfaces with components, state, events, and data fetching.", "R", [
            ["Create a React app and render a component", "JSX, props, and reusable components", "Handle clicks and user input"],
            ["State and controlled forms", "Render lists and manage component structure", "Load data and handle loading states"],
            ["Share state and organize application features", "Performance, accessibility, and testing basics", "Build a complete small React application"],
        ]),
        ("Git and GitHub", "Track changes, work safely with branches, and collaborate on shared projects.", "Git", [
            ["Initialize a repository and check status", "Stage and commit changes", "Read history and compare changes"],
            ["Create and switch branches", "Merge changes and resolve conflicts", "Use remotes and push to GitHub"],
            ["Pull requests and collaborative review", "Recover from mistakes with Git tools", "Use a team workflow on a sample project"],
        ]),
        ("Data Structures and Algorithms", "Practice core data structures and learn how to reason about algorithm efficiency.", "DS", [
            ["Analyze a problem and write step-by-step logic", "Arrays, strings, and searching", "Big-O time and space intuition"],
            ["Stacks, queues, and linked lists", "Hash maps, trees, and traversal", "Sorting and binary search"],
            ["Graphs and common traversal strategies", "Recursion, dynamic programming, and trade-offs", "Solve and explain a collection of problems"],
        ]),
    ],
    "Data Science": [
        ("Data Analysis with Python", "Clean, explore, and visualize datasets with practical Python workflows.", "DA", [
            ["Load a dataset and inspect its columns", "Clean missing and inconsistent values", "Summarize data with descriptive statistics"],
            ["Transform and group tabular data", "Explore relationships with charts", "Explain insights with a clear notebook"],
            ["Build a repeatable analysis pipeline", "Validate results and avoid misleading charts", "Present a complete data investigation"],
        ]),
        ("Machine Learning Foundations", "Understand model training, evaluation, and responsible use of machine learning.", "ML", [
            ["Prepare features and a target variable", "Split data for training and testing", "Understand prediction and model error"],
            ["Train a simple classification model", "Train and evaluate a regression model", "Compare metrics and improve features"],
            ["Cross-validation and model selection", "Data leakage, fairness, and limitations", "Build and communicate a small ML project"],
        ]),
    ],
    "Design": [
        ("UI/UX Design", "Learn user research, wireframes, visual design, prototyping, and usability testing.", "UX", [
            ["Identify a user and their problem", "Sketch a simple user flow", "Create low-fidelity wireframes"],
            ["Build a consistent visual system", "Prototype key interactions", "Run a usability check and record feedback"],
            ["Refine designs using evidence", "Accessibility and responsive design review", "Present a complete product design case study"],
        ]),
        ("Figma for Beginners", "Practice designing interfaces and clickable prototypes using Figma workflows.", "F", [
            ["Set up a file, pages, and frames", "Use shapes, text, and image assets", "Align and organize interface elements"],
            ["Create components and variants", "Use auto layout and responsive frames", "Connect screens into a prototype"],
            ["Build a small reusable design system", "Share, review, and iterate on a prototype", "Prepare a polished design handoff"],
        ]),
    ],
    "Business": [
        ("Public Speaking", "Build confidence with speech structure, delivery practice, and audience-aware presentations.", "PS", [
            ["Choose a topic and audience", "Write a clear opening and key message", "Practice voice, pacing, and posture"],
            ["Use evidence and stories effectively", "Handle questions and manage nerves", "Deliver a timed practice presentation"],
            ["Adapt delivery to different audiences", "Use feedback to refine a persuasive talk", "Present a polished final speech"],
        ]),
        ("Project Management", "Plan practical projects with clear scope, milestones, communication, and review.", "PM", [
            ["Define a problem, goal, and project scope", "List tasks and dependencies", "Set realistic milestones and responsibilities"],
            ["Track progress and manage risks", "Communicate status and handle changes", "Run a project review and record decisions"],
            ["Prioritize work across competing goals", "Improve the process using team feedback", "Create a complete project plan and retrospective"],
        ]),
    ],
    "Creative": [
        ("Creative Writing", "Develop story ideas, characters, scenes, and a revision habit through short exercises.", "W", [
            ["Collect ideas and choose a prompt", "Build a character with a clear want", "Write a focused opening scene"],
            ["Use dialogue and point of view", "Structure scenes around conflict", "Revise a draft for clarity and pace"],
            ["Connect scenes into a complete story", "Edit for voice, rhythm, and detail", "Share a polished piece and reflect on feedback"],
        ]),
    ],
}

LEVEL_NAMES = ["beginner", "intermediate", "advanced"]


class Command(BaseCommand):
    help = "Create the curated course catalog and beginner-to-advanced lesson outlines."

    def handle(self, *args, **options):
        created_courses = 0
        created_lessons = 0
        for category, courses in CATALOG.items():
            for name, description, icon, levels in courses:
                course, created = Course.objects.update_or_create(
                    slug=slugify(name),
                    defaults={
                        "name": name,
                        "category": category,
                        "description": description,
                        "icon": icon,
                    },
                )
                created_courses += int(created)
                for level_name, topics in zip(LEVEL_NAMES, levels, strict=True):
                    for order, title in enumerate(topics, start=1):
                        _, lesson_created = CourseLesson.objects.update_or_create(
                            course=course,
                            level=level_name,
                            order=order,
                            defaults={
                                "title": title,
                                "explanation": (
                                    f"In this {level_name} {course.name} lesson, learn how {title.lower()} "
                                    f"fits into practical {course.category.lower()} work. Read the key ideas, "
                                    "try each step in your own workspace, and note any questions to review."
                                ),
                                "practice": (
                                    f"Practice: use {course.name} to complete “{title}”. "
                                    "Save your result and explain one thing you learned."
                                ),
                            },
                        )
                        created_lessons += int(lesson_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Course catalog ready: {Course.objects.count()} courses, "
                f"{CourseLesson.objects.count()} level-based lessons "
                f"({created_courses} courses and {created_lessons} lessons newly created)."
            )
        )
