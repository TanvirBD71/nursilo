"""Development settings for Nursilo."""
from config.settings.base import *  # noqa: F403

DEBUG = env_bool("DEBUG", True)  # noqa: F405

# DATABASES inherit PostgreSQL from base. Provide credentials via .env for migrate/tests.
