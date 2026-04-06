import os
import logging
from collections import Counter
from datetime import datetime, timezone

import requests
import spotipy
from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from spotipy.exceptions import SpotifyException

from spotify_auth import sp_oauth

load_dotenv()

DEFAULT_FRONTEND_DASHBOARD_URL = "http://127.0.0.1:5173/"
DEFAULT_MONGO_URI = "mongodb://127.0.0.1:27017/"
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 5000
MAX_TRACK_COUNT = 20
SEARCH_LIMIT_PER_QUERY = 10
MAX_TRACK_CANDIDATES = 120
MAX_SAME_TITLE_COUNT = 1
INSIGHTS_ARTIST_LIMIT = 8
INSIGHTS_TRACK_LIMIT = 8
INSIGHTS_GENRE_LIMIT = 6
MAX_SEED_ITEMS = 5
MAX_PRESETS_PER_USER = 20
MAX_AUDIO_FEATURE_BATCH_SIZE = 100
GENERIC_FALLBACK_QUERIES = [
    "top hits",
    "viral songs",
    "global top 50",
    "popular songs",
]
ARTIST_BATCH_SIZE = 50

MOOD_KEYWORDS = {
    "happy": ["happy", "feel good", "uplifting", "sunny", "joy"],
    "sad": ["sad", "melancholy", "heartbreak", "emotional", "slow"],
    "chill": ["chill", "relax", "calm", "laid back", "mellow"],
    "romantic": ["romantic", "love", "date night", "intimate", "heart"],
    "energetic": ["energetic", "workout", "hype", "dance", "power"],
    "focus": ["focus", "study", "instrumental", "concentration", "deep work"],
}

VIBE_KEYWORDS = {
    "soft": ["soft", "gentle", "acoustic", "light", "mellow"],
    "party": ["party", "club", "dance", "weekend", "celebration"],
    "dreamy": ["dreamy", "ethereal", "ambient", "night drive", "float"],
    "intense": ["intense", "power", "hard", "epic", "adrenaline"],
}

MOOD_AUDIO_TARGETS = {
    "happy": {
        "valence": 0.82,
        "energy": 0.66,
        "danceability": 0.72,
        "acousticness": 0.24,
        "instrumentalness": 0.10,
    },
    "sad": {
        "valence": 0.20,
        "energy": 0.28,
        "danceability": 0.36,
        "acousticness": 0.42,
        "instrumentalness": 0.22,
    },
    "chill": {
        "valence": 0.54,
        "energy": 0.34,
        "danceability": 0.46,
        "acousticness": 0.48,
        "instrumentalness": 0.24,
    },
    "romantic": {
        "valence": 0.58,
        "energy": 0.40,
        "danceability": 0.52,
        "acousticness": 0.34,
        "instrumentalness": 0.12,
    },
    "energetic": {
        "valence": 0.72,
        "energy": 0.88,
        "danceability": 0.78,
        "acousticness": 0.12,
        "instrumentalness": 0.06,
    },
    "focus": {
        "valence": 0.42,
        "energy": 0.38,
        "danceability": 0.34,
        "acousticness": 0.44,
        "instrumentalness": 0.58,
    },
}

VIBE_AUDIO_TARGETS = {
    "soft": {
        "valence": 0.56,
        "energy": 0.24,
        "danceability": 0.34,
        "acousticness": 0.56,
        "instrumentalness": 0.22,
    },
    "party": {
        "valence": 0.76,
        "energy": 0.92,
        "danceability": 0.86,
        "acousticness": 0.10,
        "instrumentalness": 0.04,
    },
    "dreamy": {
        "valence": 0.52,
        "energy": 0.36,
        "danceability": 0.42,
        "acousticness": 0.40,
        "instrumentalness": 0.28,
    },
    "intense": {
        "valence": 0.44,
        "energy": 0.96,
        "danceability": 0.70,
        "acousticness": 0.08,
        "instrumentalness": 0.04,
    },
}

DISPLAY_GENRE_NAMES = {
    "hip hop": "Hip-Hop",
    "k-pop": "K-Pop",
    "lofi": "Lo-Fi",
}

MOOD_NAME_PREFIXES = {
    "happy": ["Sunlit", "Golden", "Brightside", "Daydream"],
    "sad": ["Blue Hour", "Afterglow", "Velvet Rain", "Quiet Night"],
    "chill": ["Lowkey", "Midnight", "Easy", "Coastline"],
    "romantic": ["Moonlit", "Velvet", "Heartbeat", "Slow Burn"],
    "energetic": ["Neon", "High Voltage", "Momentum", "Lift Off"],
    "focus": ["Deep", "Signal", "Still", "Clear Mind"],
}

VIBE_NAME_SUFFIXES = {
    "soft": ["Bloom", "Drift", "Glow", "Velvet"],
    "dreamy": ["Afterglow", "Cloudline", "Starlight", "Haze"],
    "party": ["Anthem", "Rush", "Lift", "Night Run"],
    "intense": ["Surge", "Ignition", "Charge", "Pressure"],
}

GENRE_ALIASES = {
    "hip hop": ["hip hop", "hip-hop", "rap"],
    "k-pop": ["k-pop", "kpop", "korean pop"],
    "lofi": ["lofi", "lo-fi", "beats"],
    "bollywood": ["bollywood", "hindi", "filmi"],
}

STRICT_GENRE_RULES = {
    "bollywood": {
        "required_any": ["bollywood", "filmi", "hindi", "indian"],
        "blocked_any": ["k-pop", "kpop", "korean", "bts", "blackpink", "j-pop", "jpop"],
    },
    "k-pop": {
        "required_any": ["k-pop", "kpop", "korean pop", "korean"],
        "blocked_any": ["bollywood", "filmi", "hindi"],
    },
    "hip hop": {
        "required_any": ["hip hop", "hip-hop", "rap", "trap"],
        "blocked_any": ["bollywood", "filmi", "k-pop", "kpop"],
    },
    "lofi": {
        "required_any": ["lofi", "lo-fi", "chillhop", "beats"],
        "blocked_any": ["k-pop", "kpop"],
    },
    "indie": {
        "required_any": ["indie", "indie pop", "indie rock", "indietronica", "indie folk"],
        "blocked_any": [],
    },
}


def get_int_env(env_name, default_value):
    raw_value = os.getenv(env_name, str(default_value)).strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {env_name} must be an integer."
        ) from exc


MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI).strip() or DEFAULT_MONGO_URI
FRONTEND_DASHBOARD_URL = (
    os.getenv("FRONTEND_DASHBOARD_URL", DEFAULT_FRONTEND_DASHBOARD_URL).strip()
    or DEFAULT_FRONTEND_DASHBOARD_URL
)
APP_HOST = os.getenv("APP_HOST", DEFAULT_APP_HOST).strip() or DEFAULT_APP_HOST
APP_PORT = get_int_env("PORT", DEFAULT_APP_PORT)

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = mongo_client["spotify_playlist_db"]
playlists_collection = db["playlists"]
presets_collection = db["presets"]
SPOTIPY_CLIENT_LOGGER = logging.getLogger("spotipy.client")
SPOTIPY_CLIENT_LOGGER.setLevel(logging.CRITICAL)
SPOTIPY_CLIENT_LOGGER.propagate = False


def error_response(message, status_code, details=None, warning=None):
    payload = {"error": message}
    if details is not None:
        payload["details"] = details
    if warning:
        payload["warning"] = warning
    return jsonify(payload), status_code


def success_response(payload, status_code=200, warning=None):
    response_payload = dict(payload)
    if warning:
        response_payload["warning"] = warning
    return jsonify(response_payload), status_code


def get_exception_message(error):
    return str(error) or error.__class__.__name__


def get_spotify_exception_status(error):
    return getattr(error, "http_status", None) or 500


def handle_spotify_exception(message, error):
    return error_response(
        message,
        get_spotify_exception_status(error),
        details=get_exception_message(error),
    )


def normalize_text(value):
    return str(value or "").strip().lower()


def unique_preserve_order(items):
    seen = set()
    unique_items = []

    for item in items:
        normalized_item = item.strip()
        if not normalized_item or normalized_item in seen:
            continue
        seen.add(normalized_item)
        unique_items.append(normalized_item)

    return unique_items


def get_display_genre_name(genre):
    normalized_genre = normalize_text(genre)
    if not normalized_genre:
        return "Playlist"

    if normalized_genre in DISPLAY_GENRE_NAMES:
        return DISPLAY_GENRE_NAMES[normalized_genre]

    return " ".join(word.capitalize() for word in normalized_genre.split())


def chunked(items, chunk_size):
    for index in range(0, len(items), chunk_size):
        yield items[index:index + chunk_size]


def get_genre_terms(genre):
    normalized_genre = normalize_text(genre)
    aliases = GENRE_ALIASES.get(normalized_genre, [])
    return unique_preserve_order([normalized_genre, *aliases])


def parse_playlist_request(data):
    mood = normalize_text(data.get("mood"))
    genre = normalize_text(data.get("genre"))
    vibe = normalize_text(data.get("vibe"))
    raw_count = str(data.get("count", "10")).strip()
    raw_visibility = normalize_text(data.get("visibility", "false"))
    raw_audio_tuning_enabled = normalize_text(data.get("audio_tuning_enabled", "false"))

    if not mood or not genre:
        return None, error_response("Both mood and genre are required.", 400)

    try:
        requested_count = int(raw_count.split()[0])
    except (ValueError, TypeError, IndexError):
        return None, error_response("Count must be a number between 1 and 20.", 400)

    count = max(1, min(requested_count, MAX_TRACK_COUNT))
    is_public = raw_visibility in {"true", "public", "yes"}
    seed_track_ids = parse_seed_ids(data.get("seed_track_ids"))
    seed_artist_ids = parse_seed_ids(data.get("seed_artist_ids"))
    audio_tuning_enabled = raw_audio_tuning_enabled in {"true", "yes", "1", "on"}
    audio_tuning = parse_audio_tuning(data.get("audio_tuning")) if audio_tuning_enabled else {}

    return {
        "mood": mood,
        "genre": genre,
        "vibe": vibe,
        "count": count,
        "is_public": is_public,
        "seed_track_ids": seed_track_ids,
        "seed_artist_ids": seed_artist_ids,
        "audio_tuning_enabled": audio_tuning_enabled,
        "audio_tuning": audio_tuning,
    }, None


def parse_seed_ids(raw_items):
    if not isinstance(raw_items, list):
        return []

    return unique_preserve_order(
        [
            str(item).strip()
            for item in raw_items
            if str(item).strip()
        ]
    )[:MAX_SEED_ITEMS]


def parse_audio_tuning(raw_tuning):
    if not isinstance(raw_tuning, dict):
        return {}

    parsed_tuning = {}
    for feature_name in ("energy", "valence", "danceability"):
        raw_value = raw_tuning.get(feature_name)
        if raw_value in (None, "", False):
            continue

        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue

        clamped_value = max(0.0, min(100.0, numeric_value))
        parsed_tuning[feature_name] = round(clamped_value / 100.0, 4)

    return parsed_tuning


def parse_variation_index(data):
    try:
        return max(0, int(data.get("variation", 0) or 0))
    except (TypeError, ValueError):
        return 0


def get_token():
    token_info = session.get("token_info")
    if not token_info or not token_info.get("access_token"):
        session.pop("token_info", None)
        return None

    refresh_token = token_info.get("refresh_token")

    try:
        if token_info.get("expires_at") and sp_oauth.is_token_expired(token_info):
            if not refresh_token:
                session.pop("token_info", None)
                return None

            refreshed_token = sp_oauth.refresh_access_token(refresh_token)
            if refresh_token and "refresh_token" not in refreshed_token:
                refreshed_token["refresh_token"] = refresh_token

            session["token_info"] = refreshed_token
            token_info = refreshed_token
    except Exception:
        session.pop("token_info", None)
        return None

    return token_info


def get_spotify_client():
    token_info = get_token()
    if not token_info:
        return None, error_response("Please login first at /login.", 401)

    spotify_client = spotipy.Spotify(
        auth=token_info["access_token"],
        requests_timeout=10,
        retries=3,
    )
    return spotify_client, None


def safe_fetch_artists(sp, artist_ids):
    if not artist_ids:
        return []

    previous_level = SPOTIPY_CLIENT_LOGGER.level
    SPOTIPY_CLIENT_LOGGER.setLevel(logging.CRITICAL)
    try:
        response = sp.artists(artist_ids)
        return response.get("artists", []) if isinstance(response, dict) else []
    except SpotifyException as error:
        if error.http_status in {401, 403, 404, 429}:
            return []
        raise
    except Exception:
        return []
    finally:
        SPOTIPY_CLIENT_LOGGER.setLevel(previous_level)


def build_search_queries(mood, genre, vibe):
    mood_terms = MOOD_KEYWORDS.get(mood, [])[:2]
    vibe_terms = VIBE_KEYWORDS.get(vibe, [])[:2]

    queries = [
        f"{mood} {genre}",
        f"{vibe} {genre}",
        f"{mood} {vibe} {genre}",
        f"{genre} playlist",
        f"best of {genre}",
        f"{genre} hits",
        f"{genre} music",
    ]

    queries.extend(f"{genre} {term}" for term in mood_terms)
    queries.extend(f"{genre} {term}" for term in vibe_terms)

    return unique_preserve_order([query[:80] for query in queries])


def search_tracks(access_token, query, limit=SEARCH_LIMIT_PER_QUERY):
    response = requests.get(
        "https://api.spotify.com/v1/search",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        params={
            "q": query,
            "type": "track",
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("tracks", {}).get("items", [])


def get_audio_features(access_token, track_ids):
    response = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        params={
            "ids": ",".join(track_ids),
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("audio_features", [])


def collect_candidate_tracks(access_token, queries):
    collected_tracks = []
    seen_track_ids = set()

    for query in queries:
        try:
            tracks = search_tracks(access_token, query)
        except Exception:
            continue

        for track in tracks:
            track_id = track.get("id")
            if not track_id or track_id in seen_track_ids:
                continue

            seen_track_ids.add(track_id)
            collected_tracks.append(track)

            if len(collected_tracks) >= MAX_TRACK_CANDIDATES:
                return collected_tracks

    return collected_tracks


def collect_seed_candidate_tracks(
    sp,
    seed_track_ids=None,
    seed_artist_ids=None,
    count=20,
    audio_tuning=None,
):
    seed_track_ids = parse_seed_ids(seed_track_ids)
    seed_artist_ids = parse_seed_ids(seed_artist_ids)

    if not seed_track_ids and not seed_artist_ids:
        return []

    recommendation_kwargs = {
        "limit": max(20, min(MAX_TRACK_CANDIDATES, count * 4)),
    }

    trimmed_seed_tracks = seed_track_ids[:MAX_SEED_ITEMS]
    remaining_seed_slots = max(0, MAX_SEED_ITEMS - len(trimmed_seed_tracks))
    trimmed_seed_artists = seed_artist_ids[:remaining_seed_slots]

    if trimmed_seed_tracks:
        recommendation_kwargs["seed_tracks"] = trimmed_seed_tracks

    if trimmed_seed_artists:
        recommendation_kwargs["seed_artists"] = trimmed_seed_artists

    if isinstance(audio_tuning, dict):
        for feature_name in ("energy", "valence", "danceability"):
            if feature_name in audio_tuning:
                recommendation_kwargs[f"target_{feature_name}"] = audio_tuning[feature_name]

    collected_tracks = []
    seen_track_ids = set()

    try:
        recommendation_items = sp.recommendations(**recommendation_kwargs).get("tracks", [])
    except Exception:
        recommendation_items = []

    for track in recommendation_items:
        track_id = (track or {}).get("id")
        if not track_id or track_id in seen_track_ids:
            continue
        seen_track_ids.add(track_id)
        collected_tracks.append(track)

    for artist_id in seed_artist_ids:
        try:
            artist_top_tracks = sp.artist_top_tracks(artist_id).get("tracks", [])
        except Exception:
            continue

        for track in artist_top_tracks:
            track_id = (track or {}).get("id")
            if not track_id or track_id in seen_track_ids:
                continue
            seen_track_ids.add(track_id)
            collected_tracks.append(track)
            if len(collected_tracks) >= MAX_TRACK_CANDIDATES:
                return collected_tracks

    return collected_tracks


def get_artist_genre_map(sp, tracks):
    artist_ids = unique_preserve_order(
        [
            artist_id
            for track in tracks
            for artist_id in [artist.get("id") for artist in track.get("artists", [])]
            if artist_id
        ]
    )

    artist_genre_map = {}

    for artist_batch in chunked(artist_ids, ARTIST_BATCH_SIZE):
        for artist in safe_fetch_artists(sp, artist_batch):
            if not artist or not artist.get("id"):
                continue

            artist_genre_map[artist["id"]] = [
                normalize_text(genre_name)
                for genre_name in artist.get("genres", [])
            ]

    return artist_genre_map


def get_track_blob(track):
    track_name = track.get("name", "")
    album_name = track.get("album", {}).get("name", "")
    artist_names = " ".join(artist.get("name", "") for artist in track.get("artists", []))
    return f"{track_name} {album_name} {artist_names}".lower()


def get_track_uri(track):
    uri = track.get("uri")
    if isinstance(uri, str) and uri.startswith("spotify:track:"):
        return uri
    return None


def get_track_unique_key(track):
    artist_names = " ".join(artist.get("name", "") for artist in track.get("artists", []))
    track_name = track.get("name", "")
    return f"{track_name.strip().lower()}|{artist_names.strip().lower()}"


def get_track_title_key(track):
    return normalize_text(track.get("name"))


def get_track_artist_genres(track, artist_genre_map):
    genres = []

    for artist in track.get("artists", []):
        artist_id = artist.get("id")
        if not artist_id:
            continue

        genres.extend(artist_genre_map.get(artist_id, []))

    return unique_preserve_order(genres)


def get_track_search_blob(track, artist_genre_map):
    artist_genres = " ".join(get_track_artist_genres(track, artist_genre_map))
    return f"{get_track_blob(track)} {artist_genres}".strip()


def get_track_artist_genre_blob(track, artist_genre_map):
    return " ".join(get_track_artist_genres(track, artist_genre_map))


def build_audio_target_profile(mood, vibe, audio_tuning=None):
    feature_names = [
        "valence",
        "energy",
        "danceability",
        "acousticness",
        "instrumentalness",
    ]
    mood_profile = MOOD_AUDIO_TARGETS.get(mood, {})
    vibe_profile = VIBE_AUDIO_TARGETS.get(vibe, {})
    combined_profile = {}

    for feature_name in feature_names:
        values = [
            value
            for value in (
                mood_profile.get(feature_name),
                vibe_profile.get(feature_name),
            )
            if value is not None
        ]
        if values:
            combined_profile[feature_name] = sum(values) / len(values)

    if audio_tuning:
        for feature_name, custom_value in audio_tuning.items():
            if feature_name not in feature_names:
                continue

            if feature_name in combined_profile:
                combined_profile[feature_name] = (
                    combined_profile[feature_name] * 0.55 + custom_value * 0.45
                )
            else:
                combined_profile[feature_name] = custom_value

    return combined_profile


def get_audio_feature_map(access_token, tracks):
    track_ids = unique_preserve_order(
        [track.get("id", "").strip() for track in tracks if track.get("id")]
    )
    audio_feature_map = {}

    for track_id_batch in chunked(track_ids, MAX_AUDIO_FEATURE_BATCH_SIZE):
        try:
            feature_items = get_audio_features(access_token, track_id_batch)
        except Exception:
            continue

        for feature_item in feature_items:
            if not feature_item or not feature_item.get("id"):
                continue
            audio_feature_map[feature_item["id"]] = feature_item

    return audio_feature_map


def score_audio_profile(track, mood, vibe, audio_feature_map, audio_tuning=None):
    track_id = track.get("id")
    audio_features = audio_feature_map.get(track_id)
    if not audio_features:
        return 0.0

    target_profile = build_audio_target_profile(mood, vibe, audio_tuning=audio_tuning)
    if not target_profile:
        return 0.0

    score = 0.0

    for feature_name, target_value in target_profile.items():
        feature_value = audio_features.get(feature_name)
        if feature_value is None:
            continue

        difference = abs(feature_value - target_value)
        score += max(0.0, 1.0 - difference) * 18

    return score


def score_title_genericity(track, mood, genre, vibe):
    title = get_track_title_key(track)
    if not title:
        return 0.0

    request_terms = set(
        unique_preserve_order(
            [
                mood,
                vibe,
                *get_genre_terms(genre),
                *MOOD_KEYWORDS.get(mood, [])[:2],
                *VIBE_KEYWORDS.get(vibe, [])[:2],
            ]
        )
    )
    title_words = [word for word in title.replace("-", " ").split() if word]
    if not title_words:
        return 0.0

    matched_words = sum(
        1 for word in title_words if any(term == word or term.startswith(f"{word} ") for term in request_terms)
    )
    if len(title_words) <= 4 and matched_words >= max(1, len(title_words) - 1):
        return -30.0

    if matched_words >= 2:
        return -14.0

    return 0.0


def has_required_genre_terms(blob, terms):
    return any(term in blob for term in terms)


def is_strict_genre_match(track, genre, artist_genre_map):
    normalized_genre = normalize_text(genre)
    searchable_blob = get_track_search_blob(track, artist_genre_map)
    artist_genre_blob = get_track_artist_genre_blob(track, artist_genre_map)
    genre_rule = STRICT_GENRE_RULES.get(normalized_genre)
    genre_terms = get_genre_terms(normalized_genre)
    artist_genres = get_track_artist_genres(track, artist_genre_map)
    has_artist_genre_data = bool(artist_genres)

    if genre_rule:
        if any(blocked_term in searchable_blob for blocked_term in genre_rule["blocked_any"]):
            return False

        if has_artist_genre_data:
            return has_required_genre_terms(
                artist_genre_blob,
                genre_rule["required_any"] + genre_terms,
            )

        if has_required_genre_terms(searchable_blob, genre_rule["required_any"]):
            return True

        if has_required_genre_terms(searchable_blob, genre_terms):
            return True

    if has_artist_genre_data:
        return has_required_genre_terms(artist_genre_blob, genre_terms)

    return has_required_genre_terms(searchable_blob, genre_terms)


def is_blocked_genre_mismatch(track, genre, artist_genre_map):
    normalized_genre = normalize_text(genre)
    genre_rule = STRICT_GENRE_RULES.get(normalized_genre)
    if not genre_rule:
        return False

    searchable_blob = get_track_search_blob(track, artist_genre_map)
    artist_genre_blob = get_track_artist_genre_blob(track, artist_genre_map)
    artist_genres = get_track_artist_genres(track, artist_genre_map)

    if any(blocked_term in searchable_blob for blocked_term in genre_rule["blocked_any"]):
        return True

    if artist_genres and not is_strict_genre_match(track, genre, artist_genre_map):
        return True

    return False


def score_track(
    track,
    mood,
    genre,
    vibe,
    artist_genre_map,
    audio_feature_map,
    audio_tuning=None,
):
    blob = get_track_search_blob(track, artist_genre_map)
    popularity = track.get("popularity", 0)
    score = float(popularity)

    base_terms = [mood, vibe, *get_genre_terms(genre)]
    mood_terms = MOOD_KEYWORDS.get(mood, [])
    vibe_terms = VIBE_KEYWORDS.get(vibe, [])

    for term in unique_preserve_order(base_terms):
        if term and term in blob:
            score += 12

    for term in mood_terms:
        if term in blob:
            score += 6

    for term in vibe_terms:
        if term in blob:
            score += 5

    if track.get("explicit") is False:
        score += 1

    if is_strict_genre_match(track, genre, artist_genre_map):
        score += 20
    else:
        score -= 25

    score += score_audio_profile(
        track,
        mood,
        vibe,
        audio_feature_map,
        audio_tuning=audio_tuning,
    )
    score += score_title_genericity(track, mood, genre, vibe)

    return score


def enforce_artist_diversity(tracks, max_per_artist=1):
    artist_count = {}
    filtered_tracks = []

    for track in tracks:
        artists = track.get("artists", [])
        if not artists:
            continue

        main_artist = artists[0].get("name", "").strip().lower()
        if not main_artist:
            continue

        if artist_count.get(main_artist, 0) < max_per_artist:
            filtered_tracks.append(track)
            artist_count[main_artist] = artist_count.get(main_artist, 0) + 1

    return filtered_tracks


def rank_and_select_tracks(
    tracks,
    mood,
    genre,
    vibe,
    count,
    artist_genre_map,
    audio_feature_map,
    exclude_track_ids=None,
    audio_tuning=None,
):
    scored_tracks = []
    seen_unique_tracks = set()
    excluded_track_ids = set(exclude_track_ids or [])

    for track in tracks:
        track_id = track.get("id")
        if not get_track_uri(track) or not track_id or track_id in excluded_track_ids:
            continue

        unique_key = get_track_unique_key(track)
        if unique_key in seen_unique_tracks:
            continue
        seen_unique_tracks.add(unique_key)

        scored_tracks.append(
            {
                "score": score_track(
                    track,
                    mood,
                    genre,
                    vibe,
                    artist_genre_map,
                    audio_feature_map,
                    audio_tuning=audio_tuning,
                ),
                "track": track,
            }
        )

    scored_tracks.sort(
        key=lambda item: (
            item["score"],
            item["track"].get("popularity", 0),
            item["track"].get("name", "").lower(),
        ),
        reverse=True,
    )

    ranked_tracks = [item["track"] for item in scored_tracks]
    strict_genre_tracks = [
        track for track in ranked_tracks if is_strict_genre_match(track, genre, artist_genre_map)
    ]
    relaxed_genre_tracks = [
        track
        for track in ranked_tracks
        if track not in strict_genre_tracks
        and not is_blocked_genre_mismatch(track, genre, artist_genre_map)
    ]

    selected_tracks = []
    selected_ids = set()

    selected_title_counts = {}

    def append_tracks(track_list, max_per_artist):
        diverse_tracks = enforce_artist_diversity(track_list, max_per_artist=max_per_artist)
        for track in diverse_tracks:
            track_id = track.get("id")
            if not track_id or track_id in selected_ids:
                continue

            title_key = get_track_title_key(track)
            if title_key and selected_title_counts.get(title_key, 0) >= MAX_SAME_TITLE_COUNT:
                continue

            selected_tracks.append(track)
            selected_ids.add(track_id)
            if title_key:
                selected_title_counts[title_key] = selected_title_counts.get(title_key, 0) + 1
            if len(selected_tracks) >= count:
                return True
        return False

    max_per_artist = 1 if count <= 10 else 2

    if append_tracks(strict_genre_tracks, max_per_artist=max_per_artist):
        return selected_tracks[:count]

    if append_tracks(relaxed_genre_tracks, max_per_artist=max_per_artist):
        return selected_tracks[:count]

    append_tracks(ranked_tracks, max_per_artist=max_per_artist)
    return selected_tracks[:count]


def build_playlist_name(mood, genre, vibe, variation=0):
    normalized_variation = max(0, int(variation or 0))
    mood_terms = MOOD_NAME_PREFIXES.get(mood, [mood.title() or "Custom"])
    vibe_terms = VIBE_NAME_SUFFIXES.get(vibe, ["Mix", "Sessions", "Select"])
    mood_term = mood_terms[normalized_variation % len(mood_terms)]
    vibe_term = vibe_terms[(normalized_variation + 1) % len(vibe_terms)]
    genre_name = get_display_genre_name(genre)
    return f"{mood_term} {genre_name} {vibe_term}"


def build_playlist_description(mood, genre, vibe, is_public):
    mood_label = mood.title() if mood else "Custom"
    genre_label = get_display_genre_name(genre)
    vibe_label = vibe.title() if vibe else "Balanced"
    visibility = "public" if is_public else "private"
    return (
        f"{mood_label} mood, {genre_label} direction, {vibe_label.lower()} finish. "
        f"Generated by Spotify Playlist Generator and saved as {visibility}."
    )


def select_playlist_tracks(
    sp,
    access_token,
    mood,
    genre,
    vibe,
    count,
    exclude_track_ids=None,
    seed_track_ids=None,
    seed_artist_ids=None,
    audio_tuning=None,
):
    search_queries = build_search_queries(mood, genre, vibe)
    candidate_tracks = collect_candidate_tracks(access_token, search_queries)
    seed_candidate_tracks = collect_seed_candidate_tracks(
        sp,
        seed_track_ids=seed_track_ids,
        seed_artist_ids=seed_artist_ids,
        count=count,
        audio_tuning=audio_tuning,
    )

    if seed_candidate_tracks:
        merged_tracks = []
        seen_track_ids = set()

        for track in [*seed_candidate_tracks, *candidate_tracks]:
            track_id = (track or {}).get("id")
            if not track_id or track_id in seen_track_ids:
                continue
            seen_track_ids.add(track_id)
            merged_tracks.append(track)
            if len(merged_tracks) >= MAX_TRACK_CANDIDATES:
                break

        candidate_tracks = merged_tracks

    if not candidate_tracks:
        fallback_queries = GENERIC_FALLBACK_QUERIES + [f"{genre} songs"]
        candidate_tracks = collect_candidate_tracks(access_token, fallback_queries)
        if seed_candidate_tracks:
            fallback_merged = []
            seen_track_ids = set()
            for track in [*seed_candidate_tracks, *candidate_tracks]:
                track_id = (track or {}).get("id")
                if not track_id or track_id in seen_track_ids:
                    continue
                seen_track_ids.add(track_id)
                fallback_merged.append(track)
                if len(fallback_merged) >= MAX_TRACK_CANDIDATES:
                    break
            candidate_tracks = fallback_merged

    if not candidate_tracks:
        return [], []

    artist_genre_map = get_artist_genre_map(sp, candidate_tracks)
    audio_feature_map = get_audio_feature_map(access_token, candidate_tracks)
    selected_tracks = rank_and_select_tracks(
        candidate_tracks,
        mood,
        genre,
        vibe,
        count,
        artist_genre_map,
        audio_feature_map,
        exclude_track_ids=exclude_track_ids,
        audio_tuning=audio_tuning,
    )

    if not selected_tracks and exclude_track_ids:
        selected_tracks = rank_and_select_tracks(
            candidate_tracks,
            mood,
            genre,
            vibe,
            count,
            artist_genre_map,
            audio_feature_map,
            audio_tuning=audio_tuning,
        )

    warning_messages = []
    if selected_tracks and len(selected_tracks) < count:
        warning_messages.append(
            f"Only {len(selected_tracks)} matching tracks were found for the selected filters."
        )

    return selected_tracks, warning_messages


def get_tracks_by_ids(sp, track_ids, market=None):
    ordered_track_ids = unique_preserve_order(
        [str(track_id).strip() for track_id in track_ids if str(track_id).strip()]
    )
    if not ordered_track_ids:
        return []

    track_lookup = {}

    for track_id_batch in chunked(ordered_track_ids, ARTIST_BATCH_SIZE):
        try:
            request_kwargs = {}
            if market:
                request_kwargs["market"] = market
            response = sp.tracks(track_id_batch, **request_kwargs)
        except Exception:
            continue

        for track in response.get("tracks", []):
            if track and track.get("id"):
                track_lookup[track["id"]] = track

    return [track_lookup[track_id] for track_id in ordered_track_ids if track_id in track_lookup]


def create_playlist(access_token, playlist_name, description, is_public):
    response = requests.post(
        "https://api.spotify.com/v1/me/playlists",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "name": playlist_name,
            "public": is_public,
            "description": description,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def persist_playlist_history(payload):
    try:
        history_payload = dict(payload)
        history_payload["created_at"] = datetime.now(timezone.utc).isoformat()
        playlists_collection.insert_one(history_payload)
        return None
    except PyMongoError:
        return "Playlist created on Spotify, but history could not be saved."


def serialize_preset(preset_doc):
    return {
        "id": str(preset_doc.get("_id")),
        "name": preset_doc.get("name", "Untitled preset"),
        "config": preset_doc.get("config", {}),
        "created_at": preset_doc.get("created_at"),
        "updated_at": preset_doc.get("updated_at"),
    }


@app.route("/")
def home():
    return success_response({"message": "Spotify Playlist Generator API is running"})


@app.route("/health")
def health():
    try:
        mongo_client.admin.command("ping")
        return success_response(
            {
                "message": "API is running.",
                "database": "connected",
            }
        )
    except Exception as error:
        return error_response(
            "Database connection failed.",
            500,
            details=get_exception_message(error),
        )


@app.route("/login")
def login():
    return redirect(sp_oauth.get_authorize_url())


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return error_response("No code received from Spotify.", 400)

    try:
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        session["token_info"] = token_info
        return redirect(FRONTEND_DASHBOARD_URL)
    except Exception as error:
        return error_response(
            "Spotify auth failed.",
            500,
            details=get_exception_message(error),
        )


@app.route("/logout")
def logout():
    session.clear()
    return success_response({"message": "Logged out successfully."})


@app.route("/playlist_history")
def playlist_history():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        user = sp.current_user()
        history_items = list(
            playlists_collection.find(
                {"user_id": user["id"]},
                {
                    "_id": 0,
                    "playlist_name": 1,
                    "playlist_url": 1,
                    "mood": 1,
                    "genre": 1,
                    "vibe": 1,
                    "count": 1,
                    "public": 1,
                    "created_at": 1,
                },
            )
            .sort("created_at", -1)
            .limit(6)
        )
        return success_response({"playlists": history_items})
    except SpotifyException as error:
        return handle_spotify_exception(
            "Spotify API error while loading playlist history.",
            error,
        )
    except PyMongoError as error:
        return error_response(
            "Unable to load playlist history.",
            500,
            details=get_exception_message(error),
        )
    except Exception as error:
        return error_response(
            "Unexpected error while loading playlist history.",
            500,
            details=get_exception_message(error),
        )


@app.route("/presets", methods=["GET"])
def list_presets():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        user = sp.current_user()
        user_id = user.get("id")
        if not user_id:
            return error_response("Unable to identify the current user.", 500)

        preset_docs = list(
            presets_collection.find(
                {"user_id": user_id},
                {
                    "_id": 1,
                    "name": 1,
                    "config": 1,
                    "created_at": 1,
                    "updated_at": 1,
                },
            )
            .sort("updated_at", -1)
            .limit(MAX_PRESETS_PER_USER)
        )

        return success_response(
            {
                "presets": [serialize_preset(preset_doc) for preset_doc in preset_docs]
            }
        )
    except PyMongoError as error:
        return error_response(
            "Unable to load presets.",
            500,
            details=get_exception_message(error),
        )
    except Exception as error:
        return error_response(
            "Unexpected error while loading presets.",
            500,
            details=get_exception_message(error),
        )


@app.route("/presets", methods=["POST"])
def create_preset():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    request_data = request.get_json(silent=True)
    if not request_data:
        return error_response("Request body must be valid JSON.", 400)

    raw_name = str(request_data.get("name", "")).strip()
    if not raw_name:
        return error_response("Preset name is required.", 400)

    preset_name = raw_name[:64]
    config_payload = request_data.get("config")
    if not isinstance(config_payload, dict):
        return error_response("Preset config must be an object.", 400)

    playlist_request, validation_error = parse_playlist_request(config_payload)
    if validation_error:
        return validation_error

    try:
        user = sp.current_user()
        user_id = user.get("id")
        if not user_id:
            return error_response("Unable to identify the current user.", 500)

        now = datetime.now(timezone.utc).isoformat()
        preset_doc = {
            "user_id": user_id,
            "name": preset_name,
            "config": {
                "mood": playlist_request["mood"],
                "genre": playlist_request["genre"],
                "vibe": playlist_request["vibe"],
                "count": playlist_request["count"],
                "visibility": "true" if playlist_request["is_public"] else "false",
                "seed_track_ids": playlist_request["seed_track_ids"],
                "seed_artist_ids": playlist_request["seed_artist_ids"],
                "audio_tuning_enabled": playlist_request["audio_tuning_enabled"],
                "audio_tuning": {
                    feature: round(value * 100, 2)
                    for feature, value in playlist_request["audio_tuning"].items()
                },
            },
            "created_at": now,
            "updated_at": now,
        }

        existing_count = presets_collection.count_documents({"user_id": user_id})
        if existing_count >= MAX_PRESETS_PER_USER:
            oldest_doc = presets_collection.find_one(
                {"user_id": user_id},
                sort=[("updated_at", 1)],
                projection={"_id": 1},
            )
            if oldest_doc and oldest_doc.get("_id"):
                presets_collection.delete_one({"_id": oldest_doc["_id"]})

        insert_result = presets_collection.insert_one(preset_doc)
        preset_doc["_id"] = insert_result.inserted_id

        return success_response(
            {
                "message": "Preset saved.",
                "preset": serialize_preset(preset_doc),
            },
            status_code=201,
        )
    except PyMongoError as error:
        return error_response(
            "Unable to save preset.",
            500,
            details=get_exception_message(error),
        )
    except Exception as error:
        return error_response(
            "Unexpected error while saving preset.",
            500,
            details=get_exception_message(error),
        )


@app.route("/presets/<preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        user = sp.current_user()
        user_id = user.get("id")
        if not user_id:
            return error_response("Unable to identify the current user.", 500)

        try:
            object_id = ObjectId(preset_id)
        except Exception:
            return error_response("Invalid preset id.", 400)

        delete_result = presets_collection.delete_one(
            {
                "_id": object_id,
                "user_id": user_id,
            }
        )

        if delete_result.deleted_count == 0:
            return error_response("Preset not found.", 404)

        return success_response({"message": "Preset deleted."})
    except PyMongoError as error:
        return error_response(
            "Unable to delete preset.",
            500,
            details=get_exception_message(error),
        )
    except Exception as error:
        return error_response(
            "Unexpected error while deleting preset.",
            500,
            details=get_exception_message(error),
        )


def serialize_top_artist(artist):
    images = artist.get("images") or []
    return {
        "id": artist.get("id"),
        "name": artist.get("name"),
        "genres": artist.get("genres", []),
        "popularity": artist.get("popularity", 0),
        "followers": (artist.get("followers") or {}).get("total", 0),
        "image_url": images[0].get("url") if images else None,
        "spotify_url": (artist.get("external_urls") or {}).get("spotify"),
    }


def serialize_top_track(track):
    album = track.get("album") or {}
    images = album.get("images") or []
    return {
        "id": track.get("id"),
        "name": track.get("name"),
        "album_name": album.get("name"),
        "artists": [artist.get("name") for artist in track.get("artists", []) if artist.get("name")],
        "popularity": track.get("popularity", 0),
        "image_url": images[0].get("url") if images else None,
        "spotify_url": (track.get("external_urls") or {}).get("spotify"),
        "preview_url": track.get("preview_url"),
    }


def serialize_playlist_track(track):
    album = track.get("album") or {}
    images = album.get("images") or []
    return {
        "id": track.get("id"),
        "name": track.get("name"),
        "album_name": album.get("name"),
        "artists": [
            artist.get("name")
            for artist in track.get("artists", [])
            if artist.get("name")
        ],
        "image_url": images[0].get("url") if images else None,
        "spotify_url": (track.get("external_urls") or {}).get("spotify"),
        "preview_url": track.get("preview_url"),
    }


def get_top_genres(artists):
    genre_counter = Counter()

    for artist in artists:
        for genre_name in artist.get("genres", []):
            normalized_genre = normalize_text(genre_name)
            if normalized_genre:
                genre_counter[normalized_genre] += 1

    return [
        {"name": genre_name.title(), "count": count}
        for genre_name, count in genre_counter.most_common(INSIGHTS_GENRE_LIMIT)
    ]


def enrich_top_artists(sp, artists):
    artist_ids = [artist.get("id") for artist in artists if artist.get("id")]
    if not artist_ids:
        return artists

    artist_lookup = {
        artist.get("id"): artist
        for artist in safe_fetch_artists(sp, artist_ids)
        if artist and artist.get("id")
    }

    enriched_artists = []

    for artist in artists:
        artist_id = artist.get("id")
        enriched_artists.append(artist_lookup.get(artist_id, artist))

    return enriched_artists


@app.route("/insights")
def insights():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        user = sp.current_user()
        top_artists_response = sp.current_user_top_artists(
            limit=INSIGHTS_ARTIST_LIMIT,
            time_range="medium_term",
        )
        top_tracks_response = sp.current_user_top_tracks(
            limit=INSIGHTS_TRACK_LIMIT,
            time_range="medium_term",
        )
        enriched_artist_items = enrich_top_artists(
            sp,
            top_artists_response.get("items", []),
        )

        top_artists = [
            serialize_top_artist(artist)
            for artist in enriched_artist_items
        ]
        top_tracks = [
            serialize_top_track(track)
            for track in top_tracks_response.get("items", [])
        ]
        top_genres = get_top_genres(enriched_artist_items)

        return success_response(
            {
                "profile_snapshot": {
                    "display_name": user.get("display_name"),
                    "followers": (user.get("followers") or {}).get("total", 0),
                    "country": user.get("country"),
                    "product": user.get("product"),
                },
                "top_artists": top_artists,
                "top_tracks": top_tracks,
                "top_genres": top_genres,
            }
        )
    except SpotifyException as error:
        return handle_spotify_exception(
            "Spotify API error while loading listening insights.",
            error,
        )
    except Exception as error:
        return error_response(
            "Unexpected error while loading listening insights.",
            500,
            details=get_exception_message(error),
        )


@app.route("/check_session")
def check_session():
    token_info = get_token()
    if not token_info:
        return success_response({"authenticated": False})

    return success_response(
        {
            "authenticated": True,
            "expires_at": token_info.get("expires_at"),
        }
    )


@app.route("/debug_token")
def debug_token():
    token_info = get_token()
    if not token_info:
        return error_response("No token in session.", 401)

    return success_response(
        {
            "scope": token_info.get("scope"),
            "token_type": token_info.get("token_type"),
            "expires_at": token_info.get("expires_at"),
            "has_access_token": "access_token" in token_info,
            "has_refresh_token": "refresh_token" in token_info,
        }
    )


@app.route("/whoami")
def whoami():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        return success_response(sp.current_user())
    except SpotifyException as error:
        return handle_spotify_exception("Failed to fetch current user.", error)
    except Exception as error:
        return error_response(
            "Unexpected error while fetching the current user.",
            500,
            details=get_exception_message(error),
        )


@app.route("/test_create")
def test_create():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    try:
        token_info = get_token()
        if not token_info:
            return error_response("Please login first at /login.", 401)

        response = requests.post(
            "https://api.spotify.com/v1/me/playlists",
            headers={
                "Authorization": f"Bearer {token_info['access_token']}",
                "Content-Type": "application/json",
            },
            json={
                "name": "Test Playlist From App",
                "public": False,
                "description": "Testing playlist creation",
            },
            timeout=10,
        )
        response.raise_for_status()
        playlist = response.json()
        return success_response(
            {
                "message": "Test playlist created successfully.",
                "playlist_name": playlist["name"],
                "playlist_url": playlist["external_urls"]["spotify"],
            }
        )
    except SpotifyException as error:
        return handle_spotify_exception(
            "Spotify API error while creating the test playlist.",
            error,
        )
    except Exception as error:
        return error_response(
            "Unexpected error while creating the test playlist.",
            500,
            details=get_exception_message(error),
        )


@app.route("/preview_playlist", methods=["POST"])
def preview_playlist():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    request_data = request.get_json(silent=True)
    if not request_data:
        return error_response("Request body must be valid JSON.", 400)

    playlist_request, validation_error = parse_playlist_request(request_data)
    if validation_error:
        return validation_error

    mood = playlist_request["mood"]
    genre = playlist_request["genre"]
    vibe = playlist_request["vibe"]
    count = playlist_request["count"]
    is_public = playlist_request["is_public"]
    seed_track_ids = playlist_request["seed_track_ids"]
    seed_artist_ids = playlist_request["seed_artist_ids"]
    audio_tuning = playlist_request["audio_tuning"]
    variation = parse_variation_index(request_data)
    exclude_track_ids = unique_preserve_order(
        [
            str(track_id).strip()
            for track_id in request_data.get("exclude_track_ids", [])
            if str(track_id).strip()
        ]
    )

    try:
        token_info = get_token()
        if not token_info:
            return error_response("Please login first at /login.", 401)
        access_token = token_info["access_token"]

        selected_tracks, warning_messages = select_playlist_tracks(
            sp,
            access_token,
            mood,
            genre,
            vibe,
            count,
            exclude_track_ids=exclude_track_ids,
            seed_track_ids=seed_track_ids,
            seed_artist_ids=seed_artist_ids,
            audio_tuning=audio_tuning,
        )

        if not selected_tracks:
            return error_response(
                "No tracks found for the selected mood and genre.",
                404,
            )

        return success_response(
            {
                "playlist_name": build_playlist_name(mood, genre, vibe, variation),
                "playlist_description": build_playlist_description(
                    mood,
                    genre,
                    vibe,
                    is_public,
                ),
                "tracks": [serialize_playlist_track(track) for track in selected_tracks],
                "tracks_found": len(selected_tracks),
                "variation": variation,
            },
            warning=" ".join(warning_messages) if warning_messages else None,
        )
    except SpotifyException as error:
        return handle_spotify_exception("Spotify API error.", error)
    except Exception as error:
        return error_response(
            "Unexpected error while previewing the playlist.",
            500,
            details=get_exception_message(error),
        )


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    sp, auth_error = get_spotify_client()
    if auth_error:
        return auth_error

    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    request_data = request.get_json(silent=True)
    if not request_data:
        return error_response("Request body must be valid JSON.", 400)

    playlist_request, validation_error = parse_playlist_request(request_data)
    if validation_error:
        return validation_error

    mood = playlist_request["mood"]
    genre = playlist_request["genre"]
    vibe = playlist_request["vibe"]
    count = playlist_request["count"]
    is_public = playlist_request["is_public"]
    seed_track_ids = playlist_request["seed_track_ids"]
    seed_artist_ids = playlist_request["seed_artist_ids"]
    audio_tuning = playlist_request["audio_tuning"]
    variation = parse_variation_index(request_data)
    requested_track_ids = unique_preserve_order(
        [
            str(track_id).strip()
            for track_id in request_data.get("track_ids", [])
            if str(track_id).strip()
        ]
    )[:count]
    requested_playlist_name = str(request_data.get("playlist_name", "")).strip()
    requested_description = str(request_data.get("playlist_description", "")).strip()

    try:
        user = sp.current_user()
        user_id = user["id"]
        token_info = get_token()
        if not token_info:
            return error_response("Please login first at /login.", 401)
        access_token = token_info["access_token"]
        warning_messages = []

        if requested_track_ids:
            selected_tracks = []
            track_uris = unique_preserve_order(
                [
                    f"spotify:track:{track_id}"
                    for track_id in requested_track_ids
                    if track_id
                ]
            )[:count]
        else:
            selected_tracks, warning_messages = select_playlist_tracks(
                sp,
                access_token,
                mood,
                genre,
                vibe,
                count,
                seed_track_ids=seed_track_ids,
                seed_artist_ids=seed_artist_ids,
                audio_tuning=audio_tuning,
            )

        if not requested_track_ids:
            if not selected_tracks:
                return error_response(
                    "No tracks found for the selected mood and genre.",
                    404,
                )

            track_uris = unique_preserve_order(
                [
                    track_uri
                    for track_uri in (get_track_uri(track) for track in selected_tracks)
                    if track_uri
                ]
            )[:count]

        if not track_uris:
            return error_response(
                "No valid tracks were available after filtering.",
                500,
            )

        playlist_name = requested_playlist_name or build_playlist_name(
            mood,
            genre,
            vibe,
            variation,
        )
        playlist_description = requested_description or build_playlist_description(
            mood,
            genre,
            vibe,
            is_public,
        )
        playlist = create_playlist(
            access_token,
            playlist_name,
            playlist_description,
            is_public,
        )
        sp.playlist_add_items(playlist_id=playlist["id"], items=track_uris)

        if len(track_uris) < count:
            warning_messages.append(
                f"Only {len(track_uris)} matching tracks were found for the selected filters."
            )

        persistence_warning = persist_playlist_history(
            {
                "user_id": user_id,
                "mood": mood,
                "genre": genre,
                "vibe": vibe,
                "count": len(track_uris),
                "public": is_public,
                "seed_track_ids": seed_track_ids,
                "seed_artist_ids": seed_artist_ids,
                "audio_tuning": audio_tuning,
                "playlist_name": playlist["name"],
                "playlist_url": playlist["external_urls"]["spotify"],
            }
        )
        if persistence_warning:
            warning_messages.append(persistence_warning)

        return success_response(
            {
                "message": "Playlist created successfully.",
                "playlist_name": playlist["name"],
                "playlist_url": playlist["external_urls"]["spotify"],
                "tracks_added": len(track_uris),
            },
            warning=" ".join(warning_messages) if warning_messages else None,
        )
    except SpotifyException as error:
        return handle_spotify_exception("Spotify API error.", error)
    except Exception as error:
        return error_response(
            "Unexpected error while generating the playlist.",
            500,
            details=get_exception_message(error),
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
