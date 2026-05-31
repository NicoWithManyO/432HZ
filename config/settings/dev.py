"""Réglages de développement local."""

from decouple import Csv, config

from .base import *  # noqa: F403

DEBUG = True

# Défaut insecure pour un démarrage zéro-config (clone frais, CI) — JAMAIS en prod.
SECRET_KEY = config("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# Emails affichés dans la console (l'envoi réel est en phase 2).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
