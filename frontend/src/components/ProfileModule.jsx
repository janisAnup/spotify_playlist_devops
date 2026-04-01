import { compactNumber } from "../utils";

function ProfileMeta({ label, value }) {
  return (
    <div className="profile-meta">
      <span>{label}</span>
      <strong>{value || "Not available"}</strong>
    </div>
  );
}

export default function ProfileModule({ profile }) {
  const avatarUrl = profile?.images?.[0]?.url;

  return (
    <section className="module-stack">
      <div className="profile-shell">
        <div className="profile-hero-card">
          <div className="profile-avatar-shell">
            {avatarUrl ? <img src={avatarUrl} alt={profile?.display_name || "Spotify profile"} className="profile-avatar" /> : <div className="profile-avatar placeholder">{profile?.display_name?.[0] || "S"}</div>}
          </div>
          <div>
            <p className="eyebrow">Profile</p>
            <h2>{profile?.display_name || "Spotify account"}</h2>
            <p className="module-copy">
              Your account snapshot with public identity, plan details, and audience information pulled directly from Spotify.
            </p>
            {profile?.external_urls?.spotify ? (
              <a className="inline-link" href={profile.external_urls.spotify} target="_blank" rel="noreferrer">
                Open Spotify profile
              </a>
            ) : null}
          </div>
        </div>

        <div className="profile-meta-grid">
          <ProfileMeta label="Email" value={profile?.email} />
          <ProfileMeta label="Country" value={profile?.country} />
          <ProfileMeta label="Product" value={profile?.product} />
          <ProfileMeta label="Followers" value={compactNumber(profile?.followers?.total || 0)} />
          <ProfileMeta label="Spotify ID" value={profile?.id} />
          <ProfileMeta label="Images" value={profile?.images?.length || 0} />
        </div>
      </div>
    </section>
  );
}
