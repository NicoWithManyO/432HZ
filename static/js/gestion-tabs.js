// Onglets du tableau de bord — pattern ARIA « tablist », amélioration progressive.
// Sans JS, tous les panneaux restent visibles (contenu accessible) ; au montage, on
// masque les panneaux inactifs et on câble clic + clavier (← →, Début, Fin).
const tablist = document.querySelector("[data-tabs]");
if (tablist) {
  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
  const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));

  const select = (index, { focus = false } = {}) => {
    tabs.forEach((tab, i) => {
      const selected = i === index;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1; // roving tabindex : un seul onglet tabbable
      if (panels[i]) panels[i].hidden = !selected;
    });
    if (focus) tabs[index].focus();
  };

  // État initial : l'ancre d'URL #tab-xxx (retour d'un POST de contenu) prime, puis
  // l'onglet marqué aria-selected dans le HTML, sinon le premier.
  const fromHash = location.hash
    ? tabs.findIndex((t) => `#${t.id}` === location.hash)
    : -1;
  const marked = tabs.findIndex((t) => t.getAttribute("aria-selected") === "true");
  const initial = fromHash >= 0 ? fromHash : marked;
  select(initial >= 0 ? initial : 0);

  tablist.addEventListener("click", (e) => {
    const tab = e.target.closest('[role="tab"]');
    if (tab) select(tabs.indexOf(tab));
  });

  tablist.addEventListener("keydown", (e) => {
    const current = tabs.findIndex((t) => t.getAttribute("aria-selected") === "true");
    let next;
    if (e.key === "ArrowRight") next = (current + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    select(next, { focus: true });
  });
}

// Confort d'édition : un enregistrement passe par POST→redirect (rechargement complet) qui
// referme les accordéons et renvoie le scroll en haut. On restaure les deux via sessionStorage
// pour que l'éditeur ne perde pas sa place. Amélioration progressive : sans JS, comportement
// par défaut (accordéons fermés, scroll en haut) — rien ne casse.
const ACC_KEY = "gestion-open-accordions";
const SCROLL_KEY = "gestion-scroll";
const accordions = Array.from(document.querySelectorAll("details.gestion-accordion"));

if (accordions.length) {
  // Clé stable d'un accordéon = id du panneau + libellé (unique au sein d'un panneau),
  // robuste au réordonnancement des items d'une liste (qui ne change pas l'ordre des blocs).
  const keyOf = (d) => {
    const panel = d.closest('[role="tabpanel"]');
    const summary = d.querySelector("summary");
    return `${panel ? panel.id : ""}::${summary ? summary.textContent.trim() : ""}`;
  };
  const readOpen = () => {
    try {
      return new Set(JSON.parse(sessionStorage.getItem(ACC_KEY)) || []);
    } catch {
      return new Set();
    }
  };
  // Rouvre les accordéons mémorisés (avant la restauration du scroll : la hauteur en dépend).
  const open = readOpen();
  accordions.forEach((d) => {
    if (open.has(keyOf(d))) d.open = true;
  });
  // Listeners posés APRÈS les ouvertures programmatiques ci-dessus → pas d'événement parasite.
  accordions.forEach((d) => {
    d.addEventListener("toggle", () => {
      const set = readOpen();
      if (d.open) set.add(keyOf(d));
      else set.delete(keyOf(d));
      sessionStorage.setItem(ACC_KEY, JSON.stringify([...set]));
    });
  });
}

// Mémorise la position de scroll juste avant tout enregistrement (y compris les boutons
// d'icône monter/descendre/supprimer), restaurée une seule fois au rechargement suivant.
document.addEventListener("submit", () => {
  sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
});
const savedScroll = sessionStorage.getItem(SCROLL_KEY);
if (savedScroll !== null) {
  sessionStorage.removeItem(SCROLL_KEY);
  // Après le rendu (accordéons rouverts + éventuel saut d'ancre #tab-…) → on repositionne.
  requestAnimationFrame(() => window.scrollTo(0, parseInt(savedScroll, 10)));
}
