// Îlot d'édition riche (Tiptap) greffé sur les <textarea data-richtext> de la gestion.
// Amélioration progressive : sans JS, le <textarea> natif reste pleinement utilisable.
// On ne produit que l'allowlist de `apps/common/sanitize.py`, et le HTML est de toute
// façon re-sanitizé côté serveur (nh3) au save : le client n'est jamais la barrière.

import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

// Pose / retire un lien via une simple invite (pas d'UI dédiée en v1).
function toggleLink(editor) {
  const previous = editor.getAttributes("link").href;
  const answer = window.prompt("Adresse du lien", previous || "https://");
  if (answer === null) return; // invite annulée : on ne touche à rien
  const url = answer.trim();
  const chain = editor.chain().focus().extendMarkRange("link");
  // Vide ou placeholder laissé tel quel ⇒ on retire le lien (jamais de href « https:// » seul).
  if (url === "" || url === "https://") {
    chain.unsetLink().run();
  } else {
    chain.setLink({ href: url }).run();
  }
}

// Barre d'outils : libellé, action, et test d'état actif (pour le reflet visuel).
const TOOLS = [
  { label: "Gras", run: (e) => e.chain().focus().toggleBold().run(), active: (e) => e.isActive("bold") },
  { label: "Ital.", run: (e) => e.chain().focus().toggleItalic().run(), active: (e) => e.isActive("italic") },
  { label: "H2", run: (e) => e.chain().focus().toggleHeading({ level: 2 }).run(), active: (e) => e.isActive("heading", { level: 2 }) },
  { label: "H3", run: (e) => e.chain().focus().toggleHeading({ level: 3 }).run(), active: (e) => e.isActive("heading", { level: 3 }) },
  { label: "Liste", run: (e) => e.chain().focus().toggleBulletList().run(), active: (e) => e.isActive("bulletList") },
  { label: "1. Liste", run: (e) => e.chain().focus().toggleOrderedList().run(), active: (e) => e.isActive("orderedList") },
  { label: "Lien", run: toggleLink, active: (e) => e.isActive("link") },
];

function mountEditor(textarea) {
  const wrap = document.createElement("div");
  wrap.className = "border-2 border-ink bg-paper";
  const toolbar = document.createElement("div");
  toolbar.className = "flex flex-wrap gap-1 p-2 border-b-2 border-ink bg-paper-2";
  const mount = document.createElement("div");
  wrap.append(toolbar, mount);

  textarea.before(wrap);

  const editor = new Editor({
    element: mount,
    extensions: [
      StarterKit.configure({
        // Allowlist : on bride aux titres h2/h3 et on coupe ce qui produirait des
        // balises hors allowlist (codeBlock → <pre>, horizontalRule → <hr>,
        // hardBreak → <br> que nh3 strippe → fusion silencieuse des lignes).
        heading: { levels: [2, 3] },
        codeBlock: false,
        horizontalRule: false,
        hardBreak: false,
        link: { openOnClick: false, autolink: true, HTMLAttributes: { rel: "noopener" } },
      }),
    ],
    content: textarea.value,
    editorProps: {
      attributes: { class: "prose-editor p-3 min-h-[8rem] focus:outline-none" },
    },
    onUpdate: ({ editor }) => syncTo(textarea, editor),
  });

  // Montage réussi : le <textarea> (qui porte le name du champ) reste dans le DOM
  // mais masqué. Si `new Editor` avait échoué, il serait resté visible (fallback).
  textarea.classList.add("sr-only");
  textarea.setAttribute("aria-hidden", "true");
  textarea.setAttribute("tabindex", "-1");

  const buttons = TOOLS.map((tool) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = tool.label;
    button.className =
      "px-2 py-1 border-2 border-ink font-mono text-[.7rem] uppercase tracking-[.06em] cursor-pointer";
    button.addEventListener("click", () => tool.run(editor));
    toolbar.append(button);
    return { button, tool };
  });

  const refresh = () =>
    buttons.forEach(({ button, tool }) => {
      const on = tool.active(editor);
      button.classList.toggle("bg-ink", on);
      button.classList.toggle("text-paper", on);
    });
  editor.on("selectionUpdate", refresh);
  editor.on("transaction", refresh);
  refresh();

  // Filet de sécurité : resynchronise juste avant l'envoi du formulaire.
  textarea.form?.addEventListener("submit", () => syncTo(textarea, editor));
}

// Un éditeur vide rend "<p></p>" : on stocke alors une chaîne vide (champ optionnel).
function syncTo(textarea, editor) {
  textarea.value = editor.isEmpty ? "" : editor.getHTML();
}

document.querySelectorAll("textarea[data-richtext]").forEach(mountEditor);
