// Preview helper: draws the chart as an SVG file so the layout can be checked without a browser.
//   node scripts/render-chart.mjs chart.json out.svg
import { readFileSync, writeFileSync } from "node:fs";

import { layoutChart } from "../lib/chartGeometry.mjs";

const chart = JSON.parse(readFileSync(process.argv[2], "utf8"));
const layout = layoutChart(chart);
const selected = Number(process.argv[4] || 0);

const houses = layout.map((h) => `<polygon points="${h.points}" fill="${h.number === selected ? "#7a2a62" : "#1a1228"}" stroke="#f3b04c" stroke-width="1.4"/>`).join("");
const signs = layout.map((h) => `<text x="${h.signX}" y="${h.signY}" fill="#b9a9c6" font-size="10" text-anchor="middle">${h.signNumber}</text>`).join("");
const planets = layout.flatMap((h) => h.planets.map((p) => `<text x="${p.x}" y="${p.y}" fill="#f5ecf8" font-size="13" font-weight="600" text-anchor="middle">${p.abbr}</text>`)).join("");

writeFileSync(process.argv[3], `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="600" height="600"><rect width="300" height="300" fill="#0b0713"/>${houses}${signs}${planets}</svg>`);
