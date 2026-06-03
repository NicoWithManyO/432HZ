// JS de layout — vanilla, minimal, progressif. Le contenu reste utilisable sans JS.
// Branche : montage des Waveform, menu mobile (overlay), reveals au scroll.
import { mountWaveforms } from "./waveform.js";

// Signale que JS est actif (les reveals ne masquent le contenu que dans ce cas).
document.documentElement.classList.add("js");

mountWaveforms();

// --- Menu mobile (overlay plein écran, cf DESIGN.md §5.5) ---
const burger = document.querySelector("[data-burger]");
const menu = document.getElementById("mobile-menu");

if (burger && menu) {
  const setOpen = (open) => {
    burger.classList.toggle("is-open", open);
    menu.classList.toggle("is-open", open);
    burger.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-hidden", String(!open));
    document.body.style.overflow = open ? "hidden" : ""; // verrou du scroll
  };

  burger.addEventListener("click", () => setOpen(!menu.classList.contains("is-open")));
  menu.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });
  // Repasse en desktop : on referme et on rétablit le scroll.
  window.matchMedia("(min-width: 881px)").addEventListener("change", (e) => {
    if (e.matches) setOpen(false);
  });
}

// --- Bandeau défilant (ticker) : remplissage + clonage pour un défilement sans raccord ---
// La séquence rendue côté serveur est d'abord complétée jusqu'à dépasser la largeur visible
// (pas de vide à droite même avec peu d'items), puis dupliquée : la piste = 2 séquences
// identiques, et le keyframe translate de -50% boucle de façon invisible (cf globals.css).
const ticker = document.querySelector("[data-ticker]");
if (ticker) {
  const track = ticker.querySelector("[data-ticker-track]");
  const seq = ticker.querySelector("[data-ticker-seq]");
  if (track && seq && seq.children.length) {
    const SPEED = 60; // vitesse de défilement en px/s
    const base = Array.from(seq.children).map((node) => node.cloneNode(true));
    // 1. Remplit la séquence tant qu'elle ne couvre pas la largeur visible. Garde-fou
    //    `passes` : si les clones mesuraient 0px (CSS pas encore appliqué), la boucle
    //    ne tournerait pas indéfiniment.
    let passes = 0;
    while (seq.scrollWidth < ticker.offsetWidth && passes < 50) {
      base.forEach((node) => seq.appendChild(node.cloneNode(true)));
      passes += 1;
    }
    // 2. Duplique la séquence entière (la 2e copie sert de tampon pour la boucle).
    const seqWidth = seq.scrollWidth;
    track.appendChild(seq.cloneNode(true));
    // 3. Durée = largeur / vitesse (cadence constante), puis active l'animation.
    track.style.animationDuration = `${seqWidth / SPEED}s`;
    track.classList.add("ticker--running");
  }
}

// --- Click-to-load des embeds tiers (RGPD) ---
// Aucun appel au service tiers tant que l'utilisateur n'a pas cliqué : au clic, on injecte
// l'iframe depuis `data-src` et on retire le placeholder. Plusieurs embeds peuvent coexister
// sur une page (formulaire HelloAsso, vidéo de l'accueil…), chacun configuré par ses
// data-attributs (titre, classe d'iframe, permissions, plein écran).
document.querySelectorAll("[data-embed]").forEach((embed) => {
  const embedLoad = embed.querySelector("[data-embed-load]");
  if (!embedLoad) return;
  embedLoad.addEventListener("click", () => {
    const src = embed.dataset.src;
    if (!src) return; // pas d'URL configurée → on ne touche à rien
    const iframe = document.createElement("iframe");
    iframe.src = src;
    iframe.loading = "lazy";
    // La politique referrer du site est `same-origin` : sans referer, YouTube refuse la
    // lecture (erreur 153). On envoie juste l'origine en cross-origin (RGPD : pas l'URL
    // complète), ce qui suffit au lecteur tiers et débloque la lecture.
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.title = embed.dataset.embedTitle || "Contenu intégré";
    iframe.className = embed.dataset.embedClass || "w-full min-h-[640px] border-0";
    if (embed.dataset.embedAllow) iframe.allow = embed.dataset.embedAllow;
    if ("embedFullscreen" in embed.dataset) iframe.allowFullscreen = true;
    embed.replaceChildren(iframe);
  });
});

// --- Carrousel de photos (accueil) : auto + flèches + points, vanilla, accessible ---
// Défilement auto seulement si `data-carousel-auto` ET hors prefers-reduced-motion. L'auto
// se met en pause au survol/focus. Sans JS, la 1re photo reste visible (les autres masquées).
document.querySelectorAll("[data-carousel]").forEach((carousel) => {
  const slides = [...carousel.querySelectorAll("[data-carousel-slide]")];
  if (slides.length < 2) return;
  const dots = [...carousel.querySelectorAll("[data-carousel-dot]")];
  let index = 0;
  let timer = null;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const auto = carousel.hasAttribute("data-carousel-auto") && !reduced;

  const rearm = () => {
    if (!auto) return;
    clearInterval(timer);
    timer = setInterval(() => show(index + 1), 5000);
  };

  const show = (i) => {
    index = (i + slides.length) % slides.length;
    slides.forEach((slide, k) => {
      const on = k === index;
      slide.classList.toggle("opacity-0", !on);
      slide.classList.toggle("pointer-events-none", !on);
    });
    dots.forEach((dot, k) =>
      dot.setAttribute("aria-current", k === index ? "true" : "false"),
    );
  };

  carousel
    .querySelector("[data-carousel-prev]")
    ?.addEventListener("click", () => {
      show(index - 1);
      rearm();
    });
  carousel
    .querySelector("[data-carousel-next]")
    ?.addEventListener("click", () => {
      show(index + 1);
      rearm();
    });
  dots.forEach((dot, k) =>
    dot.addEventListener("click", () => {
      show(k);
      rearm();
    }),
  );

  if (auto) {
    carousel.addEventListener("mouseenter", () => clearInterval(timer));
    carousel.addEventListener("mouseleave", rearm);
    carousel.addEventListener("focusin", () => clearInterval(timer));
    carousel.addEventListener("focusout", rearm);
  }

  show(0);
  rearm();
});

// --- Reveals au scroll (IntersectionObserver) ---
const revealables = document.querySelectorAll(".rv");
if (revealables.length && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.remove("pending");
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealables.forEach((el) => {
    el.classList.add("pending"); // masqué jusqu'à l'entrée dans le viewport
    observer.observe(el);
  });
}
