"use client";

import { useMemo } from "react";

import { layoutChart } from "../lib/chartGeometry.mjs";

export default function NorthIndianChart({ chart, selected, onSelectHouse }) {
  const layout = useMemo(() => layoutChart(chart), [chart]);

  return (
    <svg className="chart-svg" viewBox="0 0 300 300" role="group" aria-label="Your birth chart, North Indian style">
      {layout.map((house) => (
        <polygon
          key={house.number}
          points={house.points}
          className={`chart-house${selected?.house === house.number ? " is-selected" : ""}`}
          role="button"
          tabIndex={0}
          aria-label={`House ${house.number}: ${house.label}`}
          onClick={() => onSelectHouse?.(house.number)}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelectHouse?.(house.number)}
        />
      ))}
      {layout.map((house) => (
        <text key={`s${house.number}`} className="chart-sign" x={house.signX} y={house.signY}>
          {house.signNumber}
        </text>
      ))}
      {layout.flatMap((house) =>
        house.planets.map((planet) => (
          <text
            key={planet.key}
            x={planet.x}
            y={planet.y}
            className={`chart-planet${selected?.planet === planet.key ? " is-selected" : ""}`}
          >
            {planet.abbr}
          </text>
        ))
      )}
    </svg>
  );
}
