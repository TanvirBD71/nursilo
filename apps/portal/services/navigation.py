"""Student navigation presentation — honest availability only (docs/11, docs/15)."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    href: str | None
    available: bool
    group: str  # primary | secondary | utility
    current: bool = False


class NavigationService:
    """
    Build student nav from implemented routes only.
    Unavailable domains link to an honest unavailable page — never fake features.
    """

    PRIMARY = (
        ("dashboard", "Dashboard", "portal:dashboard", True),
        ("learn", "Learn", "learning:catalog", True),
        ("practice", "Practice", "assessment:entry", True),
        ("exams", "Exams", "exams:catalog", True),
        ("library", "Library", "library:catalog", True),
        ("search", "Search", "portal:unavailable", False),
    )
    SECONDARY = (
        ("notifications", "Notifications", "portal:notifications", True),
        ("subscription", "Subscription", "billing:current", True),
        ("profile", "Profile", "portal:profile", True),
        ("security", "Security", "accounts:devices", True),
        ("settings", "Settings", "portal:settings", True),
    )

    @classmethod
    def items(cls, *, active: str | None = None) -> list[NavItem]:
        items: list[NavItem] = []
        for key, label, route_name, available in cls.PRIMARY:
            items.append(cls._item(key, label, route_name, available, "primary", active))
        for key, label, route_name, available in cls.SECONDARY:
            items.append(cls._item(key, label, route_name, available, "secondary", active))
        return items

    @classmethod
    def _item(
        cls,
        key: str,
        label: str,
        route_name: str,
        available: bool,
        group: str,
        active: str | None,
    ) -> NavItem:
        if available:
            href = reverse(route_name)
        else:
            href = reverse("portal:unavailable", kwargs={"feature": key})
        return NavItem(
            key=key,
            label=label,
            href=href,
            available=available,
            group=group,
            current=active == key,
        )
