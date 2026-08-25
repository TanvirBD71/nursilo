"""Password validators per docs/07 §8 — Django hashers only; no custom crypto."""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from apps.accounts.policy import PASSWORD_MIN_LENGTH


class MinimumLengthValidator:
    def __init__(self, min_length=None):
        self.min_length = min_length or PASSWORD_MIN_LENGTH

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least %(min_length)d characters."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return _("Your password must contain at least %(min_length)d characters.") % {
            "min_length": self.min_length
        }


class ComplexityValidator:
    """Require upper, lower, digit, and special character (docs/07 §8)."""

    def validate(self, password, user=None):
        missing = []
        if not re.search(r"[A-Z]", password):
            missing.append("an uppercase letter")
        if not re.search(r"[a-z]", password):
            missing.append("a lowercase letter")
        if not re.search(r"\d", password):
            missing.append("a digit")
        if not re.search(r"[^A-Za-z0-9]", password):
            missing.append("a special character")
        if missing:
            raise ValidationError(
                _("Password must include %(requirements)s."),
                code="password_complexity",
                params={"requirements": ", ".join(missing)},
            )

    def get_help_text(self):
        return _(
            "Your password must include uppercase, lowercase, a digit, "
            "and a special character."
        )
