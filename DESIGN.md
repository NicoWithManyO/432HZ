# DESIGN.md — Charte graphique 432 Hz

> Charte visuelle du site de l'association **432 Hz** (Annecy). **Référence unique** de la couche
> front. Stack cible : **monolithe Django** — templates Django + **Tailwind** (CSS vars de
> `design/tokens.css`), JS vanilla minimal (Waveform, menu mobile, reveals). Pas de React, pas de
> shadcn.
> Maquette de référence : `reference/maquette-accueil.html`. **En cas de doute sur une mesure, c'est
> elle qui fait foi.** Logo : `reference/logo-432.png`.

---

## 0. Esprit (à lire avant de coder)

L'asso fait du **spectacle vivant** : concerts, performances, spectacles, fêtes de quartier, plus une
mission **éducative & préventive**. Le site doit être **chaleureux, vivant, communautaire** — surtout
pas underground/rave.

Direction verrouillée : **affiche culturelle imprimée**.
- Fond **papier crème**, encre **noire**, **rouge** du logo en accent franc.
- **Ombres portées nettes** (offset dur, jamais de blur), **cadres épais**, **angles vifs** (pas
  d'arrondis).
- Grain papier discret sur tout l'écran.
- La **signature** = l'**oscilloscope** du logo, décliné comme motif graphique (bandeaux,
  séparateurs) via le composant `Waveform`.

Croisement assumé de deux mondes :
- **Son / fréquence** → grotesque géométrique + mono technique + onde.
- **Spectacle vivant** → serif expressif et chaleureux pour les titres.

**Règle d'or** : si un écran ressemble à un dashboard SaaS générique (arrondis mous, ombres floues,
dégradés violets), c'est raté. On veut une **affiche**. Cette règle vaut aussi pour l'**admin** :
l'interface de gestion suit la même charte (cadres nets, ombres dures, mono pour les labels).

---

## 1. Logo (verrouillé)

Asset fourni, jamais redessiné : `432` / un oscilloscope rouge dans un cadre noir avec ligne médiane /
`H Z`.
- Fichier : `static/brand/logo-432hz.svg` (préférer un SVG net ; à défaut le PNG `reference/logo-432.png`).
- Zone de protection : marge mini = hauteur du chiffre « 4 » tout autour.
- Tailles : header `46px`, footer `64px` de haut.
- Fonds autorisés : crème (`--paper`) ou noir (`--ink`). Jamais sur photo sans cartouche.
- **Ne pas confondre** le logo (figé) avec le composant `Waveform` (§7) — motif dérivé, libre d'usage.

---

## 2. Couleurs (tokens — cf `design/tokens.css`)

| Token | Hex | Rôle |
|---|---|---|
| `paper` | `#F4EEE1` | Fond principal (papier crème) |
| `paper-2` | `#EBE3D2` | Fond alterné, hover de lignes |
| `ink` | `#15120E` | Encre / texte / bordures / fonds sombres |
| `ink-soft` | `#3A342B` | Texte secondaire sur fond clair |
| `muted` | `#7A7164` | Labels, légendes, métadonnées |
| `red` | `#F4322E` | **Accent unique** (CTA, kickers, onde, hover) |
| `red-deep` | `#CE241F` | Rouge en petit texte sur crème (lisibilité), hover |
| `line` | `rgba(21,18,14,.16)` | Filets discrets |

**Discipline** : noir + crème + rouge, **rien d'autre**. Pas de seconde couleur d'accent. La hiérarchie
se fait au noir et aux tailles ; le rouge se mérite.

**Contraste / accessibilité (WCAG AA)** :
- `red #F4322E` sur `paper` ≈ 3.4:1 → **interdit pour du texte courant**. Réservé aux gros titres
  (≥ 24px bold), aplats avec texte blanc, éléments graphiques.
- Petit texte rouge sur crème → utiliser **`red-deep`**.
- Texte blanc sur `red` : OK. Texte `ink` sur `paper` : OK.

---

## 3. Typographie

| Usage | Police | Poids | Détails |
|---|---|---|---|
| Display / titres | **Fraunces** (serif) | 600 / 900, italique pour accents | côté « spectacle vivant » |
| Corps / UI | **Archivo** (grotesque) | 400 / 500 / 600 / 800 | lisible, neutre, robuste |
| Labels / mono | **Space Mono** | 400 / 700 | dates, kickers, « Hz » — **uppercase + letter-spacing** |

Polices **self-hosted** (RGPD/perf) — pas d'appel Google côté client. Servir des `woff2` depuis
`static/fonts/` (ou `@fontsource/*` si un petit build npm est présent), déclarées en `@font-face`.

**Échelle fluide** (clamp) :
- H1 hero : `clamp(2.7rem, 7.4vw, 6.1rem)` / line-height `.96` / `Fraunces 900`
- H2 section : `clamp(1.9rem, 4.4vw, 3.1rem)` / `Fraunces 900`
- H3 carte : `1.42rem` / `Fraunces 600`
- Corps : `17px` / line-height `1.55` / `Archivo 400`
- Mono label : `.72rem` / uppercase / letter-spacing `.14em`

Règle : **kickers en mono rouge**, **titres en serif**, **texte en grotesque**. On ne mélange pas.

---

## 4. Forme : bordures, ombres, radius

C'est ce qui fait le style « affiche ». À respecter scrupuleusement.
- **Radius** : `0` partout. Aucun arrondi (`borderRadius.none` Tailwind).
- **Bordures** : `2px solid ink` (standard), `3px solid ink` (éléments forts : feature, bandeau onde).
- **Ombres** : **offset dur, blur = 0** (utilitaires `shadow-hard`, `shadow-hard-lg`, `shadow-hard-red`).
  - bouton : `4px 4px 0 ink` → hover `6px 6px 0`
  - carte (hover) : `7px 7px 0 red`
  - feature : `8px 8px 0 ink`
- Le hover « décolle » l'élément : `transform: translate(-2px,-2px)` + ombre qui grandit. Transition
  `.12s–.14s`.

---

## 5. Layout & responsive (impeccable de 320px à l'ultrawide)

Mobile-first **impératif** — la majorité du public est sur téléphone. Principe : **fluidité d'abord
(clamp + grilles intrinsèques), breakpoints seulement pour les raffinements**.

### 5.1 Tokens responsive (cf `design/tokens.css`)
```css
--gutter: clamp(16px, 4vw, 24px);     /* padding latéral du conteneur */
--section-y: clamp(44px, 8vw, 66px);  /* respiration verticale des sections */
--hdr: 74px;                          /* hauteur header, sert au scroll-margin */
```
- Conteneur : `max-width:1240px`, padding `0 var(--gutter)`.
- `section` : `padding: var(--section-y) 0`, `border-bottom:2px solid ink`,
  `scroll-margin-top: calc(var(--hdr) + 8px)`.
- Corps : `font-size: clamp(15.5px, 1.4vw, 17px)`.

### 5.2 Typo & espacements fluides
Tout ce qui est « grand » est en `clamp` (cf §3). Idem paddings internes notables, marges de
section-head, gaps de grille (`clamp(16px,2.4vw,22px)`). **Aucune** valeur de titre/espace majeure en
`px` fixe.

### 5.3 Grilles intrinsèques (reflow automatique, sans media query)
```css
.grid-3{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(min(100%, 265px), 1fr));
  gap:clamp(16px,2.4vw,22px);
}
```
`min(100%, 265px)` évite tout débordement à 320px. 3 → 2 → 1 colonne automatiquement.

### 5.4 Breakpoints (raffinements uniquement)
| Largeur | Ce qui change |
|---|---|
| `> 880px` | desktop plein, menu inline |
| `≤ 880px` | menu inline masqué → **burger + overlay** ; `feature` en 1 colonne ; footer 3 → 2 |
| `≤ 600px` | `stats` → 2×2 ; lignes d'actus empilées (flèche masquée) ; footer 1 colonne ; cartouche header masquée |

### 5.5 Menu mobile (vrai composant JS, pas un placeholder)
Overlay plein écran, jamais une `alert`.
- Panneau `position:fixed; inset:0; z-index:60`, header sticky **au-dessus** (`z-index:70`) pour garder
  le burger (→ croix) tappable.
- Animation `transform: translateY(-100%) → 0`, `.4s cubic-bezier(.6,.05,.1,1)`.
- Liens en **Fraunces 900** géants (`clamp(2rem,11vw,3.2rem)`), CTA Adhérer en aplat rouge.
- **Verrouille le scroll du body** à l'ouverture (`overflow:hidden`), le restaure à la fermeture.
- Ferme sur : clic d'un lien, touche `Échap`, passage en desktop (`matchMedia('(min-width:881px)')`).
- Burger animé en croix. `aria-expanded` / `aria-controls` / `aria-hidden` tenus à jour.

### 5.6 Onde à densité adaptative
La `Waveform` change de densité : `< 600px → ~72 barres | < 900px → ~110 | ≥ 900px → 150`. Reconstruire
**au resize** (debounce ~180ms — déjà géré dans `design/waveform.js`). Bandeau en
`clamp(80px,16vw,120px)`, SVG `preserveAspectRatio="none"`.

### 5.7 Cibles tactiles & confort
- Tout interactif ≥ **44–48px** de hauteur tactile.
- `:focus-visible` rouge visible partout.
- `<meta viewport ... viewport-fit=cover>` ; `-webkit-text-size-adjust:100%`.
- `text-wrap: balance` sur les titres.

### 5.8 Anti-débordement (zéro scroll horizontal)
`body{overflow-x:hidden}` (filet), `min(100%, …)` sur les `minmax`, vérifier à 320/360/768/1024/1440 que
les ombres dures + `translate` au hover ne créent pas de scroll.

### 5.9 `prefers-reduced-motion`
Obligatoire. En `reduce` : couper ticker, pulsation de l'onde, reveals (état final immédiat),
neutraliser transitions/animations. Déjà câblé dans `design/globals.css` et `design/waveform.js`.

> **Checklist recette responsive** : 320 · 360 · 414 · 768 · 1024 · 1280 · 1600px — pas de débordement,
> pas de texte coupé, cibles tactiles OK, menu mobile fluide, onde lisible, focus visible,
> reduced-motion respecté.

---

## 6. Tokens dans le code (Tailwind, monolithe Django)

Fichiers prêts à l'emploi fournis dans `design/` :
- `tokens.css` — les CSS vars (source unique). À `@import` en premier.
- `globals.css` — base + grain papier + focus + skip-link + ticker + reveals + reduced-motion.
- `tailwind.config.js` — couleurs / fontFamily / `boxShadow` durs / `borderRadius:0`. Ajuster les
  `content` globs aux templates Django réels.
- `waveform.js` — composant signature en JS vanilla.

**Pipeline conseillé** (sans bundler lourd) : Tailwind CLI (standalone ou npm) compile
`globals.css` → `static/css/app.css` en scannant `templates/**/*.html`. Charger `app.css` + les
`@font-face` dans le `<head>` du layout de base.

**Composants UI réutilisables** : pas de shadcn — on écrit des **classes utilitaires Tailwind**
factorisées (via `@layer components` ou des partials de template `{% include %}`). Exemples de
recettes :
- **Bouton rouge** : `inline-flex items-center min-h-[48px] px-5 bg-red text-paper border-2 border-ink
  shadow-hard font-sans font-extrabold uppercase tracking-wide hover:-translate-x-0.5
  hover:-translate-y-0.5 hover:shadow-[6px_6px_0_var(--ink)] transition`.
- **Bouton fantôme « poster »** : idem mais `bg-paper text-ink`.
- **Carte** : `border-2 border-ink bg-paper hover:shadow-hard-red hover:-translate-x-1
  hover:-translate-y-1 transition`.
- **Badge** : `font-mono uppercase tracking-wider text-xs border-2` — neutre (`border-ink bg-paper`)
  ou rouge (`bg-red text-white border-white`).

---

## 7. Composant signature — `Waveform`

Motif d'oscilloscope dérivé du logo (§1). Bandeau hero, séparateur, fond du bloc adhésion.
**Déterministe** (rendu stable), enveloppe en cloche (plus fort au centre), pulsation optionnelle,
densité adaptative, respecte `prefers-reduced-motion`.

Implémentation fournie : **`design/waveform.js`** (vanilla, à déposer en `static/js/waveform.js`).
```html
<div class="waveform h-[clamp(80px,16vw,120px)]" data-baseline="true" data-animated="true"></div>
<script type="module">
  import { mountWaveforms } from "/static/js/waveform.js";
  mountWaveforms();
</script>
```
Usage hero : cadre `3px solid ink`, cartouches `432` (haut-gauche, serif 900) et `HZ` (bas-droite, mono
letter-spacing `.4em`) qui chevauchent le cadre.

---

## 8. Inventaire des composants (gabarits publics)

| Composant | Specs clés |
|---|---|
| **Ticker** | bandeau noir sticky-top, défilé mono uppercase, `+` rouge entre items, boucle ~28s linéaire infinie (contenu dupliqué ×2). |
| **Header** | sticky, fond crème, `border-bottom 2px ink`. Logo + cartouche mono « Association culturelle · Annecy » (filet rouge à gauche). Liens à soulignement rouge animé ; bouton « Adhérer » rouge. Burger ≤ 880px. |
| **Hero** | kicker mono rouge → H1 serif (italique rouge sur le mot fort) → lede → 2 CTA → **bande Waveform** → bandeau **stats**. Reveal en cascade au load. |
| **Stats** | grille 4 (→ 2×2 mobile), séparateurs = fond `ink` + cellules crème. Chiffres serif 900 (certains rouges), labels mono muted. Valeurs réelles : **81 adhérent·e·s · 22 bénévoles · 2021**. |
| **Feature (À l'affiche)** | 2 colonnes, `border 3px ink`, `shadow-hard-lg`. Média = aplat sombre + hachures rouges + badge type + grande date serif. Corps : type mono rouge, titre serif, méta en pastilles mono bordées, CTA rouge. |
| **Card** (agenda / archives) | média ratio 4/3 (fond sombre + placeholder + badge), corps : date mono rouge, titre serif 600, desc muted, lieu mono. Hover = décollage + `shadow-hard-red`. |
| **News list** | lignes pleine largeur séparées par filets `2px ink`. Grille `date · (catégorie+titre) · flèche`. Hover : fond `paper-2` + décalage padding gauche. Flèche masquée mobile, lignes empilées. |
| **Bloc L'asso** | 2 colonnes : manifeste (titre serif, mot fort rouge italique) + **3 missions** numérotées (mono rouge) séparées par filets (promotion spectacle vivant / manifestations / éducatif & préventif). |
| **CTA Adhérer** | section pleine `ink`, texte crème, titre serif géant (mot fort rouge italique), bouton rouge à ombre rouge. Waveform rouge translucide ancrée en bas. Brancher sur **HelloAsso** (click-to-load). |
| **Footer** | fond crème, 3 colonnes (logo+pitch / navigation / réseaux : Insta, Facebook, SoundCloud, contact). Barre basse mono : copyright + mentions légales/RGPD. |

---

## 9. Motion

- **Reveal au scroll** : `IntersectionObserver` (threshold ~`.12`), classe `.pending` → révélée,
  `opacity 0→1` + `translateY(18px→0)`, `.6s ease`, cascade (`i % 4 * 60ms`). Contenu visible par défaut
  (pas d'écran blanc) — cf `globals.css`.
- **Pulsation onde** : rAF, désactivée si reduced-motion (`waveform.js`).
- **Hover** : décollage `translate(-2..-3px)` + ombre agrandie, `.12–.14s`.
- **Ticker** : translation linéaire infinie.
- **Toujours** respecter `prefers-reduced-motion: reduce`.

---

## 10. Ton éditorial

- Tutoiement, chaleureux, direct, **inclusif** (« adhérent·e·s », « curieux·se »).
- Phrases courtes, énergiques. Verbes d'action (« On fait vibrer », « Adhère, fais du bruit »).
- Jamais de jargon. Festif mais crédible (mission éducative).
- Kickers mono en VO courte (« Du neuf », « Ça s'est passé chez nous »).

---

## 11. Garde-fous a11y / perf / RGPD

- Contraste : respecter §2 (rouge petit texte → `red-deep`).
- `:focus-visible` rouge visible sur **tous** les interactifs.
- Images d'events/actus : `alt` descriptifs, `loading="lazy"`, ratio fixe (anti-CLS), WebP + `srcset`.
- Polices self-hosted → pas d'appel Google côté client.
- HelloAsso / embeds (YouTube, Vimeo, SoundCloud) : **click-to-load** (placeholder + bouton) tant qu'il
  n'y a pas de gestionnaire de consentement.
- Waveform : SVG léger, pas d'images lourdes pour le motif.
- Analytics **Plausible** (sans cookie).

---

*Maquette de référence : `reference/maquette-accueil.html`. En cas de doute sur une mesure, c'est elle
qui fait foi.*
