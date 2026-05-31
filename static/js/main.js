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
