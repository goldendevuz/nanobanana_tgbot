import asyncio

from django.core.management.base import BaseCommand

from bot.services.telegram_bot import run


class Command(BaseCommand):
    help = "Run the Telegram bot (long polling)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Telegram bot…"))
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bot stopped."))
