"""Analytics read models — rebuildable projections (docs/05 §14, docs/06 §11)."""
from django.conf import settings
from django.db import models


class LearnerTopicStat(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_stats",
    )
    topic = models.ForeignKey(
        "learning.Topic",
        on_delete=models.CASCADE,
        related_name="learner_stats",
    )
    attempt_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    accuracy_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "learner_topic_stats"
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="uq_learner_topic_stats"),
        ]
        indexes = [
            models.Index(fields=["updated_at"]),
        ]


class QuestionUsageStat(models.Model):
    question = models.OneToOneField(
        "assessment.Question",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="usage_stat",
    )
    attempt_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    accuracy_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    difficulty_trend = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "question_usage_stats"
        indexes = [
            models.Index(fields=["updated_at"]),
        ]


class ContentPerformanceStat(models.Model):
    content_type = models.CharField(max_length=64)
    content_id = models.UUIDField()
    views_or_starts = models.PositiveIntegerField(default=0)
    completions = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_performance_stats"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "content_id"],
                name="uq_content_performance_stats",
            ),
        ]
        indexes = [
            models.Index(fields=["updated_at"]),
        ]
