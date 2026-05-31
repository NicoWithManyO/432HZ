// Médiathèque : glisser-déposer sur le champ fichier (amélioration progressive).
// Sans JS, l'<input type="file"> natif reste pleinement fonctionnel.

const form = document.querySelector("[data-upload-form]");
const input = form?.querySelector('input[type="file"]');

if (input) {
  const dropzone = document.createElement("label");
  dropzone.className =
    "block border-2 border-dashed border-ink bg-paper-2 text-center cursor-pointer " +
    "py-8 px-4 font-mono uppercase tracking-[.1em] text-[.72rem] text-muted transition-colors";
  dropzone.textContent = "Glissez une image ici ou cliquez pour parcourir";

  // On déplace l'input natif dans le label (clic = ouverture du sélecteur) et on le masque.
  input.classList.add("sr-only");
  input.before(dropzone);
  dropzone.append(input);

  const setLabel = () => {
    const file = input.files[0];
    dropzone.firstChild.textContent = file
      ? `Fichier choisi : ${file.name}`
      : "Glissez une image ici ou cliquez pour parcourir";
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
      setLabel();
    }
  });

  input.addEventListener("change", setLabel);
}
