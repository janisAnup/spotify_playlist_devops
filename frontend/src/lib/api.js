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

export function isUnauthorizedResponse(response, payload) {
  if (!response) {
    return false;
  }

  if (response.status === 401) {
    return true;
  }

  const responseUrl = String(response.url || "");
  if (response.redirected && /\/login(?:[/?#]|$)/i.test(responseUrl)) {
    return true;
  }

  const contentType = String(response.headers?.get?.("content-type") || "").toLowerCase();
  if (contentType.includes("text/html")) {
    const payloadText = typeof payload === "string" ? payload.toLowerCase() : "";
    if (responseUrl.toLowerCase().includes("/login") || payloadText.includes("accounts.spotify.com/authorize")) {
      return true;
    }
  }

  if (payload && typeof payload === "object") {
    const errorText = String(payload.error || "").toLowerCase();
    if (errorText.includes("login")) {
      return true;
    }
  }

  return false;
}

export function isAuthScopeIssue(response, payload) {
  if (!response || response.status !== 403) {
    return false;
  }

  const joinedMessage = [
    typeof payload === "string" ? payload : "",
    payload && typeof payload === "object" ? String(payload.error || "") : "",
    payload && typeof payload === "object" ? String(payload.details || "") : ""
  ].join(" ").toLowerCase();

  return ["scope", "permission", "token", "login", "authorize", "auth"].some((word) => joinedMessage.includes(word));
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
