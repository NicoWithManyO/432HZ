/* Composant signature « Waveform » — version vanilla JS (monolithe, pas de React).
 * Motif d'oscilloscope dérivé du logo : enveloppe en cloche (plus fort au centre),
 * amplitudes DÉTERMINISTES (rendu stable), pulsation optionnelle, densité adaptative,
 * respect strict de prefers-reduced-motion. Sert de bandeau hero, séparateur, fond
 * du bloc adhésion. Cf DESIGN.md §7.
 *
 * Usage HTML :
 *   <div class="waveform" data-baseline="true" data-animated="true"></div>
 *   <script type="module">
 *     import { mountWaveforms } from "/static/js/waveform.js";
 *     mountWaveforms();
 *   </script>
 *
 * Le SVG s'étire en pleine largeur (preserveAspectRatio="none"). Hauteur du bandeau
 * gérée en CSS : height: clamp(80px, 16vw, 120px).
 */

const SVG_NS = "http://www.w3.org/2000/svg";
const VIEW_W = 1200;

// Densité de barres selon la largeur (sinon barres tassées sur mobile).
function barsForWidth(width) {
  if (width < 600) return 72;
  if (width < 900) return 110;
  return 150;
}

// Amplitudes déterministes : bruit pseudo-aléatoire * enveloppe en cloche centrale.
function computeAmps(bars, height) {
  const amps = new Array(bars);
  for (let i = 0; i < bars; i++) {
    const env = Math.sin((i / bars) * Math.PI); // cloche : 0 aux bords, 1 au centre
    const rand = Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1);
    amps[i] = (rand * 0.55 + 0.18) * env * (height * 0.46);
  }
  return amps;
}

function buildSvg(container) {
  const height = 120;
  const cy = height / 2;
  const baseline = container.dataset.baseline !== "false";
  const animated = container.dataset.animated !== "false";

  const width = container.clientWidth || 1200;
  const bars = barsForWidth(width);
  const amps = computeAmps(bars, height);

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${VIEW_W} ${height}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  svg.style.width = "100%";
  svg.style.height = "100%";
  svg.style.display = "block";

  const group = document.createElementNS(SVG_NS, "g");
  group.setAttribute("stroke", "var(--red)");
  group.setAttribute("stroke-width", "2.4");
  group.setAttribute("stroke-linecap", "round");

  for (let i = 0; i < bars; i++) {
    const x = (i / bars) * VIEW_W;
    const a = amps[i];
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("x1", x.toFixed(1));
    line.setAttribute("y1", (cy - a).toFixed(1));
    line.setAttribute("x2", x.toFixed(1));
    line.setAttribute("y2", (cy + a).toFixed(1));
    group.appendChild(line);
  }
  svg.appendChild(group);

  if (baseline) {
    const mid = document.createElementNS(SVG_NS, "line");
    mid.setAttribute("x1", "0");
    mid.setAttribute("y1", String(cy));
    mid.setAttribute("x2", String(VIEW_W));
    mid.setAttribute("y2", String(cy));
    mid.setAttribute("stroke", "var(--ink)");
    mid.setAttribute("stroke-width", "3");
    svg.appendChild(mid);
  }

  container.replaceChildren(svg);

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (animated && !reduce) startPulse(group, amps, cy);
}

// Pulsation « live » : modulation lente de chaque barre via requestAnimationFrame.
function startPulse(group, amps, cy) {
  const lines = group.children;
  let t = 0;
  function tick() {
    t += 1;
    for (let i = 0; i < lines.length; i++) {
      const s = 0.85 + 0.15 * Math.sin(t * 0.06 + i * 0.4);
      const a = amps[i] * s;
      lines[i].setAttribute("y1", (cy - a).toFixed(1));
      lines[i].setAttribute("y2", (cy + a).toFixed(1));
    }
    group._raf = requestAnimationFrame(tick);
  }
  group._raf = requestAnimationFrame(tick);
}

// Reconstruit au resize (densité adaptative), avec debounce ~180ms.
let resizeTimer = null;
function scheduleRebuild(containers) {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => containers.forEach(buildSvg), 180);
}

export function mountWaveforms(selector = ".waveform") {
  const containers = Array.from(document.querySelectorAll(selector));
  if (containers.length === 0) return;
  containers.forEach(buildSvg);
  window.addEventListener("resize", () => scheduleRebuild(containers));
}
