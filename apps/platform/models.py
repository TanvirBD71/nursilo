"""Platform settings and feature toggles (docs/05 §15, docs/06 §8.15)."""
from django.conf import settings
from django.db import models


class PlatformSetting(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "platform_settings"

    def __str__(self):
        return self.key


class FeatureToggle(models.Model):
    code = models.CharField(max_length=64, primary_key=True)
    is_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feature_toggles"

    def __str__(self):
        return f"{self.code}={'on' if self.is_enabled else 'off'}"
