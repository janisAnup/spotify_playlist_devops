export default function WelcomeModule({ profile, onSelectTab }) {
  return (
    <section className="module-stack">
      <div className="module-hero">
        <div>
          <p className="eyebrow">Welcome</p>
          <h2>{profile?.display_name ? `${profile.display_name}'s listening studio` : "Your listening studio"}</h2>
          <p className="module-copy">
            Use the left navigation to move through your account, playlist creation, insights, and playlist history in separate modules.
          </p>
        </div>
        <div className="quick-actions">
          <button type="button" className="primary-button" onClick={() => onSelectTab("profile")}>
            Open profile
          </button>
          <button type="button" className="ghost-button" onClick={() => onSelectTab("insights")}>
            Open insights
          </button>
          <button type="button" className="ghost-button" onClick={() => onSelectTab("create")}>
            Create playlist
          </button>
        </div>
      </div>
    </section>
  );
}
