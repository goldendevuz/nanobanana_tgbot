"""Symmetric encryption for user-supplied content.

Prompts (and the images generated from them) are the user's private data: nobody
operating the CRM needs to read them, so they are encrypted before they ever reach
the database and are never decrypted for display. If we need to know what somebody
asked for, we ask them.
"""

import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__all__ = ["encrypt", "decrypt", "fingerprint", "is_encrypted", "InvalidToken"]

# Fernet tokens are urlsafe-base64 and always start with the 0x80 version byte.
TOKEN_PREFIX = "gAAAAA"


@lru_cache(maxsize=4)
def _build_fernet(key: str) -> Fernet:
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "PROMPT_ENCRYPTION_KEY is not a valid Fernet key. "
            "Generate one with: python manage.py generate_encryption_key"
        ) from exc


def _fernet() -> Fernet:
    key = settings.PROMPT_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured(
            "PROMPT_ENCRYPTION_KEY is not set — user prompts cannot be stored safely. "
            "Generate one with: python manage.py generate_encryption_key"
        )
    return _build_fernet(key)


def encrypt(text: str) -> str:
    """Encrypt plaintext. Empty values are stored as-is — there is nothing to hide."""
    if not text:
        return ""
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`."""
    if not token:
        return ""
    return _fernet().decrypt(token.encode()).decode()


def is_encrypted(value: str) -> bool:
    """Cheap check used by the migration to stay idempotent."""
    return bool(value) and value.startswith(TOKEN_PREFIX)


def fingerprint(text: str, length: int = 12) -> str:
    """Keyed digest of the plaintext.

    Lets staff tell two generations apart, or spot a repeated prompt, without
    learning the content. Keyed with HMAC so short prompts cannot be recovered
    from a dictionary of hashes.
    """
    if not text:
        return ""
    digest = hmac.new(
        settings.PROMPT_ENCRYPTION_KEY.encode(),
        text.encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest[:length]
