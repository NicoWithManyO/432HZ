# Cahier des charges — Site 432 Hz (v2, reset)

> Refonte **repartie de zéro** du site de l'association culturelle **432 Hz** (Annecy).
> On **garde la charte graphique** (`DESIGN.md` + `design/` + `reference/maquette-accueil.html`).
> On **abandonne** l'ancienne architecture headless et le moteur de blocs : les pages sont
> désormais **fixes** (codées en dur), et les admins postent **events** et **actus** via une
> interface conviviale.
>
> Ce document est le point de départ pour reconstruire le projet dans une nouvelle session.
> Sources liées : `DESIGN.md` (visuel, fait foi), `CONVENTIONS.md` (code/tests/git), `design/`
> (fichiers prêts), `reference/` (maquette HTML + logo).

---

## 1. Contexte & objectif

L'association fait du **spectacle vivant** (concerts, performances, fêtes de quartier) et porte une
mission **éducative & préventive**. Le site doit être chaleureux, vivant, communautaire — une
**affiche culturelle imprimée** en ligne (cf `DESIGN.md §0`).

Objectif v2 : un site **simple à maintenir** où :
- les **pages de présentation** (accueil, asso, adhérer, contact) sont fixes ;
- les **events** et **actus** sont créés/édités/publiés par les admins dans une **interface
  conviviale** (formulaires clairs, pas de composition de blocs) ;
- le **public** consulte l'agenda, les actus et leurs pages détail, avec un **SEO** soigné.

**Pourquoi ce reset** : l'ancienne v1 (Django+DRF headless + React SSR + moteur de blocs partagé +
pages en arbre + draft/publish/historique partout) était surdimensionnée pour le besoin réel. On
vise désormais le **strict nécessaire**, en monolithe Django.

---

## 2. Périmètre

### Dans le périmètre (v1 de la v2)
- **Pages publiques fixes** : Accueil, Agenda (liste + détail event), Actus (liste + détail actu),
  L'asso, Adhérer (HelloAsso), Contact / Mentions légales / Confidentialité, 404.
- **Gestion admin conviviale** : CRUD events + actus avec **bascule Brouillon / Publié**, upload
  d'images (cover + galerie), description en **texte riche léger**.
- **Médiathèque** simple (upload, réutilisation d'images).
- **Auth sur invitation par token**, rôles **owner / éditeur**, **verrou d'édition** (confort).
- **SEO** (head par page, JSON-LD Event/Organization, sitemap, robots).
- **RGPD** (click-to-load tiers, analytics sans cookie Plausible, pages légales).
- **Sécurité** (Argon2, CSP, rate-limiting, validation upload).
- **Déploiement** VPS (Nginx + Gunicorn, HTTPS), **backups** SQLite + médias.

### Hors périmètre (explicitement abandonné ou repoussé)
- ❌ **Moteur de blocs** / composition de pages / pages en arbre parent-enfant.
- ❌ **Front React / SSR / SPA** : tout est rendu par Django (templates).
- ❌ **API publique DRF** : inutile en monolithe (vues Django classiques).
- ❌ **Draft/publish riche + historique des versions + restauration** : remplacé par une simple
  bascule de statut.
- 🔜 **Phase 2** : email (SMTP/Brevo → notifications, reset self-service, formulaire de contact
  envoyé), inscription aux events, espace membre, recherche, newsletter, stockage objet S3.

---

## 3. Décisions structurantes (verrouillées)

| Sujet | Décision |
|---|---|
| **Architecture** | **Monolithe Django** : templates Django + Tailwind, JS vanilla minimal. 1 process applicatif. |
| **Base de données** | **SQLite partout**, même en prod (**mode WAL**). Backup = `sqlite3.backup()` + copie des médias. |
| **Pages** | **Fixes**, codées en templates. Pas de CMS de pages. |
| **Workflow events/actus** | **Bascule `draft` / `published`** (champ `status`). Pas d'historique. |
| **Auth** | **Invitation par token**, rôles **owner / éditeur**, **verrou d'édition** pessimiste. Sessions Django + CSRF. Argon2. |
| **Texte riche** | Description event/actu = HTML léger **sanitizé serveur** (`nh3`), allowlist restreinte. Éditeur convivial minimal côté admin. |
| **Images** | `ImageField` + vignettes **WebP/srcset** (`easy-thumbnails`), validation réelle (Pillow), ré-encodage, noms aléatoires. |
| **SEO / RGPD** | En v1 : head par page, JSON-LD, sitemap/robots ; click-to-load tiers, **Plausible**, pages légales. |
| **Langue** | Code **anglais**, commentaires **français**, commits **100 % français**, UI publique en français (tutoiement inclusif). |
| **Git** | Dev sur **`DEV`**, merge sur **`PROD`** à la mise en prod. **Jamais de push** par l'assistant. Pas de mention d'IA dans les commits. |

---

## 4. Stack technique

**Backend / app**
- **Python 3.13**, **Django 5.2 LTS**.
- **SQLite** (WAL) — `PRAGMA journal_mode=WAL`.
- Settings découpés par env : `config/settings/{base,dev,prod}.py`, secrets via **python-decouple**
  (`.env`, jamais commité ; `.env.example` fourni).
- **Pillow** + **easy-thumbnails** (vignettes WebP/srcset).
- **nh3** (sanitize HTML du texte riche).
- **argon2-cffi** (`PASSWORD_HASHERS`).
- **django-ratelimit** (login, accept-invite, upload).
- **django-csp** (CSP stricte).
- Dépendances **figées** dans `requirements.txt`.

**Front (servi par Django)**
- Templates Django + **Tailwind CSS** (CLI standalone ou npm) → `static/css/app.css`.
- Tokens & styles fournis : `design/tokens.css`, `design/globals.css`, `design/tailwind.config.js`.
- **JS vanilla minimal** : `Waveform` (`design/waveform.js`), menu mobile, reveals au scroll, ticker,
  click-to-load. Pas de framework.
- **Éditeur de texte riche admin** : **Tiptap** (ProseMirror) monté en **îlot JS** sur le champ
  `description` des formulaires events/actus (toolbar : gras/italique/lien/listes/h2-h3). Le HTML
  produit est **toujours re-sanitizé serveur** (`nh3`) avant enregistrement. Bundlé via le petit build
  front (Vite/esbuild léger, uniquement pour cet îlot + Tailwind).
- Polices **self-hosted** (`static/fonts/`, `@font-face`) — Fraunces, Archivo, Space Mono.

**Ops**
- **Gunicorn** derrière **Nginx**, **HTTPS** Let's Encrypt (certbot).
- **Plausible** (analytics sans cookie).
- Sentry optionnel (back) en P-ops.

> Un petit `package.json` sert à compiler **Tailwind** + bundler l'**îlot Tiptap** (et éventuellement
> `@fontsource`). C'est la seule dépendance JS du projet, cantonnée à l'admin (l'îlot riche n'est pas
> chargé côté public). Build léger (Vite ou esbuild). Le reste du JS reste vanilla.

---

## 5. Modèle de données

> UUID en clé primaire partout (pas d'IDs séquentiels exposés). `slug` unique, dérivé du titre à la
> création, **stable** ensuite (si on change un slug → prévoir une redirection 301, cf §8).

### `media.Image`
| Champ | Type | Notes |
|---|---|---|
| `id` | UUID pk | |
| `file` | ImageField | `upload_to="images/%Y/%m/"` |
| `alt` | Char(200), blank | texte alternatif |
| `title` | Char(200), blank | titre interne médiathèque |
| `uploaded_by` | FK User, null | |
| `created_at` | DateTime auto_now_add | |

### `events.Event`
| Champ | Type | Notes |
|---|---|---|
| `id` | UUID pk | |
| `slug` | Slug(200), unique | dérivé du `title` |
| `title` | Char(200) | |
| `kind` | Char(40), blank | concert, performance, spectacle, quartier… (texte libre) |
| `starts_at` | DateTime | |
| `ends_at` | DateTime, null | |
| `location` | Char(200), blank | ex. « Le Pâquier, Annecy » |
| `price` | Char(80), blank | ex. « Entrée libre », « 8 € » |
| `description` | Text | **HTML léger sanitizé** (nh3) |
| `cover` | FK Image, null | image principale |
| `gallery` | M2M Image (ordonnée) | via table `EventImage` avec `order` |
| `status` | Char(10) | `draft` \| `published`, défaut `draft` |
| `published_at` | DateTime, null | posé au 1er passage en `published` |
| `created_at` / `updated_at` | DateTime | |
| `is_past` | property | calc sur `ends_at` ou `starts_at` vs `now()` |

### `news.News`
| Champ | Type | Notes |
|---|---|---|
| `id` | UUID pk | |
| `slug` | Slug(200), unique | dérivé du `title` |
| `title` | Char(200) | |
| `category` | Char(60), blank | ex. Appel, Atelier, Partenariat |
| `description` | Text | **HTML léger sanitizé** (nh3) |
| `cover` | FK Image, null | |
| `gallery` | M2M Image (ordonnée), optionnelle | via `NewsImage` avec `order` |
| `status` | Char(10) | `draft` \| `published`, défaut `draft` |
| `published_at` | DateTime, null | posé au 1er passage en `published` |
| `created_at` / `updated_at` | DateTime | |

### `accounts` (auth)
- **User** : modèle Django standard (ou `AbstractUser` custom si on veut un email-login plus tard).
- **Profile** (1-1 User) : `role` (`owner` \| `editor`), `is_validated` (bool), `created_at`.
- **Invitation** : `token` (unique, `secrets.token_urlsafe(32)`), `email` (optionnel, info),
  `created_by` (FK User), `created_at`, `expires_at` (~+7j), `used_at` (null tant que non consommée).
- **EditLock** (verrou d'édition, confort) : `object_type` (`event`\|`news`), `object_id` (UUID),
  `holder` (FK User), `acquired_at`, `heartbeat_at`. Verrou considéré actif si `heartbeat_at` récent
  (ex. < 2 min). Prise/heartbeat/relâche + reprise forcée par un owner.

> Helpers communs : un manager/queryset `.published()` (status=published) côté Event/News, et un
> mixin `published_at` posé à la première publication.

---

## 6. Pages publiques (rendu Django)

Layout de base commun : **Ticker** + **Header** (sticky, burger ≤ 880px) + contenu + **Footer**.
Charte = `DESIGN.md`. Toutes responsive (checklist §5.9 de DESIGN.md).

| Route | Page | Contenu |
|---|---|---|
| `/` | **Accueil** | Décliné de `reference/maquette-accueil.html` : Hero (Waveform), Stats (81 adhérent·e·s · 22 bénévoles · 2021), **À l'affiche** (prochain event en vedette), **Agenda** (3-4 prochains events), **Actus** (dernières), **Bloc L'asso** (3 missions), **CTA Adhérer**. Reveals en cascade. |
| `/agenda/` | **Agenda** | Liste des events `published`, séparés **à venir / passés** (`?when=upcoming\|past`), cartes 4/3. |
| `/agenda/<slug>/` | **Détail event** | Cover + date/lieu/prix (pastilles mono), description riche, **galerie**, CTA Adhérer. 404 si `draft`. |
| `/actus/` | **Actus** | Liste des actus `published` en lignes pleine largeur (date · catégorie+titre · flèche). |
| `/actus/<slug>/` | **Détail actu** | Cover + catégorie + description riche + galerie éventuelle. 404 si `draft`. |
| `/asso/` | **L'asso** | Manifeste + 3 missions statutaires (promotion spectacle vivant / manifestations / éducatif & préventif). Contenu fixe. |
| `/adherer/` | **Adhérer** | Pitch + **HelloAsso en click-to-load** (placeholder + bouton « Charger le formulaire »). |
| `/contact/` | **Contact** | Coordonnées, réseaux (Insta, Facebook, SoundCloud). Formulaire d'envoi = **phase 2** (en v1 : email/lien direct). |
| `/mentions-legales/`, `/confidentialite/` | **Légal** | Pages fixes (mentions + politique de confidentialité, mention Plausible sans cookie). |
| 404 | **Not found** | Gabarit à la charte. |

> Données réelles connues à reprendre : Stats = **81 adhérent·e·s · 22 bénévoles · 2021**.

---

## 7. Interface d'administration (conviviale)

Servie par Django sous un préfixe dédié (ex. **`/gestion/`**) — distinct de `/django-admin/` (réservé
au superuser pour le dépannage). Même charte « affiche » que le public (cf `DESIGN.md §0`, §6).

**Accès** : connexion par session (login/mot de passe), réservé aux profils **validés** (owner ou
editor). Création de compte uniquement via **invitation** (§9).

**Écrans**
1. **Connexion** : formulaire login. Rate-limité.
2. **Tableau de bord** : raccourcis « Nouvel event », « Nouvelle actu », listes récentes avec pastille
   de statut (brouillon/publié).
3. **Events — liste** : tableau (titre, date, statut, modifié le), filtres à venir/passés/brouillons,
   actions éditer/supprimer.
4. **Event — formulaire** (création/édition) :
   - champs : titre, slug (auto, modifiable), type (`kind`), date début/fin (`datetime-local`), lieu,
     prix, **description en texte riche** (gras/italique/liens/listes/titres), **cover** + **galerie**
     (sélection médiathèque ou upload direct) ;
   - **aperçu** du rendu (au minimum un lien « voir en brouillon » ou un panneau d'aperçu live) ;
   - actions : **Enregistrer (brouillon)**, **Publier** / **Dépublier**, Supprimer.
5. **Actus — liste / formulaire** : symétrique aux events (titre, slug, catégorie, description riche,
   cover, galerie, statut).
6. **Médiathèque** : upload (drag & drop), grille des images, `alt`/`titre` éditables, réutilisation.
7. **Comptes & invitations** (owner uniquement) : créer une invitation (→ token affiché, transmis
   hors-ligne), liste des éditeurs, (dé)validation, régénération de token.

**Verrou d'édition (confort)** : à l'ouverture d'un event/actu en édition, prise d'un `EditLock` +
heartbeat ; si un autre éditeur tient déjà le verrou → bandeau « en cours d'édition par X »
(lecture seule), un owner peut **reprendre** le verrou. *Peut être implémenté en dernier (P-admin) ou
différé si le temps manque — c'est un confort, pas un bloquant.*

**Texte riche** : **Tiptap** (ProseMirror) monté en **îlot JS** sur le champ `description` (toolbar :
gras, italique, lien, listes, h2/h3). Configurer Tiptap pour ne produire **que** les balises de
l'allowlist. Le HTML est **toujours re-sanitizé au serveur** avec `nh3` (allowlist : `p, strong, em,
u, s, a, ul, ol, li, h2, h3, blockquote, code`) avant enregistrement — ne jamais faire confiance au
client.

---

## 8. SEO

- `<head>` par page : `title`, `meta description`, `canonical`, Open Graph (titre, desc, image cover),
  `lang="fr"`.
- **JSON-LD** : `Event` (date, lieu, offre/prix) sur les détails d'event ; `Organization` global ;
  `BreadcrumbList` si pertinent.
- **`sitemap.xml`** (events + actus publiés + pages fixes) via `django.contrib.sitemaps`, **`robots.txt`**.
- Images responsives **WebP + `srcset`**, `loading="lazy"`, ratios fixes (anti-CLS).
- **Slugs stables** ; si un slug change, créer une **redirection 301** (petit modèle `Redirect`
  `old_path → new_path`, ou `django.contrib.redirects`).

---

## 9. Authentification & droits

- **Sessions Django + CSRF** (same-origin, monolithe). **Argon2** pour les mots de passe + validators
  stricts (longueur/complexité/similarité).
- **Pas d'inscription ouverte.** Bootstrap du premier **owner** via `createsuperuser` ou une commande
  de management `bootstrap_owner`.
- **Invitation par token** : un owner crée une invitation → un token est généré et **affiché**
  (transmis hors-ligne par l'owner, l'email arrive en phase 2). L'invité ouvre
  `/gestion/invitation/<token>/`, choisit son mot de passe → compte créé en rôle **editor**, **validé**,
  invitation marquée `used_at` (usage unique, expiration ~7j).
- **Rôles** :
  - **owner** : tout, plus gestion des comptes/invitations, reprise de verrou.
  - **editor** : CRUD events/actus/médias, publier/dépublier. Pas de gestion des comptes.
- **Rate-limiting** sur login, acceptation d'invitation, upload.

---

## 10. RGPD

- **Click-to-load** pour tous les tiers : **HelloAsso** (page Adhérer), embeds éventuels (YouTube,
  Vimeo, SoundCloud) — placeholder + bouton, aucun appel tiers tant que l'utilisateur n'a pas cliqué.
- **Analytics Plausible** (sans cookie, script léger ou proxy).
- Polices **self-hosted** (pas d'appel Google Fonts côté client).
- Pages **Mentions légales** + **Politique de confidentialité** (incluant la mention Plausible).
- Pas de cookie non essentiel ; cookie de session uniquement (sécurisé, `HttpOnly`, `SameSite=Lax`).

---

## 11. Sécurité

- **HTTPS** + `SECURE_SSL_REDIRECT`, **HSTS** (décision preload à acter avant submit), cookies durcis
  (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `HttpOnly`, `SameSite`).
- **CSP** stricte via `django-csp` (pas de script inline non haché côté admin).
- **Validation upload** : type réel via **Pillow** (pas l'extension), **poids max ~8 Mo**, ré-encodage,
  noms de fichiers aléatoires, limite Nginx `client_max_body_size`.
- **Sanitize** systématique du HTML riche (`nh3`) au serveur.
- En-têtes Nginx : `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`.

---

## 12. Déploiement

- **VPS** (OVH ou Hetzner — à trancher). **Nginx** en reverse-proxy → **Gunicorn**
  (`127.0.0.1:8000`, `--workers 3`), service **systemd** `432hz.service`. **Un seul process
  applicatif** (plus de Node SSR — c'était la complexité de la v1).
- Routage Nginx : `/static/` et `/media/` servis en direct (expires longs, `/media/` ~30j) ; tout le
  reste → Gunicorn.
- **HTTPS** Let's Encrypt (certbot, plugin nginx).
- **Backups** : `deploy/backup.sh` — `sqlite3.backup()` (gère WAL, pas besoin de CLI) + copie de
  `media/`, archive `tar.gz`, rétention (~14j), **cron** nocturne. Restauration testée (stop service →
  restore db + media → start).
- `.env` prod (secrets python-decouple), `DEBUG=False`, `ALLOWED_HOSTS` réel, `collectstatic`.
- **Nom de domaine** à réserver (bloque HTTPS + SEO).

---

## 13. Arborescence projet (cible)

```
432hz/                         # racine du repo (= nouveau projet)
  manage.py
  requirements.txt
  .env.example
  config/
    settings/ {base,dev,prod}.py
    urls.py  wsgi.py  asgi.py
  apps/
    common/       # mixins (PublishableQuerySet, slug auto, UUID pk), utils, sanitize
    accounts/     # Profile, Invitation, EditLock, auth views, invitation flow
    media/        # Image, médiathèque (upload, thumbnails WebP/srcset)
    events/        # Event (+ EventImage), vues publiques + gestion
    news/          # News (+ NewsImage), vues publiques + gestion
    pages/         # vues des pages fixes (accueil, asso, adhérer, contact, légal, 404)
    seo/           # sitemaps, robots, JSON-LD, Redirect
  templates/
    base.html  layout/ (header, footer, ticker, menu_mobile)
    public/ (home, agenda_list, event_detail, news_list, news_detail, asso, adherer, contact, legal, 404)
    gestion/ (login, dashboard, event_form, event_list, news_form, news_list, media, invitations)
    partials/ (button, card, badge, waveform, ...)
  static/
    css/app.css (compilé)  js/ (waveform.js, menu.js, reveal.js)  fonts/  brand/
  theme/            # source Tailwind si pipeline npm (input.css, package.json) — optionnel
  deploy/           # nginx.conf, 432hz.service, backup.sh, DEPLOY.md
```

> Fichiers de design prêts à copier depuis ce bundle : `design/tokens.css` → `static/css/`,
> `design/globals.css` → source Tailwind, `design/tailwind.config.js` → racine,
> `design/waveform.js` → `static/js/`. `reference/maquette-accueil.html` = gabarit de l'accueil.

---

## 14. Roadmap de construction (linéaire)

**P0 — Fondations**
- Repo + `CLAUDE.md` + `CONVENTIONS.md` + `DESIGN.md` + `design/`.
- Django 5.2 + SQLite (WAL) + settings par env (python-decouple).
- Pipeline Tailwind (`globals.css` → `static/css/app.css`), `base.html` (layout, fonts self-hosted,
  grain papier, focus), **Waveform** branché.
- Commande `bootstrap_owner`.

**P1 — Données & auth**
- Modèles `media.Image`, `events.Event` (+EventImage), `news.News` (+NewsImage), `accounts.Profile`,
  `Invitation`, `EditLock`. Migrations. Manager `.published()`.
- Argon2 + validators. **Invitation par token** (création owner, acceptation, validation). Rôles +
  permissions (owner/editor). Login/logout session.

**P2 — Gestion (admin convivial)**
- Écrans `/gestion/` : login, dashboard, **CRUD events** (formulaire + texte riche sanitizé + cover +
  galerie + bascule publier/dépublier), **CRUD actus** symétrique.
- **Médiathèque** (upload + thumbnails WebP/srcset). Comptes & invitations (owner).
- **Verrou d'édition** (ou différé).

**P3 — Front public**
- Layout (Header/Footer/Ticker/menu mobile JS). **Accueil** (maquette). **Agenda** liste + détail.
  **Actus** liste + détail. **Asso / Adhérer / Contact / Légal / 404**.
- Responsive « op » (checklist DESIGN.md 320→1600), reveals au scroll.

**P4 — SEO & RGPD**
- Head par page, **JSON-LD** (Event/Organization), **sitemap.xml** + **robots.txt**, 301 sur slug.
- **Click-to-load** (HelloAsso + embeds), **Plausible**, pages légales.

**P5 — Sécurité (durcissement)**
- CSP (`django-csp`), `SECURE_*`/HSTS, cookies durcis. **Rate-limiting** (login, invite, upload).
  **Validation upload** (type réel, poids, ré-encodage). Sanitize confirmé.

**P6 — Ops & recette**
- Nginx + Gunicorn + systemd, HTTPS Let's Encrypt. **Backups** (SQLite + médias) planifiés et testés.
  Logs (+ Sentry optionnel). Recette **responsive + a11y**.

**P7 — Contenu réel & lancement**
- Saisie du vrai contenu par l'asso, vérif SEO (Search Console), redirections, go-live.

> **Jalons** : (1) squelette qui tourne + un event éditable (P0-P1) ; (2) gestion utilisable +
> accueil rendu (P2-P3) ; (3) site complet + SEO/RGPD (P4) ; (4) prêt prod durci/sauvegardé (P5-P6) ;
> (5) en ligne (P7).

---

## 15. Conventions

Voir **`CONVENTIONS.md`** (KISS/DRY, code anglais / commentaires français, **commits 100 % FR** sans
mention d'IA, TDD logique métier, branches DEV/PROD, **jamais de push** par l'assistant, confirmation
avant action destructive). La charte **`DESIGN.md`** fait foi pour tout choix visuel.
