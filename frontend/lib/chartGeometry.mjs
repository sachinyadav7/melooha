import { signNumber } from "./signs.mjs";

// North Indian chart on a 300 x 300 square. House 1 is the top diamond and the houses
// run anticlockwise. Points: corners A B C D, edge midpoints, inner points P1..P4, centre O.
const A = [0, 0], B = [300, 0], C = [300, 300], D = [0, 300];
const T = [150, 0], R = [300, 150], Bt = [150, 300], L = [0, 150];
const P1 = [75, 75], P2 = [225, 75], P3 = [225, 225], P4 = [75, 225];
const O = [150, 150];

export const HOUSE_POLYGONS = {
  1: [T, P1, O, P2],
  2: [A, T, P1],
  3: [A, P1, L],
  4: [L, P1, O, P4],
  5: [L, P4, D],
  6: [D, P4, Bt],
  7: [Bt, P4, O, P3],
  8: [Bt, P3, C],
  9: [C, P3, R],
  10: [R, P3, O, P2],
  11: [R, P2, B],
  12: [B, P2, T],
};

export const ABBR = {
  SUN: "Su", MOON: "Mo", MARS: "Ma", MERCURY: "Me", JUPITER: "Ju",
  VENUS: "Ve", SATURN: "Sa", RAHU: "Ra", KETU: "Ke",
};

export function polygonArea(points) {
  let sum = 0;
  points.forEach(([x1, y1], i) => {
    const [x2, y2] = points[(i + 1) % points.length];
    sum += x1 * y2 - x2 * y1;
  });
  return Math.abs(sum) / 2;
}

const average = (points) => [
  points.reduce((s, p) => s + p[0], 0) / points.length,
  points.reduce((s, p) => s + p[1], 0) / points.length,
];

const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

const ROW_HEIGHT = 15;
const COLUMN_WIDTH = 28;

// Side triangles (3, 5, 9, 11) are tall and thin, so their planets stack in one column.
// Top and bottom triangles (2, 6, 8, 12) fit two planets side by side. Diamonds fit three.
const SIDE_TRIANGLES = new Set([3, 5, 9, 11]);

function planetsPerRow(houseNumber, isDiamond) {
  if (isDiamond) return 3;
  return SIDE_TRIANGLES.has(houseNumber) ? 1 : 2;
}

/** Turns the chart from the API into everything needed to draw it. Shared by the page and the preview script. */
export function layoutChart(chart) {
  const planetsByHouse = {};
  for (const planet of chart.planets) {
    (planetsByHouse[planet.house] ||= []).push(planet);
  }

  return chart.houses.map((house) => {
    const polygon = HOUSE_POLYGONS[house.number];
    const isDiamond = polygon.length === 4;
    const centre = average(polygon);
    // The sign number sits by the corner nearest the middle of the chart, away from the planets.
    const inner = [...polygon].sort((a, b) => distance(a, O) - distance(b, O))[0];
    const signPosition = lerp(inner, centre, isDiamond ? 0.25 : 0.3);

    const perRow = planetsPerRow(house.number, isDiamond);
    const planets = planetsByHouse[house.number] || [];
    const rowCount = Math.ceil(planets.length / perRow);

    const placed = planets.map((planet, index) => {
      const row = Math.floor(index / perRow);
      const column = index % perRow;
      const inThisRow = Math.min(perRow, planets.length - row * perRow);
      return {
        key: planet.key,
        abbr: ABBR[planet.key],
        x: centre[0] + (column - (inThisRow - 1) / 2) * COLUMN_WIDTH,
        y: centre[1] + (row - (rowCount - 1) / 2) * ROW_HEIGHT + 4,
      };
    });

    return {
      number: house.number,
      sign: house.sign,
      label: house.label,
      points: polygon.map((p) => p.join(",")).join(" "),
      signNumber: signNumber(house.sign),
      signX: signPosition[0],
      signY: signPosition[1] + 3,
      planets: placed,
    };
  });
}
