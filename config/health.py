"""Minimal health endpoint — no secrets, debug, or filesystem paths."""
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})
