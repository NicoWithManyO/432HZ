/** Config Tailwind de la charte 432 Hz (monolithe Django).
 *  Les couleurs/ombres pointent sur les CSS vars de tokens.css (source unique).
 *  `content` scanne les templates Django + le JS éventuel. Adapter les chemins au
 *  vrai layout du projet (ex. apps/*/templates, theme/static_src/...).
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: "#F4EEE1", 2: "#EBE3D2" },
        ink: { DEFAULT: "#15120E", soft: "#3A342B" },
        muted: "#7A7164",
        red: { DEFAULT: "#F4322E", deep: "#CE241F" },
        line: "rgba(21,18,14,.16)",
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"Archivo"', "system-ui", "sans-serif"],
        mono: ['"Space Mono"', "monospace"],
      },
      // Ombres « affiche » : offset dur, blur = 0. Jamais de blur.
      boxShadow: {
        hard: "4px 4px 0 var(--ink)",
        "hard-lg": "8px 8px 0 var(--ink)",
        "hard-red": "7px 7px 0 var(--red)",
      },
      borderRadius: { none: "0" }, // radius 0 partout — aucun arrondi
    },
  },
  plugins: [],
};
