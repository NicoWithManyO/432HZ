# CONVENTIONS — 432 Hz v2 (manyO.dev)

Conventions de travail du projet. Complète `CAHIER-DES-CHARGES.md` (le quoi) et `DESIGN.md` (le visuel).

## Principes de code

- **KISS / DRY / responsabilité unique.** Solution la plus simple qui marche, pas de sur-ingénierie ni
  d'abstraction prématurée.
- **Périmètre strict.** On implémente uniquement ce qui est demandé. Pas de refactor opportuniste ni de
  bonus « au cas où ».
- **Langue.** Code en **anglais** (variables, fonctions, fichiers), commentaires en **français**.
- **Commentaires utiles seulement.** Le *pourquoi* non évident (contrainte, workaround, invariant),
  jamais la paraphrase du code.
- **Cause racine, jamais de pansement.** Pas de `try/except: pass` silencieux ni de fix qui masque le
  symptôme.
- **Idiomes respectés.** PEP 8 + layout Django pour Python. Templates Django lisibles, classes Tailwind
  factorisées (`@layer components` ou partials `{% include %}`). JS vanilla en modules ES, sobre.

## Backend (Django, monolithe)

- Settings découpés par environnement (`config/settings/{base,dev,prod}.py`), secrets via
  **python-decouple** (`.env`, jamais commité — voir `.env.example`).
- Base **SQLite** en **mode WAL** (dev et prod). Backup = `sqlite3.backup()` + copie des médias.
- Dépendances **figées** dans `requirements.txt` (versions épinglées).
- Apps métier dans `apps/` : `common`, `accounts`, `media`, `events`, `news`, `pages`, `seo`.
- HTML riche (description events/actus) **toujours sanitizé serveur** (`nh3`) avant enregistrement.

## Front (templates Django + Tailwind + JS vanilla)

- Tailwind + tokens de `DESIGN.md` (`design/tokens.css`, `design/globals.css`,
  `design/tailwind.config.js`). Radius 0, ombres dures, charte « affiche » respectée.
- **Pas de framework JS.** JS vanilla minimal et progressif (Waveform, menu mobile, reveals, ticker,
  click-to-load). Le site doit rester utilisable sans JS pour le contenu essentiel.
- Polices **self-hosted** (`static/fonts/`, `@font-face`) — pas d'appel Google côté client (RGPD/perf).
- Accessibilité : `:focus-visible` rouge partout, cibles tactiles ≥ 44px, `prefers-reduced-motion`
  respecté, `alt` sur les images.

## Tests

- **TDD** pour la logique métier (statut publié, `is_past`, slug auto, sanitize, permissions,
  verrou) : test qui échoue d'abord.
- Test-after pour l'UI / CRUD / câblage. Re-run systématique des tests existants après une modif.
- Vérif manuelle du parcours (serveur de dev) pour les écrans. **Pas de vérif verte = pas de commit.**

## Git & commits

- Messages de commit **100 % français**, préfixes : `init` / `ajout` / `correctif` / `refonte` /
  `doc` / `test`.
- **Jamais** de trailer `Co-Authored-By` ni aucune mention d'IA/assistant.
- **Jamais de `git push`** ni de PR depuis l'assistant — c'est l'utilisateur qui pousse.
- Branches : on développe sur **`DEV`** ; merge sur **`PROD`** uniquement à la mise en production.
- Confirmation obligatoire avant toute action destructive (`rm -rf`, `reset --hard`, drop, etc.).
