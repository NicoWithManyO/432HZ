// Zone de dépôt stylée (drag & drop + aperçu) greffée sur un <input type="file">.
// Amélioration progressive partagée : médiathèque (gestion.js) et picker galerie (gallery.js).
// Sans JS, l'<input type="file"> natif reste pleinement fonctionnel.

const PROMPT = "Glissez une image ici ou cliquez pour parcourir";

// Greffe la zone de dépôt sur l'input ; renvoie une fonction de réinitialisation
// (vide le champ et remet l'invite/aperçu à zéro) pour l'appelant après un envoi.
export function enhanceDropzone(input, { promptText = PROMPT } = {}) {
  const dropzone = document.createElement("label");
  dropzone.className =
    "block border-2 border-dashed border-ink bg-paper-2 text-center cursor-pointer " +
    "py-8 px-4 font-mono uppercase tracking-[.1em] text-[.72rem] text-muted transition-colors";

  // Aperçu (masqué tant qu'aucune image n'est choisie) + libellé texte.
  const preview = document.createElement("img");
  preview.className = "mx-auto mb-3 max-h-48 w-auto border-2 border-ink";
  preview.hidden = true;
  const caption = document.createElement("span");
  caption.className = "block";
  caption.textContent = promptText;

  // On déplace l'input natif dans le label (clic = ouverture du sélecteur) et on le masque.
  input.classList.add("sr-only");
  input.before(dropzone);
  dropzone.append(preview, caption, input);

  let objectUrl = null;
  const showFile = () => {
    const file = input.files[0];
    // Libère l'URL objet précédente (évite la fuite mémoire).
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    if (file && file.type.startsWith("image/")) {
      objectUrl = URL.createObjectURL(file);
      preview.src = objectUrl;
      preview.hidden = false;
    } else {
      preview.hidden = true;
    }
    caption.textContent = file ? `Fichier choisi : ${file.name}` : promptText;
  };

  ["dragenter", "dragover"].forEach((type) =>
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add("border-red", "text-red");
    }),
  );
  ["dragleave", "drop"].forEach((type) =>
    dropzone.addEventListener(type, () => dropzone.classList.remove("border-red", "text-red")),
  );

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      showFile();
    }
  });

  input.addEventListener("change", showFile);

  return () => {
    input.value = "";
    showFile();
  };
}
