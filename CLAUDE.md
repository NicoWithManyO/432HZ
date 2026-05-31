# CLAUDE.md — 432 Hz (v2)

Repère pour démarrer une session sur ce projet (reconstruction « reset »).

## Le projet

Site de l'asso culturelle **432 Hz** (Annecy). **Monolithe Django** : pages publiques **fixes** en
templates + Tailwind, et une **interface de gestion conviviale** où les admins postent **events** et
**actus** (bascule Brouillon / Publié). Esthétique = **affiche culturelle imprimée**. SQLite (WAL).

> On REPART de zéro. L'ancienne v1 (headless DRF + React SSR + moteur de blocs + pages en arbre) est
> **abandonnée** : pas d'API publique, pas de React, pas de composition de blocs.

## Sources de vérité (à lire avant de coder)

- `CAHIER-DES-CHARGES.md` — périmètre, décisions, modèle de données, pages, admin, auth, déploiement,
  **roadmap P0→P7**.
- `DESIGN.md` — charte graphique (couleurs, typo, formes, responsive, composants, Waveform). **Fait foi**
  pour toute mesure visuelle.
- `CONVENTIONS.md` — code, tests, git.
- `design/` — fichiers prêts : `tokens.css`, `globals.css`, `tailwind.config.js`, `waveform.js`.
- `reference/` — `maquette-accueil.html` (gabarit de l'accueil, fait foi), `logo-432.png`.

## Décisions structurantes

- **Monolithe Django** (1 process), **SQLite partout** (WAL, backup `sqlite3.backup()` + médias).
- **Pages fixes** (templates), **pas** de CMS de pages ni de moteur de blocs.
- Events/actus : **bascule `draft`/`published`** (pas d'historique). Description = **HTML léger
  sanitizé serveur** (`nh3`). Images = `ImageField` + vignettes **WebP/srcset**.
- Auth **sur invitation** (token), rôles **owner / éditeur**, **verrou d'édition** (confort), sessions
  + CSRF, Argon2.
- SEO (head/JSON-LD/sitemap/robots) + RGPD (click-to-load, **Plausible**) en v1.

## Règles de travail

- Code en **anglais**, commentaires en **français**. Périmètre strict, KISS/DRY.
- Commits **100 % FR** (`init`/`ajout`/`correctif`/`refonte`/`doc`/`test`), **aucune** mention d'IA.
  On bosse sur **`DEV`**, merge sur **`PROD`** seulement à la mise en prod.
- **Jamais de push** — l'utilisateur s'en charge. Confirmation avant toute action destructive.
- **TDD** pour la logique métier ; pas de vérif verte = pas de commit.
