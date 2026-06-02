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
