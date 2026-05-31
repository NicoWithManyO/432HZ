# DESIGN.md — Association 432 Hz

> Charte de design du site de l'association **432 Hz** (Annecy).
> Référence unique pour la couche front. À garder à la racine du repo et à lier depuis `CLAUDE.md`.
> Stack cible : **Django + DRF (headless) · React + TypeScript (SSR public + admin SPA) · Tailwind · shadcn/ui · Vite**. (Pas de Wagtail — cf `ARCHITECTURE.md`.)
> Auteur : Nico — manyO.dev.

---

## 0. Esprit (à lire avant de coder)

L'asso fait du **spectacle vivant** : concerts, performances, spectacles, fêtes de quartier, plus une mission **éducative & préventive**. Le site doit être **chaleureux, vivant, communautaire** — surtout pas underground/rave.

Direction verrouillée : **affiche culturelle imprimée**.
- Fond **papier crème**, encre **noire**, **rouge** du logo en accent franc.
- **Ombres portées nettes** (offset dur, jamais de blur), **cadres épais**, **angles vifs** (pas d'arrondis).
- Grain papier discret sur tout l'écran.
- La **signature** = l'**oscilloscope** du logo, décliné comme motif graphique partout (bandeaux, séparateurs).

Croisement assumé de deux mondes :
- **Son / fréquence** → grotesque géométrique + mono technique + onde.
- **Spectacle vivant** → serif expressif et chaleureux pour les titres.

Règle d'or : si un écran ressemble à un dashboard SaaS générique (arrondis mous, ombres floues, dégradés violets), c'est raté. On veut une **affiche**.

---

## 1. Logo (verrouillé)

Le logo est un **asset fourni**, on ne le redessine jamais : c'est `432` / un oscilloscope rouge dans un cadre noir avec ligne médiane / `H Z`.

- Fichier : `static/brand/logo-432hz.svg` (préférer un SVG net ; à défaut le PNG fourni).
- Zone de protection : marge mini = hauteur du chiffre « 4 » tout autour.
- Tailles : header `46px`, footer `64px` de haut.
- Fonds autorisés : crème (`--paper`) ou noir (`--ink`). Jamais sur photo sans cartouche.
- **Ne pas confondre** le logo (figé) avec le composant `Waveform` (§7) qui est un **motif dérivé** libre d'usage pour la déco.

---

## 2. Couleurs (tokens)

| Token | Hex | Rôle |
|---|---|---|
| `paper` | `#F4EEE1` | Fond principal (papier crème) |
| `paper-2` | `#EBE3D2` | Fond alterné, hover de lignes |
| `ink` | `#15120E` | Encre / texte / bordures / fonds sombres |
| `ink-soft` | `#3A342B` | Texte secondaire sur fond clair |
| `muted` | `#7A7164` | Labels, légendes, métadonnées |
| `red` | `#F4322E` | **Accent unique** (CTA, kickers, onde, hover) |
| `red-deep` | `#CE241F` | Rouge en texte sur crème (lisibilité), hover |
| `line` | `rgba(21,18,14,.16)` | Filets discrets |

**Discipline** : noir + crème + rouge, **rien d'autre**. Pas de seconde couleur d'accent. La hiérarchie se fait au noir et aux tailles, le rouge se mérite.

**Contraste / accessibilité (WCAG AA)** :
- `red #F4322E` sur `paper` ≈ 3.4:1 → **interdit pour du texte courant**. À réserver aux gros titres (≥ 24px bold), aux aplats avec texte blanc, et aux éléments graphiques.
- Pour du rouge en petit texte sur crème, utiliser **`red-deep`**.
- Texte blanc sur `red` : OK. Texte `ink` sur `paper` : OK (ratio élevé).

---

## 3. Typographie

| Usage | Police | Poids | Détails |
|---|---|---|---|
| Display / titres | **Fraunces** (serif) | 600 / 900, italique pour accents | côté « spectacle vivant », chaleureux |
| Corps / UI | **Archivo** (grotesque) | 400 / 500 / 600 / 800 | lisible, neutre, robuste |
| Labels / mono | **Space Mono** | 400 / 700 | dates, kickers, « Hz », coordonnées — **uppercase + letter-spacing** |

Import (Google Fonts) :
```
https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;800;900&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,500&family=Space+Mono:wght@400;700&display=swap
```
(En prod, préférer `@fontsource/*` self-hosted pour RGPD/perf : `@fontsource/fraunces`, `@fontsource/archivo`, `@fontsource/space-mono`.)

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

- **Radius** : `0` partout. Aucun arrondi.
- **Bordures** : `2px solid ink` (standard), `3px solid ink` (éléments forts : feature, bandeau onde).
- **Ombres** : **offset dur, blur = 0**.
  - bouton : `4px 4px 0 var(--ink)` → hover `6px 6px 0`
  - carte (hover) : `7px 7px 0 var(--red)`
  - feature : `8px 8px 0 var(--ink)`
- Le hover « décolle » l'élément : `transform: translate(-2px,-2px)` + ombre qui grandit. Transition `.12s–.14s`.

---

## 5. Layout & responsive (objectif : impeccable de 320px à l'ultrawide)

Mobile-first **impératif** — la majorité du public est sur téléphone. Le responsive ne doit pas juste « ne pas casser », il doit être fluide et soigné. Principe : **fluidité d'abord (clamp + grilles intrinsèques), breakpoints seulement pour les raffinements** (réorganisations qu'on ne peut pas faire fluides).

### 5.1 Tokens responsive (CSS vars)
```css
--gutter: clamp(16px, 4vw, 24px);     /* padding latéral du conteneur */
--section-y: clamp(44px, 8vw, 66px);  /* respiration verticale des sections */
--hdr: 74px;                          /* hauteur header, sert au scroll-margin */
```
- Conteneur : `max-width:1240px`, padding `0 var(--gutter)`.
- `section` : `padding: var(--section-y) 0`, `border-bottom:2px solid ink`, **`scroll-margin-top: calc(var(--hdr) + 8px)`** (les ancres ne passent pas sous le header sticky).
- Corps : `font-size: clamp(15.5px, 1.4vw, 17px)`.

### 5.2 Typo & espacements fluides
Tout ce qui est « grand » est en `clamp` (cf §3). Idem pour les paddings internes notables (`.feature__body: clamp(22px,4vw,34px)`), les marges de section-head, les gaps de grille (`clamp(16px,2.4vw,22px)`). **Aucune** valeur de titre/espace majeure en `px` fixe.

### 5.3 Grilles intrinsèques (reflow automatique)
Les grilles de cartes ne dépendent **pas** des breakpoints : elles se réorganisent seules.
```css
.grid-3{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(min(100%, 265px), 1fr));
  gap:clamp(16px,2.4vw,22px);
}
```
`min(100%, 265px)` évite tout débordement à 320px. Résultat : 3 → 2 → 1 colonne sans media query.

### 5.4 Breakpoints (raffinements uniquement)
| Largeur | Ce qui change |
|---|---|
| `> 880px` | desktop plein, menu inline |
| `≤ 880px` | menu inline masqué → **burger + overlay** ; `feature` passe en 1 colonne (média bordure bas au lieu de droite) ; `asso` en 1 colonne ; footer 3 → 2 |
| `≤ 600px` | `stats` → 2×2 ; lignes d'actus empilées (flèche masquée) ; footer 1 colonne ; cartouche header masquée ; lien « voir tout » repassé sous le titre |

### 5.5 Menu mobile (vrai composant, pas un placeholder)
Overlay plein écran, jamais une `alert`.
- Panneau `position:fixed; inset:0; z-index:60`, header sticky **au-dessus** (`z-index:70`) pour garder le burger (→ croix) tappable.
- Animation `transform: translateY(-100%) → 0`, `.4s cubic-bezier(.6,.05,.1,1)`, `visibility` togglée.
- Liens en **Fraunces 900** géants (`clamp(2rem,11vw,3.2rem)`), CTA Adhérer en aplat rouge.
- **Verrouille le scroll du body** à l'ouverture (`overflow:hidden`), le restaure à la fermeture.
- Ferme sur : clic d'un lien, touche `Échap`, passage en desktop (`matchMedia('(min-width:881px)')`).
- Burger animé en croix (`.active` → rotation des 2 barres, opacité 0 sur la médiane). `aria-expanded` / `aria-controls` / `aria-hidden` tenus à jour.

### 5.6 Onde à densité adaptative
La `Waveform` n'a pas la même densité selon l'écran (sinon barres tassées sur mobile) :
```
< 600px → ~72 barres   |   < 900px → ~110   |   ≥ 900px → 150
```
Reconstruire **au resize** (debounce ~180ms). Hauteur du bandeau en `clamp(80px,16vw,120px)`, SVG en `preserveAspectRatio="none"` (étirement plein largeur assumé).

### 5.7 Cibles tactiles & confort
- Tout interactif ≥ **44–48px** de hauteur tactile (boutons `min-height:48px`, lien Adhérer header `min-height:44px`, lignes d'actus `min-height:64px`, burger `padding:10px`).
- `:focus-visible` rouge visible partout (les ombres dures ne tiennent pas lieu de focus).
- `<meta viewport ... viewport-fit=cover>` ; `-webkit-text-size-adjust:100%`.
- `text-wrap: balance` sur les titres.

### 5.8 Anti-débordement (zéro scroll horizontal)
- `body{overflow-x:hidden}` (filet de sécurité, pas une excuse pour déborder).
- `min(100%, …)` sur les `minmax` de grille.
- Les **ombres dures** et le `translate` au hover ne doivent jamais créer de scroll : vérifier à 320 / 360 / 768 / 1024 / 1440.

### 5.9 `prefers-reduced-motion`
Obligatoire. En `reduce` : couper ticker, pulsation de l'onde (ne pas lancer la boucle rAF) et reveals (état final immédiat : `.rv{opacity:1;transform:none}`), neutraliser transitions/animations via le bloc média global.

> **Checklist de recette responsive** : 320 · 360 · 414 · 768 · 1024 · 1280 · 1600px — pas de débordement, pas de texte coupé, cibles tactiles OK, menu mobile fluide, onde lisible, focus visible, reduced-motion respecté.

---

## 6. Tokens dans le code (Tailwind + shadcn)

### `app/globals.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root{
  --paper:#F4EEE1; --paper-2:#EBE3D2;
  --ink:#15120E; --ink-soft:#3A342B; --muted:#7A7164;
  --red:#F4322E; --red-deep:#CE241F;
  --line:rgba(21,18,14,.16);
}

@layer base{
  body{ background:var(--paper); color:var(--ink); font-family:theme('fontFamily.sans'); }
  /* grain papier global */
  body::after{
    content:""; position:fixed; inset:0; pointer-events:none; z-index:9999;
    opacity:.05; mix-blend-mode:multiply;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }
  :focus-visible{ outline:3px solid var(--red); outline-offset:2px; }
}
```

### `tailwind.config.ts`
```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./templates/**/*.{html,js}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper:   { DEFAULT:"#F4EEE1", 2:"#EBE3D2" },
        ink:     { DEFAULT:"#15120E", soft:"#3A342B" },
        muted:   "#7A7164",
        red:     { DEFAULT:"#F4322E", deep:"#CE241F" },
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans:    ['"Archivo"', "system-ui", "sans-serif"],
        mono:    ['"Space Mono"', "monospace"],
      },
      boxShadow: {
        hard:    "4px 4px 0 var(--ink)",
        "hard-lg":"8px 8px 0 var(--ink)",
        "hard-red":"7px 7px 0 var(--red)",
      },
      borderRadius: { none:"0" },
    },
  },
} satisfies Config;
```

### shadcn/ui — overrides
On part de shadcn pour la mécanique (a11y, slots) mais on **réécrit le style** :
- `Button` : créer les variants `red` (`bg-red text-paper border-2 border-ink shadow-hard`) et `ghost-poster` (`bg-paper text-ink border-2 border-ink shadow-hard`). `rounded-none`, font `sans` poids `800`, hover `-translate-x-0.5 -translate-y-0.5`.
- `Card` : `rounded-none border-2 border-ink bg-paper`, hover `shadow-hard-red -translate-x-1 -translate-y-1`.
- `Badge` : `rounded-none font-mono uppercase tracking-wider text-xs border-2`. Deux styles : neutre (`border-ink bg-paper`) et rouge (`bg-red text-white border-white`).
- Désactiver tout arrondi par défaut de shadcn (`--radius: 0`).

---

## 7. Composant signature — `Waveform`

Motif d'oscilloscope dérivé du logo. Sert de bandeau hero, de séparateur, de fond du bloc adhésion. **Déterministe** (rendu stable au SSR), enveloppe en cloche (plus fort au centre, comme le logo), pulsation optionnelle, respecte `prefers-reduced-motion`.

`src/components/brand/Waveform.tsx`
```tsx
import { useEffect, useMemo, useRef } from "react";

interface WaveformProps {
  bars?: number;        // densité de barres
  height?: number;      // hauteur du viewBox
  baseline?: boolean;   // ligne médiane noire (façon logo)
  animated?: boolean;   // pulsation "live"
  className?: string;
}

export function Waveform({
  bars = 150,
  height = 120,
  baseline = true,
  animated = true,
  className,
}: WaveformProps) {
  const W = 1200;
  const cy = height / 2;

  // amplitudes déterministes (stable SSR) : bruit pseudo-aléatoire * enveloppe en cloche
  const amps = useMemo(() => {
    return Array.from({ length: bars }, (_, i) => {
      const env = Math.sin((i / bars) * Math.PI);                  // cloche centrale
      const rand = Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1);
      return (rand * 0.55 + 0.18) * env * (height * 0.46);
    });
  }, [bars, height]);

  const groupRef = useRef<SVGGElement>(null);

  useEffect(() => {
    if (!animated) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0, t = 0;
    const tick = () => {
      t += 1;
      const lines = groupRef.current?.children;
      if (lines) {
        for (let i = 0; i < lines.length; i++) {
          const s = 0.85 + 0.15 * Math.sin(t * 0.06 + i * 0.4);
          const a = amps[i] * s;
          const l = lines[i] as SVGLineElement;
          l.setAttribute("y1", (cy - a).toFixed(1));
          l.setAttribute("y2", (cy + a).toFixed(1));
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [animated, amps, cy]);

  return (
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none"
         className={className} aria-hidden="true">
      <g ref={groupRef} stroke="var(--red)" strokeWidth={2.4} strokeLinecap="round">
        {amps.map((a, i) => {
          const x = (i / bars) * W;
          return <line key={i} x1={x} y1={cy - a} x2={x} y2={cy + a} />;
        })}
      </g>
      {baseline && <line x1={0} y1={cy} x2={W} y2={cy} stroke="var(--ink)" strokeWidth={3} />}
    </svg>
  );
}
```
Usage hero : cadre `3px solid ink`, cartouches `432` (haut-gauche, serif 900) et `HZ` (bas-droite, mono letter-spacing `.4em`) qui chevauchent le cadre.

**Densité responsive** (cf §5.6) : passer `bars` selon la largeur — `useMemo`/`useEffect` sur un `matchMedia` ou un hook `useMediaQuery`, ex. `< 600px → 72`, `< 900px → 110`, sinon `150`. Hauteur du bandeau en `clamp(80px,16vw,120px)`. Ne pas animer si `prefers-reduced-motion: reduce` (déjà géré dans le composant).

---

## 8. Inventaire des composants

| Composant | Specs clés |
|---|---|
| **Ticker** | bandeau noir sticky-top, défilé mono uppercase, `+` rouge entre items, `@keyframes slide` (translateX -50%, ~28s linéaire infini). Dupliquer le contenu ×2 pour boucle continue. |
| **Header** | sticky, fond crème, `border-bottom 2px ink`. Logo + cartouche mono « Association culturelle · Annecy » (filet rouge à gauche). Menu : liens avec soulignement rouge animé au hover ; bouton « Adhérer » = `Button variant=red`. Burger ≤ 880px. |
| **Hero** | kicker mono rouge → H1 serif (italique rouge sur le mot fort) → lede → 2 CTA → **bande Waveform** → bandeau **stats**. Reveal en cascade au load. |
| **Stats** | grille 4 (→ 2×2 mobile), séparateurs = fond `ink` + cellules crème. Chiffres serif 900 (certains rouges), labels mono muted. Valeurs réelles : **81 adhérent·e·s · 22 bénévoles · 2021**. |
| **Feature (À l'affiche)** | 2 colonnes, `border 3px ink`, `shadow-hard-lg`. Média = aplat sombre + hachures rouges + badge type + grande date serif. Corps : type mono rouge, titre serif, méta en pastilles mono bordées, CTA rouge. |
| **Card** (agenda / archives) | média ratio 4/3 (fond sombre radial + placeholder pictogramme + badge), corps : date mono rouge, titre serif 600, desc muted, lieu mono. Hover = décollage + `shadow-hard-red`. |
| **News list** | lignes pleine largeur séparées par filets `2px ink`. Grille `date · (catégorie+titre) · flèche`. Hover : fond `paper-2` + décalage padding gauche. Flèche masquée mobile, lignes empilées. |
| **Bloc L'asso** | 2 colonnes : manifeste (titre serif, mot fort rouge italique) + liste des **3 missions** numérotées (mono rouge) séparées par filets. Missions = la trame statutaire (promotion spectacle vivant / manifestations / éducatif & préventif). |
| **CTA Adhérer** | section pleine `ink`, texte crème, titre serif géant (mot fort rouge italique), bouton rouge à ombre rouge. Waveform rouge translucide ancrée en bas. Brancher sur **HelloAsso**. |
| **Footer** | fond crème, 3 colonnes (logo+pitch / navigation / réseaux : Insta, Facebook, SoundCloud, contact). Barre basse mono : copyright + mentions légales/RGPD. |

---

## 9. Motion

- **Reveal au scroll** : `IntersectionObserver` (threshold ~`.12`), classe `.rv` → `.in`, `opacity 0→1` + `translateY(18px→0)`, `.6s ease`, délai en cascade (`i % 4 * 60ms`).
- **Pulsation onde** : voir `Waveform` (rAF, désactivée si reduced-motion).
- **Hover** : décollage `translate(-2..-3px)` + ombre agrandie, `.12–.14s`.
- **Ticker** : translation linéaire infinie.
- **Toujours** respecter `prefers-reduced-motion: reduce` (couper pulsation, ticker, reveals → état final immédiat).

---

## 10. Ton éditorial

- Tutoiement, chaleureux, direct, **inclusif** (« adhérent·e·s », « curieux·se »).
- Phrases courtes, énergiques. Verbes d'action (« On fait vibrer », « Adhère, fais du bruit »).
- Jamais de jargon. Festif mais crédible (mission éducative).
- Kickers mono en VO courte (« Du neuf », « Ça s'est passé chez nous »).

---

## 11. Garde-fous a11y / perf / RGPD

- Contraste : respecter §2 (rouge petit texte → `red-deep`).
- `:focus-visible` rouge visible sur **tous** les interactifs (les ombres dures ne suffisent pas).
- Images d'events : `alt` descriptifs, `loading="lazy"`, ratio fixe (anti CLS).
- Polices self-hosted (`@fontsource`) → pas d'appel Google côté client (RGPD).
- HelloAsso : chargement **click-to-load** (placeholder + bouton) tant qu'il n'y a pas de gestionnaire de consentement.
- Waveform : SVG léger, pas d'images lourdes pour le motif.

---

## 12. Arbo front conseillée
```
src/
  components/
    brand/      Waveform.tsx, Logo.tsx, Ticker.tsx
    ui/         (shadcn restylé : button, card, badge…)
    sections/   Hero.tsx, FeatureEvent.tsx, EventGrid.tsx,
                NewsList.tsx, ArchiveGrid.tsx, AssoBlock.tsx, JoinCta.tsx
    layout/     Header.tsx, Footer.tsx
  styles/       globals.css, tokens.css
```
Les sections sont des **composants React** rendus en **SSR** côté public et réutilisés tels quels dans l'aperçu de l'admin maison (un seul renderer de blocs, cf `ARCHITECTURE.md` §0). Le contenu (events, news, pages) vient de l'**API DRF** — le front ne fait que le rendu selon cette charte.

---

*Maquette de référence : `432hz-home.html`. En cas de doute sur une mesure, c'est elle qui fait foi.*
