"use client";

import { describeSelection, factText, targetForFact } from "../lib/facts.mjs";
import NorthIndianChart from "./NorthIndianChart";

export default function EvidenceSheet({ factId, chart, onClose }) {
  const target = targetForFact(factId, chart);
  const info = describeSelection(chart, target);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet stack" role="dialog" aria-modal="true" aria-label="Why this answer" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" aria-hidden="true" />
        <h2>Why this answer?</h2>
        <p>{factText(factId, chart) || "This comes from your birth chart."}</p>
        <div className="card chart-wrap">
          <NorthIndianChart chart={chart} selected={target} />
        </div>
        {info && (
          <div className="stack-sm">
            {info.lines.map((line) => <p key={line} className="muted">{line}</p>)}
          </div>
        )}
        <button className="btn btn-primary" onClick={onClose}>Got it</button>
      </div>
    </div>
  );
}
