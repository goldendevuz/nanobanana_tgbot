from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a PROMPT_ENCRYPTION_KEY to put in .env."

    def handle(self, *args, **options):
        self.stdout.write(f"PROMPT_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
        self.stdout.write(
            self.style.WARNING(
                "Store this outside version control and back it up — without it, "
                "existing prompts cannot be decrypted."
            )
        )
