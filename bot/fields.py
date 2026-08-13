"""Model fields that keep their value encrypted at rest."""

import logging

from django.core.exceptions import FieldError
from django.db import models

from bot.crypto import InvalidToken, decrypt, encrypt

logger = logging.getLogger(__name__)

UNREADABLE = ""


class EncryptedTextField(models.TextField):
    """A TextField whose database column holds ciphertext.

    Values are encrypted on the way in and decrypted on the way out, so calling code
    keeps working with plain strings. Lookups are refused rather than silently
    returning nothing: Fernet tokens are non-deterministic, so ``filter(prompt=...)``
    could never match and would quietly hide rows.
    """

    description = "Text stored encrypted at rest"

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return decrypt(value)
        except InvalidToken:
            # A row written before encryption was enabled, or with a rotated key.
            logger.warning("Could not decrypt %s value — returning empty", self.name)
            return UNREADABLE

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return encrypt(value)

    def get_lookup(self, lookup_name):
        if lookup_name != "isnull":
            raise FieldError(
                f"'{self.name}' is encrypted and cannot be filtered on "
                f"(tried '{lookup_name}'). Query by task_id or fingerprint instead."
            )
        return super().get_lookup(lookup_name)
