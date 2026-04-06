import { useEffect, useMemo, useRef, useState } from "react";

import { createDefaultInsights, defaultForm, moodOptions, tabItems, vibeOptions } from "./constants";
import { API_BASE, apiRequest, getMessage, isAuthScopeIssue, isUnauthorizedResponse } from "./lib/api";
import CreateModule from "./components/CreateModule";
import HistoryModule from "./components/HistoryModule";
import InsightsModule from "./components/InsightsModule";
import ProfileModule from "./components/ProfileModule";
import TabNav from "./components/TabNav";
import WelcomeModule from "./components/WelcomeModule";

function StatPill({ label, value }) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function GuestLanding({ surfaceMessage, onLogin }) {
  return (
    <main className="guest-layout">
      <section className="glass-panel hero-card">
        <div className="hero-copy">
          <div className="spotify-badge">
            <svg viewBox="0 0 64 64" aria-hidden="true" className="spotify-badge__icon">
              <circle cx="32" cy="32" r="32" fill="#1ed760" />
              <path d="M18 24c9-3 20-2 29 3" stroke="#0b1118" strokeWidth="4.5" strokeLinecap="round" fill="none" />
              <path d="M21 34c7-2 15-1 22 3" stroke="#0b1118" strokeWidth="4" strokeLinecap="round" fill="none" />
              <path d="M24 43c5-1 10 0 14 2" stroke="#0b1118" strokeWidth="3.5" strokeLinecap="round" fill="none" />
            </svg>
            <span>Built for Spotify listeners</span>
          </div>
          <p className="eyebrow">Discover</p>
          <h2>Generate playlists around your mood, not just random songs</h2>
          <p>
            Spotify Playlist Generator helps you create playlists based on mood, genre, vibe, and listening style. Connect your Spotify account to generate playlists directly inside your own library.
          </p>

          <div className="hero-actions">
            <button type="button" className="primary-button large" onClick={onLogin}>
              Login with Spotify
            </button>
            <a href="#features" className="secondary-link">
              Explore features
            </a>
          </div>

          {surfaceMessage ? <p className="surface-message guest" role="alert">{surfaceMessage}</p> : null}
        </div>

        <div className="showcase-panel illustration-shell">
          <div className="showcase-panel__header">
            <span>Preview</span>
            <strong>Smart playlist flow</strong>
          </div>

          <div className="illustration-stack">
            <div className="illustration-card illustration-card--primary">
              <span className="illustration-label">Mood</span>
              <strong>Chill</strong>
            </div>
            <div className="illustration-card">
              <span className="illustration-label">Genre</span>
              <strong>Indie</strong>
            </div>
            <div className="illustration-card">
              <span className="illustration-label">Vibe</span>
              <strong>Dreamy</strong>
            </div>
          </div>

          <div className="playlist-mock">
            <div className="playlist-mock__disc" />
            <div className="playlist-mock__panel">
              <p>Generated playlist</p>
              <strong>Chill Indie Set</strong>
              <span>10 tracks saved to Spotify</span>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="feature-ribbon">
        <div className="feature-card">
          <p className="eyebrow">Mood Based</p>
          <h3>Create playlists with intent</h3>
          <p>
            Build playlists from mood, genre, and vibe instead of manually hunting for songs one by one.
          </p>
        </div>
        <div className="feature-card">
          <p className="eyebrow">Spotify Ready</p>
          <h3>Save directly to your library</h3>
          <p>
            Login with Spotify so the app can create playlists in your account and keep the experience seamless.
          </p>
        </div>
        <div className="feature-card">
          <p className="eyebrow">Personalized</p>
          <h3>See profile and listening insights</h3>
          <p>
            Explore your profile, recent playlist history, top artists, and top songs in one connected interface.
          </p>
        </div>
      </section>
    </main>
  );
}

function WorkspaceApp() {
  const [activeTab, setActiveTab] = useState("create");
  const [authState, setAuthState] = useState("loading");
  const [profile, setProfile] = useState(null);
  const [history, setHistory] = useState([]);
  const [insights, setInsights] = useState(createDefaultInsights);
  const [insightsError, setInsightsError] = useState("");
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const [result, setResult] = useState(null);
  const [surfaceMessage, setSurfaceMessage] = useState("");
  const previewRequestRef = useRef(0);

  const summary = useMemo(() => {
    const moodLabel = moodOptions.find((option) => option.value === form.mood)?.label || form.mood;
    const vibeLabel = vibeOptions.find((option) => option.value === form.vibe)?.label || form.vibe;
    const visibility = form.visibility === "true" ? "Public" : "Private";
    const fallbackTitle = `${moodLabel} ${form.genre} set`;
    const fallbackDescription = `${form.count} tracks with a ${vibeLabel.toLowerCase()} tone, saved as ${visibility.toLowerCase()}.`;
    const seedArtistCount = Array.isArray(form.seed_artist_ids) ? form.seed_artist_ids.length : 0;
    const seedTrackCount = Array.isArray(form.seed_track_ids) ? form.seed_track_ids.length : 0;

    return {
      title: preview?.playlist_name || fallbackTitle,
      description: preview?.playlist_description || fallbackDescription,
      chips: [
        moodLabel,
        form.genre,
        vibeLabel,
        `${form.count} songs`,
        visibility,
        seedArtistCount ? `${seedArtistCount} artist seeds` : "",
        seedTrackCount ? `${seedTrackCount} track seeds` : ""
      ].filter(Boolean)
    };
  }, [form, preview]);

  const activeTabMeta = tabItems.find((item) => item.id === activeTab) || tabItems[0];

  function resetWorkspaceState() {
    setProfile(null);
    setHistory([]);
    setInsights(createDefaultInsights());
    setInsightsError("");
    setPreview(null);
    setPreviewError("");
    setResult(null);
  }

  function handleUnauthorized(message = "Your Spotify session expired. Please connect again.") {
    setAuthState("guest");
    resetWorkspaceState();
    setSurfaceMessage(message);
    setActiveTab("welcome");
  }

  async function ensureActiveSession(actionLabel) {
    try {
      const { response, payload } = await apiRequest("/check_session");
      if (!response.ok || !payload || payload.authenticated !== true) {
        handleUnauthorized(`Spotify login required to ${actionLabel}. Please connect again.`);
        return false;
      }
      return true;
    } catch {
      setSurfaceMessage("Could not verify Spotify session. Please try again.");
      return false;
    }
  }

  useEffect(() => {
    let ignore = false;

    async function bootstrap() {
      setIsBootstrapping(true);

      try {
        const { response, payload } = await apiRequest("/check_session");

        if (!response.ok) {
          throw new Error("Unable to verify your Spotify session.");
        }

        if (!payload || payload.authenticated !== true) {
          if (!ignore) {
            setAuthState("guest");
            resetWorkspaceState();
          }
          return;
        }

        if (!ignore) {
          setAuthState("authenticated");
          setActiveTab("create");
        }

        await Promise.all([loadProfile(ignore), loadHistory(ignore), loadInsights(ignore)]);
      } catch (error) {
        if (!ignore) {
          setAuthState("guest");
          setSurfaceMessage(error.message || "Backend is unavailable right now.");
        }
      } finally {
        if (!ignore) {
          setIsBootstrapping(false);
        }
      }
    }

    bootstrap();

    return () => {
      ignore = true;
    };
  }, []);

  async function loadProfile(ignore = false) {
    const { response, payload } = await apiRequest("/whoami");

    if (isUnauthorizedResponse(response, payload)) {
      if (!ignore) {
        handleUnauthorized();
      }
      return;
    }

    if (!response.ok) {
      throw new Error(getMessage(payload, "Could not load your Spotify profile."));
    }

    if (!ignore) {
      setProfile(payload);
    }
  }

  async function loadHistory(ignore = false) {
    const { response, payload } = await apiRequest("/playlist_history");

    if (isUnauthorizedResponse(response, payload)) {
      if (!ignore) {
        handleUnauthorized();
      }
      return;
    }

    if (!response.ok) {
      if (!ignore) {
        setHistory([]);
      }
      return;
    }

    if (!ignore) {
      setHistory(Array.isArray(payload?.playlists) ? payload.playlists : []);
    }
  }

  async function loadInsights(ignore = false) {
    const { response, payload } = await apiRequest("/insights");

    if (isUnauthorizedResponse(response, payload)) {
      if (!ignore) {
        handleUnauthorized();
      }
      return;
    }

    if (!response.ok) {
      if (!ignore) {
        setInsightsError(
          `${getMessage(payload, "Could not load listening insights.")} Try logging out and connecting Spotify again so the new permissions are granted.`
        );
      }
      return;
    }

    if (!ignore) {
      setInsights(payload);
      setInsightsError("");
    }
  }

  function updateForm(key, value) {
    setPreview(null);
    setPreviewError("");
    setResult(null);
    setForm((current) => ({
      ...current,
      [key]: value
    }));
  }

  async function requestPreview({ excludeTrackIds = [], variation = 0 } = {}) {
    const requestId = previewRequestRef.current + 1;
    previewRequestRef.current = requestId;
    setIsPreviewing(true);
    setPreviewError("");

    try {
      const { response, payload } = await apiRequest("/preview_playlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ...form,
          exclude_track_ids: excludeTrackIds,
          variation
        })
      });

      if (previewRequestRef.current !== requestId) {
        return;
      }

      if (isUnauthorizedResponse(response, payload)) {
        handleUnauthorized();
        setPreview(null);
        return;
      }

      if (!response.ok) {
        throw new Error(getMessage(payload, "Could not build a draft playlist."));
      }

      setPreview({
        playlist_name: payload.playlist_name || summary.title,
        playlist_description: payload.playlist_description || summary.description,
        tracks: Array.isArray(payload.tracks) ? payload.tracks : [],
        tracks_found: payload.tracks_found || 0,
        warning: payload.warning || "",
        variation: payload.variation || variation
      });
    } catch (error) {
      if (previewRequestRef.current !== requestId) {
        return;
      }

      setPreview(null);
      setPreviewError(error.message || "Could not build a draft playlist.");
    } finally {
      if (previewRequestRef.current === requestId) {
        setIsPreviewing(false);
      }
    }
  }

  useEffect(() => {
    if (authState !== "authenticated" || activeTab !== "create") {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      requestPreview();
    }, 320);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    authState,
    activeTab,
    form.mood,
    form.genre,
    form.vibe,
    form.count,
    form.visibility,
    form.seed_artist_ids,
    form.seed_track_ids,
    form.audio_tuning_enabled,
    form.audio_tuning
  ]);

  function handleLogin() {
    window.location.href = `${API_BASE}/login`;
  }

  async function handleLogout() {
    try {
      await apiRequest("/logout");
    } finally {
      setAuthState("guest");
      resetWorkspaceState();
      setSurfaceMessage("");
      setActiveTab("welcome");
    }
  }

  async function handleGenerate(event) {
    event.preventDefault();
    const hasSession = await ensureActiveSession("create playlist");
    if (!hasSession) {
      return;
    }

    setIsCreating(true);
    setSurfaceMessage("");
    setResult({
      type: "loading",
      title: "Mixing your playlist",
      message: "Matching tracks, checking genre fit, and preparing a Spotify-ready playlist."
    });

    try {
      const { response, payload } = await apiRequest("/generate_playlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ...form,
          variation: preview?.variation || 0,
          playlist_name: preview?.playlist_name || "",
          playlist_description: preview?.playlist_description || "",
          track_ids: Array.isArray(preview?.tracks) ? preview.tracks.map((track) => track.id).filter(Boolean) : []
        })
      });

      if (isUnauthorizedResponse(response, payload)) {
        handleUnauthorized("Spotify login expired while creating the playlist. Please reconnect and try again.");
        setResult(null);
        return;
      }

      if (isAuthScopeIssue(response, payload)) {
        throw new Error("Spotify permissions are missing for playlist creation. Reconnect Spotify and approve access.");
      }

      if (!response.ok) {
        throw new Error(getMessage(payload, "Playlist creation failed."));
      }

      setResult({
        type: "success",
        title: payload.playlist_name || "Playlist created",
        message: `${payload.tracks_added || 0} tracks were added to your Spotify library.`,
        warning: payload.warning || "",
        playlistUrl: payload.playlist_url || ""
      });

      await loadHistory();
      setActiveTab("history");
    } catch (error) {
      setSurfaceMessage(error.message || "Could not create playlist right now.");
      setResult({
        type: "error",
        title: "Could not create playlist",
        message: error.message || "Please try again in a moment."
      });
    } finally {
      setIsCreating(false);
    }
  }

  function handleRegenerate() {
    const excludedTrackIds = Array.isArray(preview?.tracks) ? preview.tracks.map((track) => track.id).filter(Boolean) : [];
    const nextVariation = (preview?.variation || 0) + 1;
    setResult(null);
    requestPreview({
      excludeTrackIds: excludedTrackIds,
      variation: nextVariation
    });
  }

  function toggleSeedSelection(fieldName, itemId, limit = 5) {
    setResult(null);
    setPreviewError("");
    setForm((current) => {
      const currentValues = Array.isArray(current[fieldName]) ? current[fieldName] : [];
      if (currentValues.includes(itemId)) {
        return {
          ...current,
          [fieldName]: currentValues.filter((value) => value !== itemId)
        };
      }

      if (currentValues.length >= limit) {
        setSurfaceMessage("You can select up to 5 seeds in each group.");
        return current;
      }

      return {
        ...current,
        [fieldName]: [...currentValues, itemId]
      };
    });
  }

  function updateAudioTuning(featureName, value) {
    const normalizedValue = Math.max(0, Math.min(100, Number(value) || 0));
    setResult(null);
    setPreviewError("");
    setSurfaceMessage("");
    setForm((current) => ({
      ...current,
      audio_tuning_enabled: true,
      audio_tuning: {
        ...(current.audio_tuning || {}),
        [featureName]: normalizedValue
      }
    }));
  }

  function handleRemoveTrack(indexToRemove) {
    setResult(null);
    setPreviewError("");
    setPreview((current) => {
      if (!current || !Array.isArray(current.tracks) || !current.tracks[indexToRemove]) {
        return current;
      }

      const nextTracks = current.tracks.filter((_, index) => index !== indexToRemove);
      return {
        ...current,
        tracks: nextTracks,
        tracks_found: nextTracks.length
      };
    });
  }

  function moveTrack(fromIndex, toIndex) {
    setResult(null);
    setPreviewError("");
    setPreview((current) => {
      if (!current || !Array.isArray(current.tracks)) {
        return current;
      }

      const tracks = [...current.tracks];
      if (!tracks[fromIndex] || toIndex < 0 || toIndex >= tracks.length) {
        return current;
      }

      const [moved] = tracks.splice(fromIndex, 1);
      tracks.splice(toIndex, 0, moved);
      return {
        ...current,
        tracks
      };
    });
  }

  function handleMoveTrackUp(index) {
    moveTrack(index, index - 1);
  }

  function handleMoveTrackDown(index) {
    moveTrack(index, index + 1);
  }

  function renderActiveModule() {
    switch (activeTab) {
      case "profile":
        return <ProfileModule profile={profile} />;
      case "create":
        return (
          <CreateModule
            form={form}
            updateForm={updateForm}
            handleGenerate={handleGenerate}
            isCreating={isCreating}
            isPreviewing={isPreviewing}
            preview={preview}
            previewError={previewError}
            handlePreview={() => requestPreview({ variation: preview?.variation || 0 })}
            handleRegenerate={handleRegenerate}
            handleRemoveTrack={handleRemoveTrack}
            handleMoveTrackUp={handleMoveTrackUp}
            handleMoveTrackDown={handleMoveTrackDown}
            insights={insights}
            toggleSeedTrack={(trackId) => toggleSeedSelection("seed_track_ids", trackId)}
            toggleSeedArtist={(artistId) => toggleSeedSelection("seed_artist_ids", artistId)}
            updateAudioTuning={updateAudioTuning}
            result={result}
            summary={summary}
            surfaceMessage={surfaceMessage}
          />
        );
      case "insights":
        return <InsightsModule insights={insights} insightsError={insightsError} />;
      case "history":
        return <HistoryModule history={history} />;
      case "welcome":
      default:
        return (
          <WelcomeModule
            profile={profile}
            onSelectTab={setActiveTab}
          />
        );
    }
  }

  return (
    <div className={authState === "authenticated" ? "app-shell is-authenticated" : "app-shell"}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="ambient ambient-three" />

      <header className="topbar">
        <div>
          <p className="brand-mark">Spotify Playlist Generator</p>
          <h1>{authState === "authenticated" ? activeTabMeta.label : "Music, organized around your mood"}</h1>
        </div>

        <div className="topbar-actions">
          {authState === "authenticated" ? (
            <StatPill label="Focus" value={activeTabMeta.eyebrow} />
          ) : null}
          {authState === "authenticated" ? (
            <button type="button" className="ghost-button" onClick={handleLogout}>
              Logout
            </button>
          ) : (
            <button type="button" className="primary-button" onClick={handleLogin}>
              Connect Spotify
            </button>
          )}
        </div>
      </header>

      {isBootstrapping ? (
        <main className="loading-state">
          <div className="glass-panel" role="status" aria-live="polite">
            <p className="eyebrow">Loading studio</p>
            <h2>Checking your Spotify session</h2>
            <p>Once the session is ready, we'll bring your profile, history, and listening insights into the workspace.</p>
          </div>
        </main>
      ) : authState === "authenticated" ? (
        <main className="workspace-layout">
          <TabNav items={tabItems} activeTab={activeTab} onSelect={setActiveTab} />
          <div className="module-stage">{renderActiveModule()}</div>
        </main>
      ) : (
        <GuestLanding surfaceMessage={surfaceMessage} onLogin={handleLogin} />
      )}
    </div>
  );
}

export default WorkspaceApp;
