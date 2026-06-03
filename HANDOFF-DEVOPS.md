# HANDOFF-DEVOPS — sécurité (P5)

Note pour le Claude devops, en complément du `DEPLOY-BRIEF.md`. Résume ce que la
phase **P5 (durcissement sécurité)** a posé côté app et ce que l'infra doit (ou ne
doit pas) faire en regard.

## 1. Taille des uploads

Le bloc média de l'accueil accepte des vidéos auto-hébergées jusqu'à **100 Mo**.
Nginx/Cloudflare doivent autoriser au moins autant :

```
client_max_body_size 100M;   # ≥ 100 Mo, sinon 413 sur l'upload vidéo
```

Côté Django, `DATA_UPLOAD_MAX_MEMORY_SIZE` n'a pas été relevé : il ne s'applique pas
aux fichiers uploadés (le vrai garde-fou est `client_max_body_size`).

## 2. En-têtes de sécurité — posés par Django, pas par l'infra

Django pose lui-même **CSP, HSTS, nosniff, Referrer-Policy, X-Frame-Options** et les
cookies `Secure`/`SameSite` (via `SECURE_*` en prod + `django-csp`). L'infra **ne doit
ni les dupliquer ni les stripper** :

- pas de second `Strict-Transport-Security` côté Nginx (double HSTS) ;
- pas d'`add_header Content-Security-Policy` côté Nginx (écraserait/dédoublerait la CSP).

La CSP autorise les iframes `frame-src` vers **youtube-nocookie.com**, **player.vimeo.com**
et **www.helloasso.com** (click-to-load vidéo + adhésion). Si un proxy filtre les en-têtes,
les laisser passer tels quels.

En cas de violation CSP inattendue en prod : passer `DJANGO_CSP_REPORT_ONLY=True` le
temps de diagnostiquer (ne bloque plus rien), corriger, repasser à `False`.

## 3. Rate-limiting — impact sur le déploiement

- **`django-axes`** (verrou login après 5 échecs) stocke en **base de données** :
  indépendant du nombre de workers, survit au restart. `migrate` crée ses tables
  (étape standard du déploiement).
- **`django-ratelimit`** (throttle invitation + uploads) s'appuie sur le **cache**, ici
  un **`LocMemCache`** (mémoire du process). Conséquence : il faut **garder un seul
  worker** (`gunicorn --workers 1`, déjà prévu au brief). Avec plusieurs workers, chaque
  process aurait son compteur → limites multipliées. Si un jour multi-worker devient
  nécessaire, basculer le cache sur `DatabaseCache` (SQLite, multi-worker-safe) — pas de
  Redis requis.

## 4. Configuration : python-decouple

On lit la config via **python-decouple** (pas `django-environ`). Le format `.env` est
identique (`CLÉ=valeur`, une par ligne). Nouvelles variables introduites en P5 (cf
`.env.example`) :

- `DJANGO_CSRF_TRUSTED_ORIGINS` — **à renseigner en prod** (origines HTTPS de confiance,
  schéma inclus, séparées par des virgules). Sans elle, le POST derrière proxy HTTPS peut
  échouer en 403 CSRF.
- `DJANGO_HSTS_SECONDS` — optionnel, défaut 1 an.
- `DJANGO_CSP_REPORT_ONLY` — optionnel, défaut `False`.

## 5. Hors périmètre P5 (phase deploy à venir)

Volontairement **non traités** ici, à livrer dans la phase deploy : whitenoise,
gunicorn, `MEDIA_ROOT` via env, split `requirements-prod.txt`, `.env.example` exhaustif
final, réponse complète aux livrables du `DEPLOY-BRIEF.md`. La présente note ne couvre
que la sécurité applicative.
