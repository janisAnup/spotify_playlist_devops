const { API_BASE } = window.APP_CONFIG || {
  API_BASE: "http://127.0.0.1:5000"
};

const profileBtn = document.getElementById("profileBtn");
const logoutBtn = document.getElementById("logoutBtn");
const playlistForm = document.getElementById("playlistForm");
const resultBox = document.getElementById("result");
const profileBox = document.getElementById("profileBox");
const createBtn = document.getElementById("createBtn");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getMessageParts(payload, fallbackMessage) {
  const parts = [];

  if (!payload) {
    return [fallbackMessage];
  }

  if (typeof payload === "string") {
    return [payload];
  }

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

  if (parts.length === 0) {
    parts.push(fallbackMessage);
  }

  return [...new Set(parts)];
}

function buildMessageHtml(parts) {
  return parts
    .map((part) => `<p>${escapeHtml(part)}</p>`)
    .join("");
}

async function parseResponsePayload(response) {
  const rawText = await response.text();

  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch (error) {
    return rawText;
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options
  });

  const payload = await parseResponsePayload(response);
  return { response, payload };
}

function redirectToLanding() {
  window.location.href = "index.html";
}

function setStatus(container, type, html) {
  const baseClass = container.id === "profileBox" ? "profile-box" : "result-box";
  container.className = `${baseClass} status-${type}`;
  container.innerHTML = html;
}

function setCreateButtonState(isLoading) {
  createBtn.disabled = isLoading;
  createBtn.textContent = isLoading ? "Creating..." : "Create Playlist";
}

async function ensureAuthenticated() {
  try {
    const { response, payload } = await apiRequest("/check_session");

    if (!response.ok) {
      setStatus(profileBox, "error", "<p>Unable to verify your session.</p>");
      return false;
    }

    if (!payload || payload.authenticated !== true) {
      redirectToLanding();
      return false;
    }

    return true;
  } catch (error) {
    setStatus(profileBox, "error", "<p>Backend is unavailable right now.</p>");
    return false;
  }
}

profileBtn.addEventListener("click", async () => {
  setStatus(profileBox, "info", "<p>Loading your Spotify profile...</p>");

  try {
    const { response, payload } = await apiRequest("/whoami");

    if (response.status === 401) {
      redirectToLanding();
      return;
    }

    if (!response.ok) {
      setStatus(
        profileBox,
        "error",
        buildMessageHtml(getMessageParts(payload, "Could not fetch profile."))
      );
      return;
    }

    setStatus(
      profileBox,
      "success",
      `
        <p><strong>Name:</strong> ${escapeHtml(payload.display_name || "Not available")}</p>
        <p><strong>Email:</strong> ${escapeHtml(payload.email || "Not available")}</p>
        <p><strong>Spotify ID:</strong> ${escapeHtml(payload.id || "Not available")}</p>
        <p><strong>Product:</strong> ${escapeHtml(payload.product || "Not available")}</p>
      `
    );
  } catch (error) {
    setStatus(profileBox, "error", "<p>Error connecting to the backend.</p>");
  }
});

logoutBtn.addEventListener("click", async () => {
  try {
    await apiRequest("/logout");
  } finally {
    redirectToLanding();
  }
});

playlistForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const mood = document.getElementById("mood").value;
  const genre = document.getElementById("genre").value;
  const count = document.getElementById("count").value;
  const visibility = document.getElementById("visibility").value;
  const vibe = document.querySelector('input[name="vibe"]:checked').value;

  if (!mood || !genre) {
    setStatus(resultBox, "error", "<p>Please select both mood and genre.</p>");
    return;
  }

  setCreateButtonState(true);
  setStatus(resultBox, "info", "<p>Creating playlist...</p>");

  try {
    const { response, payload } = await apiRequest("/generate_playlist", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        mood,
        genre,
        count,
        visibility,
        vibe
      })
    });

    if (response.status === 401) {
      redirectToLanding();
      return;
    }

    if (!response.ok) {
      setStatus(
        resultBox,
        "error",
        buildMessageHtml(getMessageParts(payload, "Playlist creation failed."))
      );
      return;
    }

    const warningHtml = payload.warning
      ? `<p class="status-warning-text">${escapeHtml(payload.warning)}</p>`
      : "";

    setStatus(
      resultBox,
      "success",
      `
        <p>Playlist created successfully.</p>
        <p><strong>Name:</strong> ${escapeHtml(payload.playlist_name || "Untitled Playlist")}</p>
        <p><strong>Tracks added:</strong> ${escapeHtml(payload.tracks_added || 0)}</p>
        ${warningHtml}
        <p><a href="${escapeHtml(payload.playlist_url || "#")}" target="_blank" rel="noreferrer">Open Playlist in Spotify</a></p>
      `
    );
  } catch (error) {
    setStatus(resultBox, "error", "<p>Could not reach the backend.</p>");
  } finally {
    setCreateButtonState(false);
  }
});

ensureAuthenticated();
