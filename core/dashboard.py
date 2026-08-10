"""Data for the Unfold admin dashboard."""

import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from bot.models import GenerationTask, TelegramUser

DAYS = 14


def _kpis() -> list[dict]:
    tasks = GenerationTask.objects.all()
    total = tasks.count()
    success = tasks.filter(state=GenerationTask.State.SUCCESS).count()
    failed = tasks.filter(state=GenerationTask.State.FAIL).count()
    pending = tasks.filter(state__in=GenerationTask.PENDING_STATES).count()
    users = TelegramUser.objects.count()
    allowed = TelegramUser.objects.filter(is_allowed=True, is_blocked=False).count()

    tasks_url = reverse("admin:bot_generationtask_changelist")
    users_url = reverse("admin:bot_telegramuser_changelist")

    return [
        {
            "title": "Generations",
            "value": total,
            "footer": f"{success} succeeded",
            "icon": "auto_awesome",
            "href": tasks_url,
        },
        {
            "title": "Success rate",
            "value": f"{(success / total * 100):.0f}%" if total else "—",
            "footer": f"{failed} failed",
            "icon": "trending_up",
            "href": f"{tasks_url}?state__exact=success",
        },
        {
            "title": "In progress",
            "value": pending,
            "footer": "waiting on Kie.ai",
            "icon": "hourglass_top",
            "href": f"{tasks_url}?state__exact=generating",
        },
        {
            "title": "Telegram users",
            "value": users,
            "footer": f"{allowed} with access",
            "icon": "group",
            "href": users_url,
        },
    ]


def _chart() -> str:
    since = timezone.now() - timedelta(days=DAYS - 1)
    rows = (
        GenerationTask.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day", "state")
        .annotate(total=Count("id"))
    )

    buckets: dict = {}
    for row in rows:
        day = buckets.setdefault(row["day"], {"success": 0, "other": 0})
        key = "success" if row["state"] == GenerationTask.State.SUCCESS else "other"
        day[key] += row["total"]

    today = timezone.localdate()
    days = [today - timedelta(days=offset) for offset in range(DAYS - 1, -1, -1)]

    return json.dumps(
        {
            "labels": [day.strftime("%d %b") for day in days],
            "datasets": [
                {
                    "label": "Success",
                    "data": [buckets.get(day, {}).get("success", 0) for day in days],
                    "backgroundColor": "#eab308",
                    "borderRadius": 4,
                },
                {
                    "label": "Other",
                    "data": [buckets.get(day, {}).get("other", 0) for day in days],
                    "backgroundColor": "#d4d4d8",
                    "borderRadius": 4,
                },
            ],
        }
    )


def dashboard_callback(request, context: dict) -> dict:
    context.update(
        {
            "kpis": _kpis(),
            "chart_data": _chart(),
            "recent_tasks": (
                GenerationTask.objects.select_related("user").order_by("-created_at")[:8]
            ),
        }
    )
    return context
