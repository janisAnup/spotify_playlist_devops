function ArtistCard({ artist }) {
  return (
    <article className="media-card">
      {artist.image_url ? <img src={artist.image_url} alt={artist.name} className="media-card__image" /> : <div className="media-card__image placeholder" />}
      <div className="media-card__body">
        <h3>{artist.name}</h3>
      </div>
    </article>
  );
}

function TrackRow({ track, index }) {
  const artists = Array.isArray(track?.artists) ? track.artists.join(", ") : "Spotify artist";

  return (
    <article className="track-row">
      <span className="track-row__index">#{index + 1}</span>
      {track.image_url ? <img src={track.image_url} alt={track.name} className="track-row__image" /> : <div className="track-row__image placeholder" />}
      <div className="track-row__body">
        <h3>{track.name}</h3>
        <p>{artists}</p>
      </div>
      {track.spotify_url ? (
        <a className="inline-link" href={track.spotify_url} target="_blank" rel="noreferrer">
          Open
        </a>
      ) : null}
    </article>
  );
}

export default function InsightsModule({ insights, insightsError }) {
  const genres = Array.isArray(insights?.top_genres) ? insights.top_genres : [];
  const artists = Array.isArray(insights?.top_artists) ? insights.top_artists : [];
  const tracks = Array.isArray(insights?.top_tracks) ? insights.top_tracks : [];

  if (insightsError) {
    return (
      <section className="module-stack">
        <div className="glass-panel empty-state-panel">
          <p className="eyebrow">Insights unavailable</p>
          <h2>Reconnect Spotify to load wrapped-style data</h2>
          <p>{insightsError}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="module-stack">
      <div className="module-hero">
        <div>
          <p className="eyebrow">Insights</p>
          <h2>Your listening wrapped</h2>
          <p className="module-copy">
            Top artists, top tracks, and your strongest genres derived from Spotify account activity.
          </p>
        </div>
      </div>

      <div className="genre-cloud">
        {genres.map((genre) => (
          <span key={genre.name} className="genre-pill">
            {genre.name} <strong>{genre.count}</strong>
          </span>
        ))}
      </div>

      <div className="insights-grid">
        <section className="glass-panel insights-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Top artists</p>
              <h2>Most played creators</h2>
            </div>
          </div>
          <div className="media-grid">
            {artists.map((artist) => (
              <ArtistCard key={artist.id || artist.name} artist={artist} />
            ))}
          </div>
        </section>

        <section className="glass-panel insights-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Top tracks</p>
              <h2>Heavy rotation songs</h2>
            </div>
          </div>
          <div className="track-list">
            {tracks.map((track, index) => (
              <TrackRow key={track.id || `${track.name}-${index}`} track={track} index={index} />
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
