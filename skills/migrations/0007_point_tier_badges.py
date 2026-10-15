from django.db import migrations


BADGES = [
    ("Copper", "Reach 500 earned points.", 500, "🥉"),
    ("Silver", "Reach 1,500 earned points.", 1500, "🥈"),
    ("Gold", "Reach 3,000 earned points.", 3000, "🥇"),
]

LEGACY_BADGES = {
    "First Steps": "Copper",
    "Skill Sharer": "Silver",
}


def update_badges(apps, schema_editor):
    Badge = apps.get_model("skills", "Badge")
    StudentBadge = apps.get_model("skills", "StudentBadge")
    database = schema_editor.connection.alias

    for old_name, new_name in LEGACY_BADGES.items():
        old_badge = Badge.objects.using(database).filter(name=old_name).first()
        target_badge = Badge.objects.using(database).filter(name=new_name).first()

        if old_badge and target_badge:
            for earned in StudentBadge.objects.using(database).filter(badge=old_badge):
                already_earned = StudentBadge.objects.using(database).filter(
                    user_id=earned.user_id, badge=target_badge
                ).exists()
                if already_earned:
                    earned.delete()
                else:
                    earned.badge_id = target_badge.pk
                    earned.save(update_fields=["badge"])
            old_badge.delete()
        elif old_badge:
            old_badge.name = new_name
            old_badge.save(update_fields=["name"])

    for name, description, points_required, icon in BADGES:
        Badge.objects.using(database).update_or_create(
            name=name,
            defaults={
                "description": description,
                "points_required": points_required,
                "icon": icon,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("skills", "0006_friendrequest"),
    ]

    operations = [
        migrations.RunPython(update_badges, migrations.RunPython.noop),
    ]
