// Pipeline PostCSS du build front. postcss-import inline les @import (tokens, fonts)
// AVANT que Tailwind ne traite ses directives ; autoprefixer en sortie.
export default {
  plugins: {
    "postcss-import": {},
    tailwindcss: {},
    autoprefixer: {},
  },
};
