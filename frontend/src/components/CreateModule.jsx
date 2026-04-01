import {
  countOptions,
  genreOptions,
  moodOptions,
  vibeOptions,
  visibilityOptions
} from "../constants";

function OptionCard({ active, title, caption, onClick }) {
  return (
    <button
      type="button"
      className={`option-card${active ? " is-active" : ""}`}
      onClick={onClick}
    >
      <span className="option-card__title">{title}</span>
      <span className="option-card__caption">{caption}</span>
    </button>
  );
}

function SeedChip({ active, label, onClick }) {
  return (
    <button
      type="button"
      className={`chip-button${active ? " is-active" : ""}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ResultPanel({ result }) {
  if (!result) {
    return (
      <div className="result-panel is-empty">
        <p className="eyebrow">Ready to generate</p>
        <h3>Your playlist will show up here</h3>
        <p>Pick a mood, shape the vibe, and create a playlist that opens directly in Spotify.</p>
      </div>
    );
  }

  return (
    <div className={`result-panel ${result.type}`}>
      <p className="eyebrow">{result.type === "success" ? "Playlist created" : "Something needs attention"}</p>
      <h3>{result.title}</h3>
      <p>{result.message}</p>
      {result.warning ? <p className="warning-copy">{result.warning}</p> : null}
      {result.playlistUrl ? (
        <a className="inline-link" href={result.playlistUrl} target="_blank" rel="noreferrer">
          Open in Spotify
        </a>
      ) : null}
    </div>
  );
}

function PreviewTracksPanel({
  summary,
  preview,
  isPreviewing,
  previewError,
  handlePreview,
  handleRegenerate,
  handleRemoveTrack,
  handleMoveTrackUp,
  handleMoveTrackDown
}) {
  return (
    <section className="glass-panel preview-panel">
      <div className="preview-header">
        <div>
          <p className="eyebrow">Draft preview</p>
          <h2>{summary.title}</h2>
        </div>
        <div className="preview-actions">
          <button type="button" className="ghost-button" onClick={handlePreview} disabled={isPreviewing}>
            Refresh preview
          </button>
          <button
            type="button"
            className="ghost-button"
            onClick={handleRegenerate}
            disabled={isPreviewing || !preview?.tracks?.length}
          >
            Regenerate mix
          </button>
        </div>
      </div>

      <p>{summary.description}</p>
      <div className="preview-chips">
        {summary.chips.map((chip) => (
          <span key={chip} className="preview-chip">
            {chip}
          </span>
        ))}
      </div>

      {isPreviewing ? (
        <div className="preview-state">
          <h3>Finding a better mix</h3>
          <p>Matching mood, genre, vibe, and audio features so the final playlist feels more intentional.</p>
        </div>
      ) : null}

      {!isPreviewing && previewError ? (
        <div className="preview-state is-error">
          <h3>Preview unavailable</h3>
          <p>{previewError}</p>
        </div>
      ) : null}

      {!isPreviewing && !previewError && preview?.warning ? (
        <p className="warning-copy preview-warning">{preview.warning}</p>
      ) : null}

      {!isPreviewing && !previewError && Array.isArray(preview?.tracks) && preview.tracks.length ? (
        <div className="draft-track-list">
          {preview.tracks.map((track, index) => (
            <article key={track.id || `${track.name}-${index}`} className="draft-track">
              {track.image_url ? (
                <img
                  src={track.image_url}
                  alt={track.name || "Track cover"}
                  className="draft-track__image"
                />
              ) : (
                <div className="draft-track__image draft-track__image--placeholder" aria-hidden="true" />
              )}
              <div className="draft-track__body">
                <span className="draft-track__index">{String(index + 1).padStart(2, "0")}</span>
                <h3>{track.name}</h3>
                <p>{Array.isArray(track.artists) ? track.artists.join(", ") : "Spotify artist"}</p>
                <div className="draft-track__actions">
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => handleMoveTrackUp(index)}
                    disabled={index === 0}
                  >
                    Move up
                  </button>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => handleMoveTrackDown(index)}
                    disabled={index === preview.tracks.length - 1}
                  >
                    Move down
                  </button>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => handleRemoveTrack(index)}
                    disabled={preview.tracks.length <= 1}
                  >
                    Remove
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {!isPreviewing && !previewError && (!preview || !preview.tracks?.length) ? (
        <div className="preview-state">
          <h3>Draft tracks will appear here</h3>
          <p>Tune the controls and we'll prepare a distinct set before anything is saved to Spotify.</p>
        </div>
      ) : null}
    </section>
  );
}

export default function CreateModule({
  form,
  updateForm,
  handleGenerate,
  isCreating,
  isPreviewing,
  preview,
  previewError,
  handlePreview,
  handleRegenerate,
  handleRemoveTrack,
  handleMoveTrackUp,
  handleMoveTrackDown,
  insights,
  toggleSeedTrack,
  toggleSeedArtist,
  updateAudioTuning,
  presets,
  presetName,
  setPresetName,
  handleSavePreset,
  applyPreset,
  deletePreset,
  presetMessage,
  result,
  summary,
  surfaceMessage
}) {
  const topTracks = Array.isArray(insights?.top_tracks) ? insights.top_tracks : [];
  const topArtists = Array.isArray(insights?.top_artists) ? insights.top_artists : [];

  return (
    <section className="studio-grid">
      <form className="glass-panel composer-panel" onSubmit={handleGenerate}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Composer</p>
            <h2>Dial in the mood</h2>
          </div>
          <span className="helper-badge">Live preview</span>
        </div>

        <div className="section-stack">
          <div>
            <label className="section-label">Mood</label>
            <div className="option-grid mood-grid">
              {moodOptions.map((option) => (
                <OptionCard
                  key={option.value}
                  active={form.mood === option.value}
                  title={option.label}
                  caption={option.caption}
                  onClick={() => updateForm("mood", option.value)}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="section-label">Genre</label>
            <div className="chip-row">
              {genreOptions.map((genre) => (
                <button
                  key={genre}
                  type="button"
                  className={`chip-button${form.genre === genre ? " is-active" : ""}`}
                  onClick={() => updateForm("genre", genre)}
                >
                  {genre}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="section-label">Vibe direction</label>
            <div className="option-grid vibe-grid">
              {vibeOptions.map((option) => (
                <OptionCard
                  key={option.value}
                  active={form.vibe === option.value}
                  title={option.label}
                  caption={option.description}
                  onClick={() => updateForm("vibe", option.value)}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="section-label">Seed Tracks (from your top tracks)</label>
            <div className="chip-row">
              {topTracks.slice(0, 8).map((track) => (
                <SeedChip
                  key={track.id}
                  active={Array.isArray(form.seed_track_ids) && form.seed_track_ids.includes(track.id)}
                  label={track.name}
                  onClick={() => toggleSeedTrack(track.id)}
                />
              ))}
            </div>
            {!topTracks.length ? <p className="surface-message">Top tracks unavailable right now.</p> : null}
          </div>

          <div>
            <label className="section-label">Seed Artists (from your top artists)</label>
            <div className="chip-row">
              {topArtists.slice(0, 8).map((artist) => (
                <SeedChip
                  key={artist.id}
                  active={Array.isArray(form.seed_artist_ids) && form.seed_artist_ids.includes(artist.id)}
                  label={artist.name}
                  onClick={() => toggleSeedArtist(artist.id)}
                />
              ))}
            </div>
            {!topArtists.length ? <p className="surface-message">Top artists unavailable right now.</p> : null}
          </div>

          <div className="tuning-grid">
            <label className="section-label">Audio Tuning</label>
            <button
              type="button"
              className={`segment-button${form.audio_tuning_enabled ? " is-active" : ""}`}
              onClick={() => updateForm("audio_tuning_enabled", !form.audio_tuning_enabled)}
            >
              {form.audio_tuning_enabled ? "Manual tuning enabled" : "Enable manual tuning"}
            </button>
            <label className="slider-field">
              <span>Energy</span>
              <input
                type="range"
                min="0"
                max="100"
                value={Number(form?.audio_tuning?.energy ?? 50)}
                onChange={(event) => updateAudioTuning("energy", event.target.value)}
                disabled={!form.audio_tuning_enabled}
              />
              <strong>{Number(form?.audio_tuning?.energy ?? 50)}</strong>
            </label>
            <label className="slider-field">
              <span>Valence</span>
              <input
                type="range"
                min="0"
                max="100"
                value={Number(form?.audio_tuning?.valence ?? 50)}
                onChange={(event) => updateAudioTuning("valence", event.target.value)}
                disabled={!form.audio_tuning_enabled}
              />
              <strong>{Number(form?.audio_tuning?.valence ?? 50)}</strong>
            </label>
            <label className="slider-field">
              <span>Danceability</span>
              <input
                type="range"
                min="0"
                max="100"
                value={Number(form?.audio_tuning?.danceability ?? 50)}
                onChange={(event) => updateAudioTuning("danceability", event.target.value)}
                disabled={!form.audio_tuning_enabled}
              />
              <strong>{Number(form?.audio_tuning?.danceability ?? 50)}</strong>
            </label>
          </div>

          <div className="controls-row">
            <div className="field-shell">
              <span className="section-label">Track count</span>
              <div className="segmented-group">
                {countOptions.map((count) => (
                  <button
                    key={count}
                    type="button"
                    className={`segment-button${form.count === count ? " is-active" : ""}`}
                    onClick={() => updateForm("count", count)}
                  >
                    {count} songs
                  </button>
                ))}
              </div>
            </div>

            <div className="field-shell">
              <span className="section-label">Visibility</span>
              <div className="segmented-group">
                {visibilityOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`segment-button${form.visibility === option.value ? " is-active" : ""}`}
                    onClick={() => updateForm("visibility", option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="preset-panel">
            <label className="section-label">Presets</label>
            <div className="preset-save-row">
              <input
                type="text"
                value={presetName}
                onChange={(event) => setPresetName(event.target.value)}
                placeholder="Preset name"
                className="preset-input"
              />
              <button type="button" className="ghost-button" onClick={handleSavePreset}>
                Save preset
              </button>
            </div>
            {presetMessage ? <p className="surface-message">{presetMessage}</p> : null}
            {Array.isArray(presets) && presets.length ? (
              <div className="preset-list">
                {presets.map((preset) => (
                  <div key={preset.id} className="preset-item">
                    <span>{preset.name}</span>
                    <div className="preset-actions">
                      <button type="button" className="ghost-button" onClick={() => applyPreset(preset)}>
                        Apply
                      </button>
                      <button type="button" className="ghost-button" onClick={() => deletePreset(preset.id)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="surface-message">No presets saved yet.</p>
            )}
          </div>
        </div>

        <div className="composer-footer">
          <div className="surface-message">
            {surfaceMessage || "Preview refreshes before creation, so you can inspect the mix and regenerate it before saving anything to Spotify."}
          </div>
          <button
            type="submit"
            className="primary-button large"
            disabled={isCreating || isPreviewing || !preview?.tracks?.length}
          >
            {isCreating ? "Creating playlist..." : "Create in Spotify"}
          </button>
        </div>
      </form>

      <div className="sidebar-stack">
        <PreviewTracksPanel
          summary={summary}
          preview={preview}
          isPreviewing={isPreviewing}
          previewError={previewError}
          handlePreview={handlePreview}
          handleRegenerate={handleRegenerate}
          handleRemoveTrack={handleRemoveTrack}
          handleMoveTrackUp={handleMoveTrackUp}
          handleMoveTrackDown={handleMoveTrackDown}
        />

        <ResultPanel result={result} />
      </div>
    </section>
  );
}
