"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    fetch(`${API}/health`)
      .then((res) => (res.ok ? setStatus("connected") : setStatus("error")))
      .catch(() => setStatus("error"));
  }, []);

  const label = {
    loading: "Checking the server...",
    connected: "Server connected",
    error: "Cannot reach the server. Check that the backend is running.",
  }[status];

  return (
    <main style={{ padding: "48px 24px", maxWidth: 480, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, marginBottom: 8 }}>Melooha: Show Your Work</h1>
      <p style={{ opacity: 0.8, marginBottom: 24 }}>
        Project skeleton. The chart and Q&A screens come next.
      </p>
      <p role="status">{label}</p>
    </main>
  );
}
