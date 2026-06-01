"""Réglages communs à tous les environnements.

Secrets et options dépendantes de l'environnement sont lus via python-decouple
(fichier `.env`, jamais commité — voir `.env.example`). Les fichiers `dev.py` et
`prod.py` héritent d'ici et n'ajustent que ce qui change.
"""

from pathlib import Path

from decouple import config

# Racine du dépôt (config/settings/base.py -> remonte de 3 niveaux).
BASE_DIR = Path(__file__).resolve().parents[2]

# SECRET_KEY et ALLOWED_HOSTS relèvent de la politique de chaque environnement :
# définis dans dev.py (défaut permissif) et prod.py (obligatoires, sans défaut).

DEBUG = False


# Applications

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Apps métier
    "apps.common",
    "apps.accounts",
    "apps.media",
    "apps.events",
    "apps.news",
    "apps.pages",
    "apps.seo",
    # Présentation de l'admin convivial (namespace url `gestion`)
    "apps.gestion",
    # Vignettes WebP/srcset (médiathèque)
    "easy_thumbnails",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "apps.seo.context_processors.seo",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Base de données — SQLite en mode WAL (meilleure concurrence lecture/écriture).
# Django découpe `init_command` sur « ; » et l'exécute à chaque connexion (base de
# test incluse). `foreign_keys=ON` est déjà posé par le backend SQLite de Django.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": config("DJANGO_DB_PATH", default=BASE_DIR / "db.sqlite3"),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}


# Hachage des mots de passe — Argon2 en tête (cf cahier §9, sécurité).

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# Authentification — point d'entrée de la gestion (cf apps.gestion.urls).

LOGIN_URL = "gestion:login"
LOGIN_REDIRECT_URL = "gestion:dashboard"
LOGOUT_REDIRECT_URL = "gestion:login"


# Validation des mots de passe

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalisation — site francophone, fuseau France.

LANGUAGE_CODE = "fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# Fichiers statiques & médias

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Vignettes (easy-thumbnails) — sortie WebP partout (l'extension pilote le format
# de sauvegarde), recadrage centré sur le sujet. Les alias `card`/`card2x`
# alimentent le srcset de la grille médiathèque (1x / 2x).

THUMBNAIL_EXTENSION = "webp"
THUMBNAIL_ALIASES = {
    "": {
        "card": {"size": (320, 240), "crop": "smart"},
        "card2x": {"size": (640, 480), "crop": "smart"},
        # Image de partage Open Graph (ratio ~1.91:1 recommandé par les réseaux).
        "og": {"size": (1200, 630), "crop": "smart"},
    },
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
