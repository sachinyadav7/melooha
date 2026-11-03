import { parseSSE } from "./sse.mjs";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const FRIENDLY = {
  network: "We could not reach the server. Check your internet and try again.",
  generic: "Something went wrong. Please try again.",
};

async function readError(response) {
  let body = {};
  try {
    body = await response.json();
  } catch {
    /* not JSON */
  }
  return new ApiError(response.status, body.code || "error", body.message || FRIENDLY.generic);
}

async function request(path, { method = "GET", body, timeoutMs = 20000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "network", FRIENDLY.network);
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) throw await readError(response);
  return response.json();
}

export const newId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

// The free hosting plan puts the server to sleep, so the first call can take about a minute.
export const wakeServer = () => request("/health", { timeoutMs: 70000 });

export const getCities = () => request("/cities").then((r) => r.cities);
export const createUser = (name) => request("/users", { method: "POST", body: { name } });
export const getUser = (id) => request(`/users/${id}`);
export const getChart = (id) => request(`/users/${id}/chart`);
export const saveChart = (id, details) => request(`/users/${id}/chart`, { method: "PUT", body: details });
export const addQuestions = (id, requestId) =>
  request(`/users/${id}/add-questions`, { method: "POST", body: { request_id: requestId } });

/** Tracking must never get in the user's way, so errors are ignored. */
export function trackEvent(id, name, properties = {}) {
  request(`/users/${id}/events`, { method: "POST", body: { name, properties } }).catch(() => {});
}

/** Streams an answer. Calls onEvent(name, data) for meta, token, reset, done and failed. */
export async function askQuestion(id, question, requestId, onEvent) {
  let response;
  try {
    response = await fetch(`${API}/users/${id}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, request_id: requestId }),
    });
  } catch {
    throw new ApiError(0, "network", FRIENDLY.network);
  }
  if (!response.ok) throw await readError(response);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSSE(buffer);
      buffer = parsed.rest;
      parsed.events.forEach((event) => onEvent(event.name, event.data));
    }
  } catch {
    throw new ApiError(0, "network", FRIENDLY.network);
  }
}
