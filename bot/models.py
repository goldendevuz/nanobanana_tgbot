from django.db import models
from django.utils import timezone


class TelegramUser(models.Model):
    """A Telegram account that has interacted with the bot."""

    telegram_id = models.BigIntegerField("Telegram ID", unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    language_code = models.CharField(max_length=16, blank=True)
    is_allowed = models.BooleanField(
        "Allowed",
        default=False,
        help_text="Only allowed users can generate images.",
    )
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Telegram user"
        verbose_name_plural = "Telegram users"
        ordering = ("-last_seen_at",)

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or str(self.telegram_id)


class GenerationTask(models.Model):
    """One image generation job submitted to the Kie.ai API."""

    class State(models.TextChoices):
        WAITING = "waiting", "Waiting"
        QUEUING = "queuing", "Queuing"
        GENERATING = "generating", "Generating"
        SUCCESS = "success", "Success"
        FAIL = "fail", "Failed"

    PENDING_STATES = (State.WAITING, State.QUEUING, State.GENERATING)

    task_id = models.CharField(max_length=128, unique=True, db_index=True)
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    chat_id = models.BigIntegerField()
    prompt = models.TextField()
    image_size = models.CharField(max_length=16, default="1:1")
    model = models.CharField(max_length=64, blank=True)
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.WAITING,
        db_index=True,
    )
    result_url = models.URLField(max_length=1024, blank=True)
    fail_message = models.TextField(blank=True)
    delivered = models.BooleanField(
        default=False,
        help_text="The result has been sent back to the Telegram chat.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Generation"
        verbose_name_plural = "Generations"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("state", "delivered"))]

    def __str__(self) -> str:
        return f"{self.task_id} — {self.short_prompt}"

    @property
    def short_prompt(self) -> str:
        return self.prompt if len(self.prompt) <= 60 else f"{self.prompt[:57]}…"

    @property
    def is_pending(self) -> bool:
        return self.state in self.PENDING_STATES

    @property
    def duration(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.created_at).total_seconds()
