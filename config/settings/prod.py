"""Réglages de production.

Le durcissement complet (CSP, HSTS, cookies, rate-limiting) arrive en P5 ;
ici on pose le strict nécessaire pour tourner derrière Nginx en HTTPS.
"""

from decouple import Csv, config

from .base import *  # noqa: F403

DEBUG = False

# Secrets obligatoires en prod : pas de défaut, on échoue vite si le .env est incomplet.
SECRET_KEY = config("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

# Derrière Nginx (reverse-proxy HTTPS) : on fait confiance à l'en-tête de protocole.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
