export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");

async function parsePayload(response) {
  const rawText = await response.text();
  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch {
    return rawText;
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options
  });

  const payload = await parsePayload(response);
  return { response, payload };
}

export function getMessage(payload, fallbackMessage) {
  if (!payload) {
    return fallbackMessage;
  }

  if (typeof payload === "string") {
    return payload;
  }

  const parts = [];

  if (typeof payload.error === "string" && payload.error) {
    parts.push(payload.error);
  }

  if (payload.error && typeof payload.error.message === "string" && payload.error.message) {
    parts.push(payload.error.message);
  }

  if (typeof payload.details === "string" && payload.details) {
    parts.push(payload.details);
  }

  if (typeof payload.warning === "string" && payload.warning) {
    parts.push(payload.warning);
  }

  return parts.join(" ") || fallbackMessage;
}
