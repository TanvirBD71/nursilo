import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'test_nursilo_dev'
          AND pid <> pg_backend_pid()
        """
    )
    print("terminated", cursor.rowcount)
