"use client";

import { splitAnswer, stripMarkers } from "../lib/facts.mjs";

function chipLabel(id, chart) {
  const fact = chart.facts.find((f) => f.id === id);
  if (!fact) return "See chart";
  return fact.text.replace(/\s*\(.*?\)\.?$/, "").replace(/\.$/, "");
}

export default function AnswerCard({ item, showChart, chart, onChip, onRetry }) {
  const streaming = item.status === "streaming" || item.status === "thinking";

  return (
    <div className="stack-sm">
      <div className="bubble-q">{item.question}</div>

      {item.status === "failed" ? (
        <div className="banner" role="alert">
          <span>{item.message}</span>
          <button className="btn btn-secondary" onClick={() => onRetry(item.question)}>Try again</button>
        </div>
      ) : (
        <div className="answer" aria-live="polite">
          {item.status === "thinking" || !item.text ? (
            <span className="muted" role="status">
              {item.rewriting ? "Double-checking this answer against your chart" : "Reading your chart"}{" "}
              <span className="dots" aria-hidden="true"><span /><span /><span /></span>
            </span>
          ) : showChart ? (
            <p>
              {splitAnswer(item.text, { streaming }).map((part, index) =>
                part.type === "text" ? (
                  <span key={index}>{part.value}</span>
                ) : (
                  <button key={index} className="fact-chip" onClick={() => onChip(part.id)}>
                    {chipLabel(part.id, chart)}
                  </button>
                )
              )}
            </p>
          ) : (
            <p>{stripMarkers(item.text, { streaming })}</p>
          )}
          {item.status === "done" && showChart && item.text.includes("[[") && (
            <p className="hint">Tap a gold fact to see it on your chart.</p>
          )}
        </div>
      )}
    </div>
  );
}
