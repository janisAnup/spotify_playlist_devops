export const moodOptions = [
  { value: "happy", label: "Happy", caption: "Sunlit, bright, replay-ready" },
  { value: "chill", label: "Chill", caption: "Late-night calm and easy momentum" },
  { value: "energetic", label: "Energetic", caption: "For workouts, motion, and momentum" },
  { value: "focus", label: "Focus", caption: "Sharp, steady, distraction-light" },
  { value: "romantic", label: "Romantic", caption: "Warm textures and soft edges" },
  { value: "sad", label: "Sad", caption: "Melancholic, reflective, cinematic" }
];

export const genreOptions = ["pop", "indie", "rock", "hip hop", "k-pop", "bollywood", "lofi"];

export const vibeOptions = [
  { value: "soft", label: "Soft", description: "Gentle layers and lighter energy" },
  { value: "dreamy", label: "Dreamy", description: "Airy, floating, and immersive" },
  { value: "party", label: "Party", description: "Crowd-ready and high-lift" },
  { value: "intense", label: "Intense", description: "Punchy, bold, and fast-moving" }
];

export const countOptions = [5, 10, 15, 20];

export const visibilityOptions = [
  { value: "false", label: "Private" },
  { value: "true", label: "Public" }
];

export const tabItems = [
  { id: "welcome", label: "Welcome", eyebrow: "Overview" },
  { id: "profile", label: "Profile", eyebrow: "Identity" },
  { id: "create", label: "Create", eyebrow: "Composer" },
  { id: "insights", label: "Insights", eyebrow: "Wrapped" },
  { id: "history", label: "History", eyebrow: "Archive" }
];

export const defaultForm = {
  mood: "chill",
  genre: "indie",
  vibe: "dreamy",
  count: 10,
  visibility: "false",
  seed_track_ids: [],
  seed_artist_ids: [],
  audio_tuning_enabled: false,
  audio_tuning: {
    energy: 50,
    valence: 50,
    danceability: 50
  }
};
