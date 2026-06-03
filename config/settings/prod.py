"""Réglages de production.

Durcissement sécurité (P5) : en-têtes HSTS/nosniff/referrer, cookies, CSRF de confiance.
La CSP et le rate-limiting sont posés dans `base.py` (actifs aussi en dev pour être testés).
"""

from decouple import Csv, config

from .base import *  # noqa: F403
from .base import MIDDLEWARE

DEBUG = False

# WhiteNoise sert les statiques en prod : inséré juste après SecurityMiddleware (ordre requis).
# Absent en dev/test (runserver s'en charge) pour ne pas charger un middleware inerte.
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

# Secrets obligatoires en prod : pas de défaut, on échoue vite si le .env est incomplet.
SECRET_KEY = config("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

# Derrière Nginx (reverse-proxy HTTPS) : on fait confiance à l'en-tête de protocole.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS : force HTTPS côté navigateur. Durée pilotable par env pour permettre une montée
# progressive (commencer bas, puis 1 an). includeSubDomains + preload visent l'éligibilité
# à la liste de préchargement des navigateurs.
SECURE_HSTS_SECONDS = config("DJANGO_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# En-têtes de sécurité applicatifs (posés par Django, pas par Nginx — cf DEPLOY-BRIEF).
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"  # doublé par la CSP `frame-ancestors 'none'`

# Origines de confiance pour le CSRF (schéma https:// inclus, ex. https://432hz.manyo.dev).
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Cookies : SameSite=Lax explicite. HttpOnly de session laissé à True (défaut) ; le cookie
# CSRF reste lisible par le JS (l'upload AJAX en a besoin) → pas de CSRF_COOKIE_HTTPONLY.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Service des statiques par WhiteNoise : noms hashés (cache long) + compression. Manifest en
# prod seulement — en dev le storage par défaut évite d'imposer un `collectstatic` pour
# résoudre `{% static %}`. `collectstatic` doit tourner après le build Tailwind (cf handoff).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
