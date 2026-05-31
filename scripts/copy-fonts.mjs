// Copie les woff2 self-hosted depuis @fontsource vers static/fonts/ (RGPD : pas d'appel
// Google Fonts côté client). Sous-ensemble latin uniquement, poids réellement utilisés
// par la charte (cf DESIGN.md §3). Lancé par `npm run fonts`.

import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dest = join(root, "static", "fonts");
mkdirSync(dest, { recursive: true });

// [package, [fichiers woff2 (sous-ensemble latin)]]
const FONTS = [
  ["@fontsource/fraunces", [
    "fraunces-latin-400-normal.woff2",
    "fraunces-latin-400-italic.woff2",
    "fraunces-latin-600-normal.woff2",
    "fraunces-latin-600-italic.woff2",
    "fraunces-latin-900-normal.woff2",
    "fraunces-latin-900-italic.woff2",
  ]],
  ["@fontsource/archivo", [
    "archivo-latin-400-normal.woff2",
    "archivo-latin-500-normal.woff2",
    "archivo-latin-600-normal.woff2",
    "archivo-latin-800-normal.woff2",
  ]],
  ["@fontsource/space-mono", [
    "space-mono-latin-400-normal.woff2",
    "space-mono-latin-700-normal.woff2",
  ]],
];

let count = 0;
for (const [pkg, files] of FONTS) {
  for (const file of files) {
    copyFileSync(join(root, "node_modules", pkg, "files", file), join(dest, file));
    count++;
  }
}
console.log(`Fonts copiées : ${count} fichiers -> static/fonts/`);
