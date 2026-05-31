// Picker de galerie ordonnée (vanilla, amélioration progressive).
// Sources de vérité = deux champs cachés rendus par le formulaire :
//   - name="gallery" : CSV d'UUID ordonnés (la galerie) ;
//   - name="cover"   : UUID de l'image de couverture (marquée ★ dans la liste).
// Réordonnancement : boutons ▲ ▼ ✕ (base fiable, clavier + mobile) ET drag via Pointer
// Events (souris + tactile). Téléversement direct : POST AJAX (fichier + métadonnées) vers
// l'endpoint d'upload, qui crée le média et le renvoie ; on l'injecte alors dans le pool et
// la sélection. Sans JS, la galerie n'est pas éditable.

import { enhanceDropzone } from "./dropzone.js";

function mountGallery(container) {
  const form = container.closest("form");
  const input = form?.querySelector('[name="gallery"]');
  const coverInput = form?.querySelector('[name="cover"]');
  const selectedZone = container.querySelector("[data-gallery-selected]");
  const emptyHint = container.querySelector("[data-gallery-empty]");
  const coverHint = container.querySelector("[data-gallery-cover-hint]");
  const pool = container.querySelector("[data-gallery-pool]");
  if (!input || !selectedZone || !pool) return;

  // Métadonnées des images, indexées par id (alimentées par le pool + les uploads).
  const meta = new Map();

  function registerTile(tile) {
    meta.set(tile.dataset.imageId, {
      thumb: tile.dataset.thumb,
      label: tile.dataset.label,
      caption: tile.dataset.caption,
    });
    tile.addEventListener("click", () => toggle(tile.dataset.imageId));
  }

  pool.querySelectorAll("[data-image-id]").forEach(registerTile);

  // État : liste ordonnée d'ids (filtrée sur ce que la médiathèque connaît) + couverture.
  let selected = (input.value || "")
    .split(",")
    .map((id) => id.trim())
    .filter((id) => meta.has(id));
  let cover = coverInput?.value || "";
  // La couverture fait partie de la galerie : si elle n'y est pas (donnée ancienne), on l'y
  // ajoute au chargement plutôt que de la laisser effacer par syncInput().
  if (cover && meta.has(cover) && !selected.includes(cover)) selected.push(cover);

  function syncInput() {
    input.value = selected.join(",");
    // La couverture doit rester dans la galerie ; sinon on l'oublie.
    if (cover && !selected.includes(cover)) cover = "";
    if (coverInput) coverInput.value = cover;
    if (emptyHint) emptyHint.hidden = selected.length > 0;
    if (coverHint) coverHint.hidden = selected.length === 0;
    pool.querySelectorAll("[data-image-id]").forEach((tile) => {
      const on = selected.includes(tile.dataset.imageId);
      tile.classList.toggle("ring-4", on);
      tile.classList.toggle("ring-red", on);
    });
  }

  function move(id, delta) {
    const i = selected.indexOf(id);
    const j = i + delta;
    if (i < 0 || j < 0 || j >= selected.length) return;
    [selected[i], selected[j]] = [selected[j], selected[i]];
    render();
  }

  function toggle(id) {
    if (selected.includes(id)) selected = selected.filter((x) => x !== id);
    else selected.push(id);
    render();
  }

  function toggleCover(id) {
    cover = cover === id ? "" : id;
    render();
  }

  function toolButton(label, title, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.title = title;
    button.setAttribute("aria-label", title);
    button.className =
      "px-2 py-1 border-2 border-ink font-mono text-[.8rem] leading-none cursor-pointer";
    button.addEventListener("click", onClick);
    return button;
  }

  function render() {
    selectedZone.innerHTML = "";
    selected.forEach((id) => {
      const info = meta.get(id);
      const tile = document.createElement("div");
      tile.dataset.imageId = id;
      const isCover = cover === id;
      tile.className =
        "flex items-center gap-3 border-2 border-ink bg-paper p-2" +
        (isCover ? " ring-4 ring-red" : "");

      const handle = document.createElement("span");
      handle.textContent = "⠿";
      handle.title = "Glisser pour réordonner";
      handle.className = "cursor-grab touch-none select-none text-muted px-1";
      handle.addEventListener("pointerdown", (event) => startDrag(event, tile, handle));

      const thumb = document.createElement("img");
      thumb.src = info.thumb;
      thumb.alt = "";
      thumb.className = "w-16 h-12 object-cover border border-ink";

      const text = document.createElement("div");
      text.className = "flex-1 min-w-0";
      const label = document.createElement("div");
      label.className =
        "font-mono text-[.66rem] uppercase tracking-[.08em] text-muted truncate";
      label.textContent = info.label;
      text.append(label);
      if (info.caption) {
        const caption = document.createElement("div");
        caption.className = "text-[.78rem] text-ink-soft truncate";
        caption.textContent = info.caption;
        text.append(caption);
      }

      // Bouton couverture : ★ marqué (rouge plein) / ☆ non marqué.
      const coverBtn = toolButton(
        isCover ? "★" : "☆",
        isCover ? "Couverture (cliquer pour retirer)" : "Définir comme couverture",
        () => toggleCover(id),
      );
      coverBtn.setAttribute("aria-pressed", isCover ? "true" : "false");
      if (isCover) coverBtn.classList.add("bg-red", "text-paper");

      tile.append(
        handle,
        thumb,
        text,
        coverBtn,
        toolButton("▲", "Monter", () => move(id, -1)),
        toolButton("▼", "Descendre", () => move(id, 1)),
        toolButton("✕", "Retirer", () => toggle(id)),
      );
      selectedZone.append(tile);
    });
    syncInput();
  }

  // --- Drag (Pointer Events : souris + tactile) : on réordonne les nœuds du DOM,
  //     puis on resynchronise l'état depuis l'ordre obtenu. ---
  let dragTile = null;

  function startDrag(event, tile, handle) {
    if (event.button && event.button !== 0) return; // souris : bouton gauche seul
    event.preventDefault();
    dragTile = tile;
    tile.classList.add("opacity-60");
    handle.setPointerCapture(event.pointerId);
    handle.addEventListener("pointermove", onDragMove);
    handle.addEventListener("pointerup", endDrag, { once: true });
    handle.addEventListener("pointercancel", endDrag, { once: true });
  }

  function onDragMove(event) {
    if (!dragTile) return;
    const others = [...selectedZone.querySelectorAll("[data-image-id]")].filter(
      (t) => t !== dragTile,
    );
    const next = others.find((t) => {
      const rect = t.getBoundingClientRect();
      return event.clientY < rect.top + rect.height / 2;
    });
    selectedZone.insertBefore(dragTile, next || null);
  }

  function endDrag(event) {
    if (!dragTile) return;
    dragTile.classList.remove("opacity-60");
    dragTile = null;
    event.currentTarget.removeEventListener("pointermove", onDragMove);
    // L'ordre DOM fait foi après un drag.
    selected = [...selectedZone.querySelectorAll("[data-image-id]")].map(
      (t) => t.dataset.imageId,
    );
    syncInput();
  }

  // --- Téléversement direct (AJAX) : fichier + métadonnées (alt / titre / légende) ---
  const uploadUrl = container.dataset.uploadUrl;
  const csrf = form?.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const fileField = container.querySelector("[data-gallery-upload-file]");
  const altField = container.querySelector("[data-gallery-upload-alt]");
  const titleField = container.querySelector("[data-gallery-upload-title]");
  const captionField = container.querySelector("[data-gallery-upload-caption]");
  const submitBtn = container.querySelector("[data-gallery-upload-submit]");
  const uploadError = container.querySelector("[data-gallery-upload-error]");
  // Même zone de dépôt stylée (drag & drop + aperçu) que la médiathèque.
  const resetDropzone = fileField ? enhanceDropzone(fileField) : null;

  function addPoolImage(item) {
    const empty = pool.querySelector("p"); // retire le « médiathèque vide » s'il est là
    if (empty) empty.remove();
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "block border-2 border-ink overflow-hidden text-left";
    tile.dataset.imageId = item.id;
    tile.dataset.thumb = item.thumb;
    tile.dataset.label = item.label;
    tile.dataset.caption = item.caption || "";
    const img = document.createElement("img");
    img.src = item.thumb;
    img.alt = item.label;
    img.loading = "lazy";
    img.className = "w-full aspect-[4/3] object-cover";
    tile.append(img);
    pool.append(tile);
    registerTile(tile);
  }

  function showUploadError(message) {
    if (!uploadError) return;
    uploadError.textContent = message;
    uploadError.hidden = false;
  }

  if (submitBtn && fileField && uploadUrl) {
    submitBtn.addEventListener("click", async () => {
      const file = fileField.files[0];
      if (uploadError) uploadError.hidden = true;
      if (!file) {
        showUploadError("Choisis d'abord un fichier image.");
        return;
      }
      submitBtn.disabled = true;
      const data = new FormData();
      data.append("file", file);
      data.append("alt", altField?.value || "");
      data.append("title", titleField?.value || "");
      data.append("caption", captionField?.value || "");
      try {
        const response = await fetch(uploadUrl, {
          method: "POST",
          headers: { "X-CSRFToken": csrf },
          body: data,
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          const detail = payload.errors?.file?.[0] || "Téléversement refusé.";
          throw new Error(detail);
        }
        const item = await response.json();
        addPoolImage(item);
        selected.push(item.id);
        render();
        // Réinitialise le panneau pour un prochain envoi.
        if (resetDropzone) resetDropzone();
        [altField, titleField, captionField].forEach((f) => {
          if (f) f.value = "";
        });
      } catch (error) {
        showUploadError(error.message);
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  render();
}

document.querySelectorAll("[data-gallery]").forEach(mountGallery);
