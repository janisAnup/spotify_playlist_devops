export default function WelcomeModule({ profile, onSelectTab }) {
  const displayName = profile?.display_name || "Your";
  const profileImage = profile?.images?.[0]?.url || "";

  return (
    <section className="module-stack">
      <div className="module-hero welcome-hero">
        <div className="welcome-copy">
          <p className="eyebrow">Welcome</p>
          <h2>{profile?.display_name ? `${profile.display_name}'s listening studio` : "Your listening studio"}</h2>
          <p className="module-copy">
            Step into a mood-first workspace designed for Spotify listeners. Shape playlists around energy, genre, and vibe, then move through your profile, insights, and history like chapters in your own listening story.
          </p>

          <div className="welcome-pills" aria-label="Workspace highlights">
            <span className="welcome-pill">Mood-led playlist creation</span>
            <span className="welcome-pill">Spotify profile + listening insights</span>
            <span className="welcome-pill">Saved playlist history archive</span>
          </div>

          <div className="quick-actions">
            <button type="button" className="primary-button" onClick={() => onSelectTab("create")}>
              Start creating
            </button>
            <button type="button" className="ghost-button" onClick={() => onSelectTab("insights")}>
              View insights
            </button>
            <button type="button" className="ghost-button" onClick={() => onSelectTab("history")}>
              Open history
            </button>
          </div>
        </div>

        <div className="welcome-showcase" aria-hidden="true">
          <div className="welcome-showcase__header">
            <span>{displayName}</span>
            <strong>Playlist journey</strong>
          </div>

          <div className="welcome-showcase__art">
            <div className="orbit orbit-a" />
            <div className="orbit orbit-b" />
            <div className="record-stack">
              <div className="record-stack__disc record-stack__disc--back" />
              <div className="record-stack__disc record-stack__disc--front" />
            </div>
            <div className="welcome-avatar-card">
              {profileImage ? (
                <img src={profileImage} alt="" className="welcome-avatar-image" />
              ) : (
                <div className="welcome-avatar-fallback">{displayName.slice(0, 1).toUpperCase()}</div>
              )}
              <div>
                <p>Connected profile</p>
                <strong>{displayName}</strong>
              </div>
            </div>
          </div>

          <div className="welcome-feature-grid">
            <article className="welcome-feature-card">
              <span>01</span>
              <strong>Compose by mood</strong>
              <p>Pick a feeling, fine-tune the vibe, and build a playlist with real intent.</p>
            </article>
            <article className="welcome-feature-card">
              <span>02</span>
              <strong>Read your patterns</strong>
              <p>Surface top artists, genres, and tracks to guide smarter playlist choices.</p>
            </article>
            <article className="welcome-feature-card">
              <span>03</span>
              <strong>Keep the archive</strong>
              <p>Every generated playlist stays easy to revisit from your history panel.</p>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
