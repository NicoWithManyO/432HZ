# Handoff déploiement — 432 Hz

Point d'entrée unique pour le Claude devops. Réponse au `DEPLOY-BRIEF.md` (point par
point) + rappels d'infra liés à la sécurité applicative (P5).

> ✅ **App prête pour le déploiement.** Les items deploy-readiness (gunicorn, whitenoise,
> `MEDIA_ROOT` par env, logging) sont livrés. Reste un seul écart **volontaire** :
> python-decouple au lieu de django-environ (même format `.env`). Détail dans le tableau.

---

## État de conformité au brief

| § brief | Attendu | État | Note |
|--------|---------|------|------|
| 1 — config par env | `django-environ` | ⚠️ écart | On utilise **python-decouple** (même format `.env`, `CLÉ=valeur`). Équivalent fonctionnel, pas de réécriture prévue. |
| 1 — `.env.example` exhaustif | toutes les clés | ✅ | Toutes les vars listées (dont `DJANGO_MEDIA_ROOT`). |
| 2 — SQLite, chemin par env | var `SQLITE_PATH` | ✅ (nom différent) | La var s'appelle **`DJANGO_DB_PATH`** (défaut `BASE_DIR/db.sqlite3`). Préfixe `DJANGO_` **volontaire** (cohérent avec `DJANGO_SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`) ; le `.env.example` fait foi comme contrat. |
| 2 — `MEDIA_ROOT` par env | lu depuis env | ✅ | Var **`DJANGO_MEDIA_ROOT`** (défaut `BASE_DIR/media`). À pointer hors repo en prod. |
| 2 — aucun `.sqlite3` commité, migrations clean | — | ✅ | `.gitignore` couvre `*.sqlite3` (+WAL/SHM) ; `makemigrations --check` clean. |
| 3 — whitenoise | dep + middleware + STORAGES | ✅ | `whitenoise==6.12.0` ; middleware inséré après `SecurityMiddleware` **en prod** ; `STORAGES` = `CompressedManifestStaticFilesStorage` (prod). `collectstatic` validé. |
| 4 — proxy SSL / cookies secure | via env, prod | ✅ | `prod.py` : `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SESSION/CSRF_COOKIE_SECURE`. |
| 4 — logging stdout/stderr | dict LOGGING | ✅ | `LOGGING` avec `StreamHandler` (console), pas de FileHandler. |
| 5 — gunicorn | dep prod + `--workers 1` | ✅ | `gunicorn==26.0.0`. WSGI = `config.wsgi:application`. `--workers 1` **obligatoire** (LocMemCache, cf §Rappels infra). |
| 6 — requirements épinglés | `==` | ✅ | Tout épinglé, gunicorn + whitenoise inclus. |
| 7 — Tailwind | signaler le build | ✅ signalé | Pipeline **Node standalone** (pas django-tailwind). CSS/JS compilés **non commités** → build requis au deploy (voir §9.5). |
| 8 — branche DEV, `.gitignore` | — | ✅ | `.gitignore` exhaustif (`.env`, `*.sqlite3`, `.venv/`, `staticfiles/`, `media/`, `node_modules/`, compilés). |

---

## Deploy-prep livrée (côté app)

Tous les items deploy-readiness sont en place :

- `gunicorn==26.0.0` + `whitenoise==6.12.0` dans `requirements.txt`.
- WhiteNoise : middleware après `SecurityMiddleware` (prod) + `STORAGES`
  `CompressedManifestStaticFilesStorage` (prod). `collectstatic --noinput` validé
  (149 fichiers, 419 post-traités, manifest généré).
- `MEDIA_ROOT` via `DJANGO_MEDIA_ROOT` (défaut `./media`).
- `LOGGING` → `StreamHandler` (stdout/stderr), aucun FileHandler.
- `.env.example` complété (`DJANGO_MEDIA_ROOT`).

Vérifs : 241 tests verts, `ruff` clean, `makemigrations --check` clean, `check --deploy` 0 issue.

---

## §9 — Livrables demandés par le brief

1. **Nom du projet** : repo `432HZ`. ⚠️ Le slug commence par un chiffre — pour les
   identifiants systemd / `/srv/<project>`, choisir un nom sans chiffre en tête
   (proposition : **`asso432hz`**, à valider).
2. **Repo + branche** : `git@github.com:NicoWithManyO/432HZ.git`, branche **`DEV`**.
   `origin/DEV` est à jour (Nico pousse manuellement ; tout est synchronisé).
3. **`.env.example`** : présent à la racine, complet (contrat des vars) — `DJANGO_SECRET_KEY`,
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_DB_PATH`, `DJANGO_MEDIA_ROOT`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
   `DJANGO_HSTS_SECONDS`, `DJANGO_CSP_REPORT_ONLY`.
4. **Domaine(s) cible** en `*.manyo.dev` : **à renseigner par Nico** (inconnu côté dev).
5. **Commandes post-deploy non standard** (au-delà de `migrate` + `collectstatic`) :
   - **Build Tailwind AVANT `collectstatic`** : `npm ci && npm run build` (génère
     `static/css/app.css`, `static/js/gestion-editor.js`, fonts — tous non commités).
     Node requis sur le builder.
   - **`python manage.py bootstrap_owner --username <u> --email <e>`** : crée le 1er
     compte owner (pas d'inscription ouverte). À lancer une fois, après `migrate`.
   - `migrate` crée aussi les tables **django-axes**.
6. **Uploads média** : **OUI**. Images ≤ **8 Mo** (JPEG/PNG/WEBP), vidéos ≤ **100 Mo**
   (MP4/WebM). → `client_max_body_size ≥ 100M` (cf §Rappels infra) et `MEDIA_ROOT`
   hors repo à provisionner.

---

## Rappels infra (sécurité applicative posée en P5)

### 1. Taille des uploads

Le bloc média de l'accueil accepte des vidéos auto-hébergées jusqu'à **100 Mo** :

```
client_max_body_size 100M;   # ≥ 100 Mo, sinon 413 sur l'upload vidéo
```

Côté Django, `DATA_UPLOAD_MAX_MEMORY_SIZE` n'a pas été relevé : il ne s'applique pas
aux fichiers uploadés (le vrai garde-fou est `client_max_body_size`).

### 2. En-têtes de sécurité — posés par Django, pas par l'infra

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

### 3. Rate-limiting — impact sur le déploiement

- **`django-axes`** (verrou login après 5 échecs) stocke en **base de données** :
  indépendant du nombre de workers, survit au restart. `migrate` crée ses tables.
- **`django-ratelimit`** (throttle invitation + uploads) s'appuie sur un **`LocMemCache`**
  (mémoire du process). Conséquence : **garder un seul worker** (`gunicorn --workers 1`).
  Avec plusieurs workers, chaque process aurait son compteur → limites multipliées. Si un
  jour multi-worker devient nécessaire, basculer le cache sur `DatabaseCache` (SQLite,
  multi-worker-safe) — pas de Redis requis.

### 4. Configuration : python-decouple

On lit la config via **python-decouple** (pas `django-environ`). Format `.env` identique
(`CLÉ=valeur`). Variables sécurité (cf `.env.example`) :

- `DJANGO_CSRF_TRUSTED_ORIGINS` — **à renseigner en prod** (origines HTTPS de confiance,
  schéma inclus, séparées par des virgules). Sans elle, le POST derrière proxy HTTPS peut
  échouer en 403 CSRF.
- `DJANGO_HSTS_SECONDS` — optionnel, défaut 1 an.
- `DJANGO_CSP_REPORT_ONLY` — optionnel, défaut `False`.
