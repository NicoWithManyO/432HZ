# 432 Hz — v2 (bundle de démarrage)

Bundle de **reconstruction** du site de l'association 432 Hz. On repart de zéro en **monolithe Django**
(pages fixes + interface de gestion conviviale pour events/actus), en **gardant la charte graphique**.

## Par où commencer (nouvelle session Claude Code)

1. Lis **`CLAUDE.md`** (amorçage) puis **`CAHIER-DES-CHARGES.md`** (le quoi + la roadmap P0→P7).
2. Garde **`DESIGN.md`** sous la main — il fait foi pour le visuel.
3. Démarre à **P0** : initialise le projet Django dans ce dossier, copie les fichiers `design/` aux bons
   endroits (cf §13 du cahier des charges), branche Tailwind + la Waveform.

## Contenu du bundle

| Fichier | Rôle |
|---|---|
| `CAHIER-DES-CHARGES.md` | Spécification complète : périmètre, décisions, modèle de données, pages, admin, auth, SEO/RGPD, sécurité, déploiement, arborescence, **roadmap**. |
| `DESIGN.md` | **Charte graphique** (couleurs, typo, formes, responsive, composants, Waveform), retargettée pour Django + Tailwind. |
| `CONVENTIONS.md` | Conventions code / tests / git. |
| `CLAUDE.md` | Repère de session pour le nouveau projet. |
| `design/tokens.css` | CSS vars (source unique des couleurs/typo/espacements). |
| `design/globals.css` | Base + grain papier + focus + ticker + reveals + reduced-motion (source Tailwind). |
| `design/tailwind.config.js` | Config Tailwind (couleurs, ombres dures, radius 0). Ajuster les `content` globs. |
| `design/waveform.js` | Composant signature « oscilloscope » en JS vanilla. |
| `reference/maquette-accueil.html` | **Maquette de l'accueil — fait foi pour les mesures.** |
| `reference/logo-432.png` | Logo (asset figé). |
| `reference/DESIGN-original.md` | Ancienne charte (avant retarget) — archive. |

## Décisions actées (résumé)

- **Monolithe Django**, 1 process, **SQLite (WAL)**.
- **Pages fixes** (templates) — plus de moteur de blocs ni de pages en arbre.
- Events/actus : **bascule Brouillon / Publié**, description **HTML léger sanitizé** (`nh3`), images
  **WebP/srcset**.
- Auth **sur invitation par token**, rôles **owner / éditeur**, **verrou d'édition** (confort).
- Pages v1 : **Accueil, Agenda (+ détail), Actus (+ détail), Asso, Adhérer, Contact/Légal, 404**.
- SEO + RGPD (**Plausible**, HelloAsso click-to-load) en v1.
