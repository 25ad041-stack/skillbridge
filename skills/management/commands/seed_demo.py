from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from skills.models import Badge, Skill, StudentProfile


class Command(BaseCommand):
    help = "Create a small set of demo students, skills, and starter badges."

    def handle(self, *args, **options):
        for name, description, points_required, icon in [
            ("Copper", "Reach 500 earned points.", 500, "🥉"),
            ("Silver", "Reach 1,500 earned points.", 1500, "🥈"),
            ("Gold", "Reach 3,000 earned points.", 3000, "🥇"),
        ]:
            Badge.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "points_required": points_required,
                    "icon": icon,
                },
            )
        for username, first_name, email, college, interests in [
            ("maya_demo", "Maya", "maya@example.com", "North College", "python design"),
            ("arjun_demo", "Arjun", "arjun@example.com", "North College", "web design"),
        ]:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first_name, "email": email},
            )
            if created:
                user.set_password("DemoPass123!")
                user.save()
            StudentProfile.objects.get_or_create(
                user=user, defaults={"college": college, "interests": interests}
            )
        maya = User.objects.get(username="maya_demo")
        arjun = User.objects.get(username="arjun_demo")
        Skill.objects.get_or_create(
            owner=maya,
            name="Python",
            mode=Skill.Mode.LEARN,
            defaults={"category": "Programming", "level": Skill.Level.BEGINNER, "description": "I want to learn Python basics."},
        )
        Skill.objects.get_or_create(
            owner=arjun,
            name="Python",
            mode=Skill.Mode.TEACH,
            defaults={"category": "Programming", "level": Skill.Level.INTERMEDIATE, "description": "I can help with Python fundamentals and small projects."},
        )
        self.stdout.write(self.style.SUCCESS("Demo data ready. Login: maya_demo / DemoPass123!"))
