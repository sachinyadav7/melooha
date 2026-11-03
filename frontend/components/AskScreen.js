"use client";

import { useRef, useState } from "react";

import { ApiError, askQuestion, newId, trackEvent } from "../lib/api";
import AnswerCard from "./AnswerCard";
import EvidenceSheet from "./EvidenceSheet";
import PaywallCard from "./PaywallCard";

const SUGGESTIONS = ["What are my strengths?", "How is my career area?", "What should I work on?"];

export default function AskScreen({ user, chart, balance, onBalance, showChart, onSeeChart }) {
  const [text, setText] = useState("");
  const [items, setItems] = useState([]);
  const [factId, setFactId] = useState(null);
  const endRef = useRef(null);

  const busy = items.some((item) => item.status === "thinking" || item.status === "streaming");
  const noQuestions = balance === 0;

  const patch = (id, changes) =>
    setItems((list) => list.map((item) => (item.id === id ? { ...item, ...changes } : item)));

  const ask = async (question) => {
    const clean = question.trim();
    if (clean.length < 3 || busy || noQuestions) return;
    const id = newId();
    setText("");
    setItems((list) => [...list, { id, question: clean, text: "", status: "thinking" }]);
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), 50);

    let answer = "";
    try {
      await askQuestion(user.user_id, clean, id, (name, data) => {
        if (name === "token") {
          answer += data.text;
          patch(id, { text: answer, status: "streaming", rewriting: false });
        } else if (name === "reset") {
          answer = "";
          patch(id, { text: "", status: "thinking", rewriting: true });
        } else if (name === "done") {
          patch(id, { text: data.answer, status: "done" });
          onBalance(data.balance);
        } else if (name === "failed") {
          patch(id, { status: "failed", message: data.message });
          onBalance(data.balance);
        }
      });
    } catch (e) {
      if (e instanceof ApiError && e.code === "insufficient_balance") {
        setItems((list) => list.filter((item) => item.id !== id));
        onBalance(0);
      } else {
        patch(id, { status: "failed", message: e.message });
      }
    }
  };

  const retry = (question) => {
    setItems((list) => list.filter((item) => !(item.status === "failed" && item.question === question)));
    ask(question);
  };

  const openChip = (id) => {
    trackEvent(user.user_id, "evidence_tapped", { fact: id });
    setFactId(id);
  };

  return (
    <div className="stack">
      <div className="stack-sm">
        <h1>Ask about your chart</h1>
        <p className="muted">Answers use only your own birth chart.</p>
        {showChart && (
          <button className="btn btn-secondary" onClick={onSeeChart}>See my chart</button>
        )}
      </div>

      {items.length === 0 && !noQuestions && (
        <div className="suggestions">
          <p className="muted">Try one of these:</p>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion" onClick={() => ask(s)}>{s}</button>
          ))}
        </div>
      )}

      {items.map((item) => (
        <AnswerCard key={item.id} item={item} showChart={showChart} chart={chart} onChip={openChip} onRetry={retry} />
      ))}

      {noQuestions && <PaywallCard userId={user.user_id} onAdded={onBalance} />}
      <div ref={endRef} />

      {!noQuestions && (
        <div className="ask-bar">
          <form className="ask-row" onSubmit={(e) => { e.preventDefault(); ask(text); }}>
            <label className="sr-only" htmlFor="question" style={{ position: "absolute", left: -9999 }}>Your question</label>
            <textarea id="question" className="input" rows={2} maxLength={500} placeholder="Type your question here"
                      value={text} onChange={(e) => setText(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(text); } }} />
            <button className="btn btn-primary send" type="submit" disabled={busy || text.trim().length < 3} aria-label="Send question">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M4 12l16-8-6 16-3-7-7-1z" />
              </svg>
            </button>
          </form>
        </div>
      )}

      {factId && <EvidenceSheet factId={factId} chart={chart} onClose={() => setFactId(null)} />}
    </div>
  );
}
