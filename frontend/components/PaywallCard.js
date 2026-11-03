"use client";

import { useEffect, useRef, useState } from "react";

import { addQuestions, newId, trackEvent } from "../lib/api";

export default function PaywallCard({ userId, onAdded }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const tracked = useRef(false);

  useEffect(() => {
    if (!tracked.current) {
      tracked.current = true;
      trackEvent(userId, "paywall_viewed");
    }
  }, [userId]);

  const add = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await addQuestions(userId, newId());
      onAdded(result.balance);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="card card-raised stack">
      <div className="stack-sm">
        <h2>You have no questions left</h2>
        <p className="muted">Add more questions to keep asking about your chart. This is a demo, so no payment is taken.</p>
      </div>
      {error && <div className="banner" role="alert"><span>{error}</span></div>}
      <button className="btn btn-primary" onClick={add} disabled={busy}>
        {busy ? "Adding..." : "Add 5 questions"}
      </button>
    </div>
  );
}
