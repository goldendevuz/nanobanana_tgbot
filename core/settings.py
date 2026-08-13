"""Django settings for the Nano Banana Telegram bot."""

from pathlib import Path

import dj_database_url
from decouple import Csv, config
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=config("CONN_MAX_AGE", default=60, cast=int),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in (
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    )
]

LANGUAGE_CODE = config("LANGUAGE_CODE", default="en-us")
TIME_ZONE = config("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "admin:index"
LOGOUT_REDIRECT_URL = "admin:login"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
}

# --------------------------------------------------------------------------- #
# Telegram bot / Kie.ai image generation
# --------------------------------------------------------------------------- #
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
ADMIN_USER_ID = config("ADMIN_USER_ID", default=0, cast=int)
BOT_ALLOW_EVERYONE = config("BOT_ALLOW_EVERYONE", default=False, cast=bool)
BOT_POLL_INTERVAL = config("BOT_POLL_INTERVAL", default=3, cast=int)

# Encrypts user prompts and result images at rest. Keep it out of version control and
# back it up separately — losing it makes existing prompts unreadable forever.
PROMPT_ENCRYPTION_KEY = config("PROMPT_ENCRYPTION_KEY", default="")

KIE_API_KEY = config("KIE_API_KEY", default="")
KIE_MODEL = config("KIE_MODEL", default="google/nano-banana")
KIE_CALLBACK_URL = config("CALLBACK_URL", default="https://example.com/api/callback")

# --------------------------------------------------------------------------- #
# Unfold admin UI
# --------------------------------------------------------------------------- #
UNFOLD = {
    "SITE_TITLE": "Nano Banana",
    "SITE_HEADER": "Nano Banana",
    "SITE_SUBHEADER": "Telegram image generation bot",
    "SITE_SYMBOL": "auto_awesome",
    "SITE_FAVICONS": [
        {"rel": "icon", "type": "image/svg+xml", "href": lambda request: static("favicon.svg")},
    ],
    "DASHBOARD_CALLBACK": "core.dashboard.dashboard_callback",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "THEME": None,  # user-switchable light/dark
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "254 252 232",
            "100": "254 249 195",
            "200": "254 240 138",
            "300": "253 224 71",
            "400": "250 204 21",
            "500": "234 179 8",
            "600": "202 138 4",
            "700": "161 98 7",
            "800": "133 77 14",
            "900": "113 63 18",
            "950": "66 32 6",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Overview",
                "separator": False,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": "Bot",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Telegram users",
                        "icon": "group",
                        "link": reverse_lazy("admin:bot_telegramuser_changelist"),
                    },
                    {
                        "title": "Generations",
                        "icon": "auto_awesome",
                        "link": reverse_lazy("admin:bot_generationtask_changelist"),
                    },
                ],
            },
            {
                "title": "Access",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Staff",
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "shield_person",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
