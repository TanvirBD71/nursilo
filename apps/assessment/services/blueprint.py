"""
Blueprint access + blueprint-driven exam generation FOUNDATION (UNIT-11).

The blueprint is data/config (``ExamBlueprint`` + categories + competencies +
cognitive allocations), never hard-coded in views. Generation targets the exact
per-category counts and the cognitive split, and NEVER silently substitutes,
downgrades, or invents questions: when the eligible published pool cannot satisfy
a category, a clear shortage report is returned instead of a compromised exam.

This does not replace UNIT-6 explicit ExamDefinitionItem pools or UNIT-5 practice
selection — it is an additional, opt-in planner over the published question bank.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from django.db.models import QuerySet

from apps.assessment.models import (
    BlueprintCategory,
    ExamBlueprint,
    Question,
)
from apps.common.choices import CognitiveLevel, EditorialState

STATUS_COMPLIANT = "blueprint_compliant"
STATUS_INSUFFICIENT = "insufficient_question_pool"


@dataclass
class CategoryPlan:
    category_code: str
    category_name: str
    required: int
    available: int

    @property
    def satisfied(self) -> bool:
        return self.available >= self.required

    @property
    def shortfall(self) -> int:
        return max(0, self.required - self.available)


@dataclass
class CognitivePlan:
    cognitive_level: str
    target: int
    available: int

    @property
    def satisfied(self) -> bool:
        return self.available >= self.target

    @property
    def shortfall(self) -> int:
        return max(0, self.target - self.available)


@dataclass
class BlueprintPlan:
    blueprint_code: str
    blueprint_name: str
    total_target: int
    status: str
    category_plans: list[CategoryPlan] = field(default_factory=list)
    cognitive_plans: list[CognitivePlan] = field(default_factory=list)
    shortages: list[str] = field(default_factory=list)
    selected_question_ids: list = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        return self.status == STATUS_COMPLIANT


class BlueprintService:
    """Read access + generation planning over published question pools."""

    @classmethod
    def active_blueprint(cls) -> ExamBlueprint | None:
        return ExamBlueprint.objects.filter(is_active=True).order_by("-created_at").first()

    @classmethod
    def get_blueprint(cls, code: str) -> ExamBlueprint | None:
        return ExamBlueprint.objects.filter(code=code).first()

    @classmethod
    def total_allocation(cls, blueprint: ExamBlueprint) -> int:
        return sum(
            c.question_count for c in blueprint.categories.all()
        )

    @classmethod
    def eligible_pool_qs(cls) -> QuerySet[Question]:
        """
        Published, non-archived, versioned questions that are not awaiting review.

        ``needs_review`` rows are excluded from blueprint-compliant generation —
        uncertain mappings are never silently substituted into an exam.
        """
        return Question.objects.filter(
            editorial_state=EditorialState.PUBLISHED,
            is_archived=False,
            current_version__isnull=False,
            needs_review=False,
        )

    @classmethod
    def eligible_for_category(cls, category: BlueprintCategory) -> QuerySet[Question]:
        return cls.eligible_pool_qs().filter(blueprint_category=category)

    @classmethod
    def plan(cls, blueprint: ExamBlueprint) -> BlueprintPlan:
        """
        Analyze the eligible pool against blueprint targets and report compliance.

        Category compliance is authoritative for COMPLIANT vs INSUFFICIENT; the
        cognitive split is reported (target vs available) so admins can act.
        """
        total_target = cls.total_allocation(blueprint) or blueprint.total_questions
        categories = list(blueprint.categories.all().order_by("sort_order", "name"))
        category_plans: list[CategoryPlan] = []
        shortages: list[str] = []
        for category in categories:
            available = cls.eligible_for_category(category).count()
            plan = CategoryPlan(
                category_code=category.code,
                category_name=category.name,
                required=category.question_count,
                available=available,
            )
            category_plans.append(plan)
            if not plan.satisfied:
                shortages.append(
                    f"{category.name} requires {plan.required} eligible but only "
                    f"{plan.available} published match."
                )

        cognitive_plans = cls._cognitive_plans(blueprint, total_target, shortages)

        category_ok = all(p.satisfied for p in category_plans)
        cognitive_ok = all(p.satisfied for p in cognitive_plans)
        status = (
            STATUS_COMPLIANT if (category_ok and cognitive_ok) else STATUS_INSUFFICIENT
        )
        return BlueprintPlan(
            blueprint_code=blueprint.code,
            blueprint_name=blueprint.name,
            total_target=total_target,
            status=status,
            category_plans=category_plans,
            cognitive_plans=cognitive_plans,
            shortages=shortages,
        )

    @classmethod
    def _cognitive_plans(
        cls, blueprint: ExamBlueprint, total_target: int, shortages: list[str]
    ) -> list[CognitivePlan]:
        allocations = list(
            blueprint.cognitive_allocations.all().order_by("sort_order", "cognitive_level")
        )
        plans: list[CognitivePlan] = []
        pool = cls.eligible_pool_qs()
        label = dict(CognitiveLevel.choices)
        for alloc in allocations:
            target = round(alloc.percent / 100 * total_target)
            available = pool.filter(cognitive_level=alloc.cognitive_level).count()
            plan = CognitivePlan(
                cognitive_level=alloc.cognitive_level,
                target=target,
                available=available,
            )
            plans.append(plan)
            if not plan.satisfied:
                shortages.append(
                    f"{label.get(alloc.cognitive_level, alloc.cognitive_level)} cognitive "
                    f"level requires {plan.target} eligible but only {plan.available} match."
                )
        return plans

    @classmethod
    def generate(cls, blueprint: ExamBlueprint, *, rng: random.Random | None = None) -> BlueprintPlan:
        """
        Produce a blueprint-compliant question selection or a shortage report.

        When compliant, selects the exact required count per category (best-effort
        honoring the cognitive split within each category). When not compliant,
        returns the plan with status INSUFFICIENT and NO selection — never a
        silently downgraded exam.
        """
        rng = rng or random.Random()
        plan = cls.plan(blueprint)
        if not plan.compliant:
            return plan

        cognitive_weights = [
            (alloc.cognitive_level, alloc.percent)
            for alloc in blueprint.cognitive_allocations.all()
        ]
        selected_ids: list = []
        for category in blueprint.categories.all().order_by("sort_order", "name"):
            need = category.question_count
            pool_ids = list(
                cls.eligible_for_category(category).values_list("id", flat=True)
            )
            chosen = cls._draw_with_cognitive(
                category=category,
                pool_ids=pool_ids,
                need=need,
                cognitive_weights=cognitive_weights,
                rng=rng,
            )
            selected_ids.extend(chosen)
        plan.selected_question_ids = selected_ids
        return plan

    @classmethod
    def _draw_with_cognitive(
        cls, *, category, pool_ids, need, cognitive_weights, rng
    ) -> list:
        """Best-effort cognitive-balanced draw within a single category."""
        if need <= 0 or not pool_ids:
            return []
        if need >= len(pool_ids):
            return list(pool_ids)

        # Bucket eligible question ids by cognitive level for this category.
        buckets: dict[str, list] = {}
        rows = cls.eligible_for_category(category).values_list("id", "cognitive_level")
        for qid, level in rows:
            buckets.setdefault(level or "", []).append(qid)
        for ids in buckets.values():
            rng.shuffle(ids)

        chosen: list = []
        # First pass: draw per-level quotas proportional to the cognitive split.
        for level, percent in cognitive_weights:
            quota = round(percent / 100 * need)
            take = buckets.get(level, [])
            for _ in range(min(quota, len(take))):
                if len(chosen) >= need:
                    break
                chosen.append(take.pop())
        # Fill any remainder from whatever eligible questions are left.
        remaining = [qid for qid in pool_ids if qid not in set(chosen)]
        rng.shuffle(remaining)
        while len(chosen) < need and remaining:
            chosen.append(remaining.pop())
        return chosen[:need]
