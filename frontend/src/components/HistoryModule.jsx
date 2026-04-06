import { formatDate } from "../utils";

export default function HistoryModule({ history }) {
  const items = Array.isArray(history) ? history : [];

  return (
    <section className="module-stack">
      <div className="module-hero">
        <div>
          <p className="eyebrow">History</p>
          <h2>Your generated playlists</h2>
          <p className="module-copy">
            A running archive of playlists created by this app, including the mood, genre, and vibe you used.
          </p>
        </div>
      </div>

      <section className="glass-panel history-panel full-width">
        {items.length === 0 ? (
          <div className="history-empty">
            <p>Your generated playlists will show up here after the first successful create.</p>
          </div>
        ) : (
          <div className="history-list">
            {items.map((item) => (
              <article key={`${item.playlist_name}-${item.created_at}`} className="history-item">
                <div>
                  <p className="history-title">{item.playlist_name}</p>
                  <p className="history-meta">
                    {item.mood} / {item.genre} / {item.vibe || "none"}
                  </p>
                </div>
                <div className="history-side">
                  <span>{formatDate(item.created_at)}</span>
                  <span>{item.count} tracks</span>
                  {item.playlist_url ? (
                    <a href={item.playlist_url} target="_blank" rel="noreferrer">
                      Open
                    </a>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
