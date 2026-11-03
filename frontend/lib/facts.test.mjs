import assert from "node:assert/strict";
import test from "node:test";

import { describeSelection, parseFactId, splitAnswer, stripMarkers, targetForFact } from "./facts.mjs";

const chart = {
  planets: [
    { key: "SATURN", name: "Saturn", meaning: "Discipline, delays and long-term effort", sign: "Aries", house: 10, retrograde: false },
    { key: "MOON", name: "Moon", meaning: "Your mind and moods", sign: "Leo", house: 2, retrograde: false, nakshatra: "Magha" },
  ],
  houses: Array.from({ length: 12 }, (_, i) => ({ number: i + 1, sign: "Cancer", label: `Area ${i + 1}` })),
  facts: [{ id: "P_SATURN_H10", text: "Saturn is in house 10 (Career and status)." }],
};

test("fact IDs point at the right planet and house", () => {
  assert.deepEqual(parseFactId("P_SATURN_H10"), { planet: "SATURN", house: 10 });
  assert.deepEqual(parseFactId("ASC_CANCER"), { house: 1 });
  assert.deepEqual(parseFactId("MOON_NAK_MAGHA"), { planet: "MOON" });
  assert.deepEqual(parseFactId("nonsense"), {});
});

test("a sign fact finds its house from the chart", () => {
  assert.deepEqual(targetForFact("P_SATURN_S_ARIES", chart), { planet: "SATURN", house: 10 });
});

test("answers split into text and fact chips", () => {
  const parts = splitAnswer("Saturn is strong. [[P_SATURN_H10]] Work steadily.");
  assert.deepEqual(parts.map((p) => p.type), ["text", "fact", "text"]);
  assert.equal(parts[1].id, "P_SATURN_H10");
});

test("a half-written marker is hidden while streaming", () => {
  assert.equal(splitAnswer("Saturn is strong. [[P_SAT", { streaming: true }).map((p) => p.value).join(""), "Saturn is strong. ");
  assert.equal(splitAnswer("Saturn is strong. [", { streaming: true }).length, 1);
  assert.equal(splitAnswer("Done. [[P_SATURN_H10]]", { streaming: true }).filter((p) => p.type === "fact").length, 1);
});

test("markers are removed for users without the chart", () => {
  assert.equal(stripMarkers("Saturn is strong. [[P_SATURN_H10]] Work steadily. [[ASC_CANCER]]"), "Saturn is strong. Work steadily.");
  assert.equal(stripMarkers("Saturn is strong. [[P_SAT", { streaming: true }), "Saturn is strong.");
});

test("selection text is plain language", () => {
  const planet = describeSelection(chart, { planet: "SATURN" });
  assert.equal(planet.title, "Saturn");
  assert.ok(planet.lines[1].includes("house 10 (Area 10)"));
  assert.ok(describeSelection(chart, { house: 1 }).lines.join(" ").includes("rising sign"));
  assert.equal(describeSelection(chart, null), null);
});
