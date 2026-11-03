import assert from "node:assert/strict";
import test from "node:test";

import { HOUSE_POLYGONS, layoutChart, polygonArea } from "./chartGeometry.mjs";

test("the 12 houses exactly fill the 300 x 300 square", () => {
  const total = Object.values(HOUSE_POLYGONS).reduce((sum, polygon) => sum + polygonArea(polygon), 0);
  assert.equal(Object.keys(HOUSE_POLYGONS).length, 12);
  assert.equal(total, 300 * 300);
});

test("diamonds are houses 1, 4, 7 and 10", () => {
  const diamonds = Object.entries(HOUSE_POLYGONS).filter(([, p]) => p.length === 4).map(([n]) => Number(n));
  assert.deepEqual(diamonds, [1, 4, 7, 10]);
});

test("planets land in their house with the sign number", () => {
  const chart = {
    houses: Array.from({ length: 12 }, (_, i) => ({ number: i + 1, sign: ["Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini"][i], label: "x" })),
    planets: [
      { key: "SUN", house: 10 }, { key: "MARS", house: 10 }, { key: "JUPITER", house: 10 }, { key: "SATURN", house: 10 },
      { key: "MOON", house: 2 },
    ],
  };
  const layout = layoutChart(chart);
  assert.equal(layout[0].signNumber, 4); // Cancer rising
  assert.equal(layout[9].planets.length, 4);
  assert.equal(layout[1].planets[0].abbr, "Mo");
  const xs = layout[9].planets.map((p) => p.x);
  assert.equal(new Set(xs.map((x, i) => `${x}-${layout[9].planets[i].y}`)).size, 4); // no two planets share a spot
});
