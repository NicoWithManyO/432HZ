"""Réglages communs à tous les environnements.

Secrets et options dépendantes de l'environnement sont lus via python-decouple
(fichier `.env`, jamais commité — voir `.env.example`). Les fichiers `dev.py` et
`prod.py` héritent d'ici et n'ajustent que ce qui change.
"""

from pathlib import Path

from csp.constants import NONE, SELF
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
    # Throttling des tentatives de connexion (cf section sécurité plus bas)
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # AxesMiddleware en dernier (a besoin de request.user résolu en amont).
    "axes.middleware.AxesMiddleware",
]


# Content-Security-Policy (django-csp). Posée par Django, pas par Nginx (cf DEPLOY-BRIEF).
# Inventaire du site : seul `main.js` (type=module, self) + du JSON-LD non exécutable, et
# TipTap minifié sans eval → `script-src 'self'` sans unsafe-* (la protection critique reste
# stricte). En revanche TipTap injecte sa feuille de style à l'exécution (<style> créé en JS,
# bloqué par `style-src 'self'`) → `style-src` autorise `'unsafe-inline'`. Risque résiduel
# négligeable : le contenu public est sanitizé par nh3 (aucun attribut `style` admis), donc
# aucune CSS contrôlée par un tiers ne peut atteindre les pages. Les embeds vidéo/adhésion
# sont en click-to-load → `frame-src` restreint aux hôtes attendus. Les aperçus d'upload
# (dropzone, URL.createObjectURL) produisent des `blob:` → `img-src` les autorise.
_CSP_DIRECTIVES = {
    "default-src": [SELF],
    "script-src": [SELF],
    "style-src": [SELF, "'unsafe-inline'"],
    "img-src": [SELF, "data:", "blob:"],
    "font-src": [SELF],
    "media-src": [SELF],
    "connect-src": [SELF],
    "frame-src": [
        SELF,
        "https://www.youtube-nocookie.com",
        "https://player.vimeo.com",
        "https://www.helloasso.com",
    ],
    "frame-ancestors": [NONE],
    "base-uri": [SELF],
    "form-action": [SELF],
    "object-src": [NONE],
}

# Bascule report-only (observer les violations sans bloquer) pilotée par env : django-csp
# 4.x lit deux réglages distincts selon le mode.
if config("DJANGO_CSP_REPORT_ONLY", default=False, cast=bool):
    CONTENT_SECURITY_POLICY_REPORT_ONLY = {"DIRECTIVES": _CSP_DIRECTIVES}
else:
    CONTENT_SECURITY_POLICY = {"DIRECTIVES": _CSP_DIRECTIVES}

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
                "apps.pages.context_processors.footer_social_links",
                "apps.pages.context_processors.nav_ctas",
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


# Rate-limiting (cf cahier §11). Deux outils complémentaires :
#  - django-axes : throttle les tentatives de connexion. Stockage en base (survit au
#    redémarrage, indépendant du nombre de workers gunicorn).
#  - django-ratelimit : protège l'acceptation d'invitation et les uploads. S'appuie sur le
#    CACHES ci-dessous (LocMemCache, mémoire de process) → garder `--workers 1` (cf
#    HANDOFF-DEVOPS.md). Désactivable en test via RATELIMIT_ENABLE (cf conftest.py).

AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend en tête : court-circuite l'auth si le couple est verrouillé.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # heure(s) avant déverrouillage automatique
# Verrou sur le couple (identifiant + IP) : ni DoS d'un compte par son seul nom, ni blocage
# de toute une IP partagée.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


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
