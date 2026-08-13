from django.db import models
from django.utils import timezone

from bot.crypto import fingerprint
from bot.fields import EncryptedTextField
from bot.i18n import DEFAULT_LANGUAGE


class TelegramUser(models.Model):
    """A Telegram account that has interacted with the bot."""

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha"
        RU = "ru", "Русский"
        EN = "en", "English"

    telegram_id = models.BigIntegerField("Telegram ID", unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    language = models.CharField(
        "Bot language",
        max_length=2,
        choices=Language.choices,
        default=DEFAULT_LANGUAGE,
        help_text="Language the bot replies in.",
    )
    language_code = models.CharField(
        "Telegram locale",
        max_length=16,
        blank=True,
        help_text="Raw locale reported by the Telegram client.",
    )
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
    # Private user content — encrypted at rest, never rendered in the admin.
    prompt = EncryptedTextField()
    prompt_fingerprint = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Keyed digest of the prompt — identifies a repeated prompt without revealing it.",
    )
    prompt_length = models.PositiveIntegerField(default=0)
    image_size = models.CharField(max_length=16, default="1:1")
    model = models.CharField(max_length=64, blank=True)
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.WAITING,
        db_index=True,
    )
    # The generated image shows exactly what was asked for, so it is protected too.
    result_url = EncryptedTextField(blank=True)
    fail_message = models.TextField(blank=True)
    delivered = models.BooleanField(
        default=False,
        help_text="The result has been sent back to the Telegram chat.",
    )
    cleanup_message_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Interim chat messages to delete once the result is delivered. "
        "Stored on the task so a restart still tidies the chat.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Generation"
        verbose_name_plural = "Generations"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("state", "delivered"))]

    def save(self, *args, **kwargs):
        # Keep the non-revealing metadata in step with the prompt.
        self.prompt_length = len(self.prompt or "")
        self.prompt_fingerprint = fingerprint(self.prompt or "")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        # Never include the prompt: __str__ is written verbatim into django_admin_log.
        return f"{self.task_id} ({self.prompt_length} chars)"

    @property
    def masked_prompt(self) -> str:
        """What staff see instead of the prompt."""
        return f"🔒 {self.prompt_length} chars · {self.prompt_fingerprint or '—'}"

    @property
    def is_pending(self) -> bool:
        return self.state in self.PENDING_STATES

    @property
    def duration(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.created_at).total_seconds()
