# Handoff déploiement — 432 Hz

Réponse au `DEPLOY-BRIEF.md` (point par point), pour le Claude devops.
Les détails **sécurité applicative** (CSP, HSTS, rate-limiting, ré-encodage image) sont
dans `HANDOFF-DEVOPS.md` — non répétés ici.

> ⚠️ **L'app n'est pas encore 100 % conforme au brief.** Des items deploy-readiness ont
> été volontairement reportés (phase P5 = sécu pure). Ils sont **côté app** (settings/deps)
> et restent donc à faire **par le dev applicatif**, pas par l'infra (cf brief : « le
> déploiement ne touche NI `settings.py` NI aucune config Django »). Voir la section
> « À finir côté app » ci-dessous.

---

## État de conformité au brief

| § brief | Attendu | État | Note |
|--------|---------|------|------|
| 1 — config par env | `django-environ` | ⚠️ écart | On utilise **python-decouple** (même format `.env`, `CLÉ=valeur`). Équivalent fonctionnel, pas de réécriture prévue. |
| 1 — `.env.example` exhaustif | toutes les clés | ⚠️ à compléter | À enrichir quand `MEDIA_ROOT`/whitenoise seront câblés (voir ci-dessous). |
| 2 — SQLite, chemin par env | var `SQLITE_PATH` | ✅ (nom différent) | La var s'appelle **`DJANGO_DB_PATH`** (défaut `BASE_DIR/db.sqlite3`). Préfixe `DJANGO_` **volontaire** (cohérent avec `DJANGO_SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`) ; le `.env.example` fait foi comme contrat. |
| 2 — `MEDIA_ROOT` par env | lu depuis env | ❌ pas fait | En dur `BASE_DIR/media`. À passer en env (sinon médias dans le repo → risque au `git reset --hard`). |
| 2 — aucun `.sqlite3` commité, migrations clean | — | ✅ | `.gitignore` couvre `*.sqlite3` (+WAL/SHM) ; `makemigrations --check` clean. |
| 3 — whitenoise | dep + middleware + STORAGES | ❌ pas fait | Absent partout. Statique non servi en prod tant que non câblé (ou servi par Nginx). |
| 4 — proxy SSL / cookies secure | via env, prod | ✅ | `prod.py` : `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SESSION/CSRF_COOKIE_SECURE`. |
| 4 — logging stdout/stderr | dict LOGGING | ❌ pas fait | Aucune config `LOGGING`. À ajouter (StreamHandler, pas de FileHandler). |
| 5 — gunicorn | dep prod + `--workers 1` | ⚠️ partiel | gunicorn **absent** de `requirements.txt`. WSGI OK (`config.wsgi:application`). `--workers 1` **obligatoire** (LocMemCache, cf HANDOFF-DEVOPS §3). |
| 6 — requirements épinglés | `==` | ✅ (incomplet) | Tout épinglé, mais **gunicorn + whitenoise manquent**. |
| 7 — Tailwind | signaler le build | ✅ signalé | Pipeline **Node standalone** (pas django-tailwind). CSS/JS compilés **non commités** → build requis au deploy (voir §9.5). |
| 8 — branche DEV, `.gitignore` | — | ✅ | `.gitignore` exhaustif (`.env`, `*.sqlite3`, `.venv/`, `staticfiles/`, `media/`, `node_modules/`, compilés). |

---

## À finir côté app AVANT un deploy fonctionnel

Ces points sont **bloquants** et relèvent de l'app (le devops ne les corrigera pas) :

1. **gunicorn + whitenoise** dans `requirements.txt`.
2. **whitenoise** : middleware juste après `SecurityMiddleware` + `STORAGES` (`CompressedManifestStaticFilesStorage`, prod uniquement pour ne pas casser le dev).
3. **`MEDIA_ROOT`** lu depuis l'env (le devops le pointe hors repo).
4. **`LOGGING`** : dict avec `StreamHandler` vers stdout/stderr.
5. **`.env.example`** mis à jour avec les nouvelles vars (MEDIA_ROOT).

> Tant que ce n'est pas livré, le déploiement échouera (pas de serveur d'app, statiques non
> servis, médias dans le repo). À traiter dans une courte itération « deploy-prep » côté app.

---

## §9 — Livrables demandés par le brief

1. **Nom du projet** : repo `432HZ`. ⚠️ Le slug commence par un chiffre — pour les
   identifiants systemd / `/srv/<project>`, choisir un nom sans chiffre en tête
   (proposition : **`asso432hz`**, à valider).
2. **Repo + branche** : `git@github.com:NicoWithManyO/432HZ.git`, branche **`DEV`**.
   ⚠️ Le dernier commit (`35bf823`, P5 + ce handoff) **n'est pas encore poussé** —
   Nico pousse manuellement ; vérifier que `origin/DEV` est à jour avant le deploy.
3. **`.env.example`** : présent à la racine (contrat des vars). À recompléter après les
   items « à finir côté app » (SQLITE_PATH, MEDIA_ROOT).
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
