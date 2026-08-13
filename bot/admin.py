from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
)
from unfold.decorators import display

from bot.i18n import LANGUAGE_NAMES
from bot.models import GenerationTask, TelegramUser

# Restyle the built-in auth admin with Unfold.
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    pass


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class GenerationTaskInline(TabularInline):
    model = GenerationTask
    extra = 0
    can_delete = False
    fields = ("task_id", "short_prompt", "state", "created_at")
    readonly_fields = fields
    ordering = ("-created_at",)
    max_num = 0
    tab = True

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(TelegramUser)
class TelegramUserAdmin(ModelAdmin):
    list_display = (
        "user_header",
        "telegram_id",
        "language_badge",
        "access_badge",
        "total_tasks",
        "last_seen_at",
    )
    list_filter = (
        ("language", ChoicesDropdownFilter),
        ("is_allowed", BooleanRadioFilter),
        ("is_blocked", BooleanRadioFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("telegram_id", "username", "first_name", "last_name")
    readonly_fields = ("telegram_id", "created_at", "last_seen_at")
    list_per_page = 25
    inlines = (GenerationTaskInline,)
    actions = ("allow_users", "block_users")
    fieldsets = (
        ("Identity", {"fields": ("telegram_id", "username", "first_name", "last_name")}),
        ("Language", {"fields": ("language", "language_code")}),
        ("Access", {"fields": ("is_allowed", "is_blocked")}),
        ("Timestamps", {"fields": ("created_at", "last_seen_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(task_count=Count("tasks"))

    @display(description="User", header=True, ordering="username")
    def user_header(self, obj: TelegramUser):
        subtitle = f"{obj.first_name} {obj.last_name}".strip() or "—"
        initials = (obj.first_name[:1] or obj.username[:1] or "?").upper()
        return obj.display_name, subtitle, initials

    @display(
        description="Access",
        ordering="is_allowed",
        label={"Allowed": "success", "Blocked": "danger", "Pending": "warning"},
    )
    def access_badge(self, obj: TelegramUser) -> str:
        if obj.is_blocked:
            return "Blocked"
        return "Allowed" if obj.is_allowed else "Pending"

    @display(description="Language", ordering="language")
    def language_badge(self, obj: TelegramUser) -> str:
        return LANGUAGE_NAMES.get(obj.language, obj.get_language_display())

    @display(description="Generations", ordering="task_count")
    def total_tasks(self, obj: TelegramUser) -> int:
        return getattr(obj, "task_count", obj.tasks.count())

    @admin.action(description="Grant access")
    def allow_users(self, request, queryset):
        updated = queryset.update(is_allowed=True, is_blocked=False)
        self.message_user(request, f"{updated} user(s) granted access.")

    @admin.action(description="Block")
    def block_users(self, request, queryset):
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f"{updated} user(s) blocked.")


@admin.register(GenerationTask)
class GenerationTaskAdmin(ModelAdmin):
    list_display = ("prompt_header", "state_badge", "user", "preview", "took", "created_at")
    list_filter = (
        ("state", ChoicesDropdownFilter),
        ("delivered", BooleanRadioFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("task_id", "prompt", "user__username", "user__telegram_id")
    autocomplete_fields = ("user",)
    date_hierarchy = "created_at"
    list_per_page = 25
    readonly_fields = (
        "task_id",
        "chat_id",
        "model",
        "result_url",
        "image_preview",
        "created_at",
        "updated_at",
        "finished_at",
    )
    fieldsets = (
        ("Request", {"fields": ("task_id", "user", "chat_id", "prompt", "image_size", "model")}),
        ("Result", {"fields": ("state", "result_url", "image_preview", "fail_message", "delivered")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at", "finished_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request) -> bool:
        return False

    @display(description="Prompt", header=True, ordering="prompt")
    def prompt_header(self, obj: GenerationTask):
        return obj.short_prompt, obj.task_id

    @display(
        description="State",
        ordering="state",
        label={
            "Waiting": "info",
            "Queuing": "info",
            "Generating": "warning",
            "Success": "success",
            "Failed": "danger",
        },
    )
    def state_badge(self, obj: GenerationTask) -> str:
        return obj.get_state_display()

    @display(description="Image")
    def preview(self, obj: GenerationTask):
        if not obj.result_url:
            return "—"
        return format_html(
            '<img src="{}" style="height:40px;width:40px;border-radius:6px;object-fit:cover" />',
            obj.result_url,
        )

    @display(description="Preview")
    def image_preview(self, obj: GenerationTask):
        if not obj.result_url:
            return "—"
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" style="max-width:420px;border-radius:8px" /></a>',
            obj.result_url,
        )

    @display(description="Took", ordering="finished_at")
    def took(self, obj: GenerationTask) -> str:
        seconds = obj.duration
        return f"{seconds:.0f}s" if seconds is not None else "—"
