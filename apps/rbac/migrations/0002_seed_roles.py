"""Seed V1 RBAC role catalog (docs/03)."""

from django.db import migrations


ROLES = [
    ("super_admin", "Super Admin"),
    ("admin", "Admin"),
    ("editor", "Editor"),
    ("reviewer", "Reviewer"),
    ("author", "Author"),
    ("student", "Student"),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("rbac", "Role")
    for code, name in ROLES:
        Role.objects.get_or_create(code=code, defaults={"name": name})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("rbac", "Role")
    Role.objects.filter(code__in=[code for code, _ in ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0001_unit1_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
