// Médiathèque : zone de dépôt (drag & drop + aperçu) sur le formulaire d'upload.
// La logique est partagée avec le picker galerie (cf dropzone.js).

import { enhanceDropzone } from "./dropzone.js";

const form = document.querySelector("[data-upload-form]");
const input = form?.querySelector('input[type="file"]');
if (input) enhanceDropzone(input);
