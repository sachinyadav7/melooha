"use client";

import { useEffect, useRef, useState } from "react";

import { trackEvent } from "../lib/api";
import { describeSelection } from "../lib/facts.mjs";
import NorthIndianChart from "./NorthIndianChart";

export default function ChartScreen({ user, chart, onAsk, onEditDetails }) {
  const [selected, setSelected] = useState(null);
  const tracked = useRef(false);

  useEffect(() => {
    if (!tracked.current) {
      tracked.current = true;
      trackEvent(user.user_id, "chart_viewed");
    }
  }, [user.user_id]);

  const info = describeSelection(chart, selected);

  return (
    <div className="stack">
      <div className="stack-sm">
        <h1>Your birth chart</h1>
        <p className="muted">
          Rising sign: <strong>{chart.ascendant.sign}</strong>. Tap any planet or house to see what it means.
        </p>
      </div>

      <div className="card chart-wrap">
        <NorthIndianChart chart={chart} selected={selected} onSelectHouse={(house) => setSelected({ house })} />
        <p className="chart-caption">House 1 is at the top. Houses count anticlockwise. Small numbers are signs.</p>
      </div>

      {info ? (
        <div className="card card-raised stack-sm" aria-live="polite">
          <h2>{info.title}</h2>
          {info.lines.map((line) => <p key={line}>{line}</p>)}
        </div>
      ) : (
        <p className="muted center">Tap the chart or a planet below.</p>
      )}

      <div className="planet-list">
        {chart.planets.map((planet) => (
          <button key={planet.key} className={`planet-row${selected?.planet === planet.key ? " is-selected" : ""}`}
                  onClick={() => setSelected({ planet: planet.key, house: planet.house })}>
            <span>
              <strong>{planet.name}</strong>
              <small>{planet.meaning}</small>
            </span>
            <span className="muted">House {planet.house}</span>
          </button>
        ))}
      </div>

      <button className="btn btn-primary" onClick={onAsk}>Ask a question about my chart</button>
      <button className="btn btn-text" onClick={onEditDetails}>Change my birth details</button>
    </div>
  );
}
