export const MARKER = /\[\[([A-Z0-9_]+)\]\]/g;

/** What a fact ID points at on the chart: a planet, a house, or both. */
export function parseFactId(id) {
  let m = /^P_([A-Z]+)_H(\d{1,2})$/.exec(id);
  if (m) return { planet: m[1], house: Number(m[2]) };
  m = /^P_([A-Z]+)_S_[A-Z]+$/.exec(id);
  if (m) return { planet: m[1] };
  if (id.startsWith("MOON_NAK_")) return { planet: "MOON" };
  if (id.startsWith("ASC_")) return { house: 1 };
  return {};
}

/** Chart target for a fact ID, filling in the house from the chart when the ID only names a planet. */
export function targetForFact(id, chart) {
  const target = parseFactId(id);
  if (target.planet && !target.house) {
    const planet = chart.planets.find((p) => p.key === target.planet);
    if (planet) target.house = planet.house;
  }
  return target;
}

export function factText(id, chart) {
  return chart.facts.find((f) => f.id === id)?.text ?? "";
}

/** Splits an answer into text and fact pieces. While streaming, a half-written marker is hidden. */
export function splitAnswer(text, { streaming = false } = {}) {
  let source = text;
  if (streaming) source = source.replace(/\[\[?[A-Z0-9_]*\]?$/, "");

  const parts = [];
  let last = 0;
  for (const match of source.matchAll(MARKER)) {
    if (match.index > last) parts.push({ type: "text", value: source.slice(last, match.index) });
    parts.push({ type: "fact", id: match[1] });
    last = match.index + match[0].length;
  }
  if (last < source.length) parts.push({ type: "text", value: source.slice(last) });
  return parts;
}

/** The answer as plain text, for users who do not see the chart (control group). */
export function stripMarkers(text, { streaming = false } = {}) {
  let source = text;
  if (streaming) source = source.replace(/\s*\[\[?[A-Z0-9_]*\]?$/, "");
  return source.replace(/\s*\[\[[A-Z0-9_]+\]\]/g, "").trim();
}

/** Plain-language explanation of what is selected on the chart. */
export function describeSelection(chart, selected) {
  if (!selected) return null;
  const planet = selected.planet ? chart.planets.find((p) => p.key === selected.planet) : null;

  if (planet) {
    const lines = [
      `${planet.name} stands for: ${planet.meaning.charAt(0).toLowerCase()}${planet.meaning.slice(1)}.`,
      `In your chart it is in ${planet.sign}, in house ${planet.house} (${chart.houses[planet.house - 1].label}).`,
    ];
    if (planet.key === "MOON") lines.push(`Your Moon is in the ${planet.nakshatra} nakshatra.`);
    if (planet.retrograde && planet.key !== "RAHU" && planet.key !== "KETU") {
      lines.push(`${planet.name} appears to move backward here (retrograde).`);
    }
    return { title: planet.name, lines };
  }

  const house = selected.house ? chart.houses[selected.house - 1] : null;
  if (house) {
    const here = chart.planets.filter((p) => p.house === house.number).map((p) => p.name);
    const lines = [`House ${house.number} is about: ${house.label.toLowerCase()}.`, `Its sign is ${house.sign}.`];
    lines.push(here.length ? `Planets here: ${here.join(", ")}.` : "No planets are in this house.");
    if (house.number === 1) lines.push("This is your rising sign, the starting point of your chart.");
    return { title: `House ${house.number}`, lines };
  }
  return null;
}
