# Handoff déploiement — 432 Hz

Réponse au `DEPLOY-BRIEF.md` (point par point), pour le Claude devops.
Les détails **sécurité applicative** (CSP, HSTS, rate-limiting, ré-encodage image) sont
dans `HANDOFF-DEVOPS.md` — non répétés ici.

> ✅ **App prête pour le déploiement.** Les items deploy-readiness (gunicorn, whitenoise,
> `MEDIA_ROOT` par env, logging) ont été livrés. Reste un seul écart **volontaire** :
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
| 5 — gunicorn | dep prod + `--workers 1` | ✅ | `gunicorn==26.0.0`. WSGI = `config.wsgi:application`. `--workers 1` **obligatoire** (LocMemCache, cf HANDOFF-DEVOPS §3). |
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
   ⚠️ Le dernier commit (`35bf823`, P5 + ce handoff) **n'est pas encore poussé** —
   Nico pousse manuellement ; vérifier que `origin/DEV` est à jour avant le deploy.
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
   (MP4/WebM). → `client_max_body_size ≥ 100M` (cf HANDOFF-DEVOPS §1) et `MEDIA_ROOT`
   hors repo à provisionner.

---

## Rappels infra (détail dans `HANDOFF-DEVOPS.md`)

- **En-têtes / CSP / HSTS posés par Django** — ne pas dupliquer ni stripper côté Nginx.
- **`--workers 1`** (rate-limit `django-ratelimit` sur LocMemCache mémoire de process).
- **python-decouple** (pas django-environ) ; format `.env` identique.
