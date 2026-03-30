import os

import requests
import spotipy
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from spotipy.exceptions import SpotifyException

from spotify_auth import sp_oauth

load_dotenv()

DEFAULT_FRONTEND_DASHBOARD_URL = "http://127.0.0.1:5500/frontend/dashboard.html"
DEFAULT_MONGO_URI = "mongodb://127.0.0.1:27017/"
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 5000
MAX_TRACK_COUNT = 20
SEARCH_LIMIT_PER_QUERY = 10
MAX_TRACK_CANDIDATES = 120
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

    if not mood or not genre:
        return None, error_response("Both mood and genre are required.", 400)

    try:
        requested_count = int(raw_count.split()[0])
    except (ValueError, TypeError, IndexError):
        return None, error_response("Count must be a number between 1 and 20.", 400)

    count = max(1, min(requested_count, MAX_TRACK_COUNT))
    is_public = raw_visibility in {"true", "public", "yes"}

    return {
        "mood": mood,
        "genre": genre,
        "vibe": vibe,
        "count": count,
        "is_public": is_public,
    }, None


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
        try:
            artist_response = sp.artists(artist_batch)
        except Exception:
            continue

        for artist in artist_response.get("artists", []):
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


def score_track(track, mood, genre, vibe, artist_genre_map):
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


def rank_and_select_tracks(tracks, mood, genre, vibe, count, artist_genre_map):
    scored_tracks = []
    seen_unique_tracks = set()

    for track in tracks:
        if not get_track_uri(track):
            continue

        unique_key = get_track_unique_key(track)
        if unique_key in seen_unique_tracks:
            continue
        seen_unique_tracks.add(unique_key)

        scored_tracks.append(
            {
                "score": score_track(track, mood, genre, vibe, artist_genre_map),
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

    def append_tracks(track_list, max_per_artist):
        diverse_tracks = enforce_artist_diversity(track_list, max_per_artist=max_per_artist)
        for track in diverse_tracks:
            track_id = track.get("id")
            if not track_id or track_id in selected_ids:
                continue

            selected_tracks.append(track)
            selected_ids.add(track_id)
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


def build_playlist_name(mood, genre, vibe):
    parts = [mood.title(), genre.title()]
    if vibe:
        parts.append(vibe.title())
    return " ".join(parts) + " Playlist"


def create_playlist(access_token, mood, genre, vibe, is_public):
    playlist_name = build_playlist_name(mood, genre, vibe)
    description = (
        "Generated by Spotify Playlist Generator | "
        f"mood: {mood}, genre: {genre}, vibe: {vibe or 'none'}"
    )
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
        playlists_collection.insert_one(payload)
        return None
    except PyMongoError:
        return "Playlist created on Spotify, but history could not be saved."


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

    try:
        user = sp.current_user()
        user_id = user["id"]
        token_info = get_token()
        if not token_info:
            return error_response("Please login first at /login.", 401)
        access_token = token_info["access_token"]

        search_queries = build_search_queries(mood, genre, vibe)
        candidate_tracks = collect_candidate_tracks(access_token, search_queries)

        if not candidate_tracks:
            fallback_queries = GENERIC_FALLBACK_QUERIES + [f"{genre} songs"]
            candidate_tracks = collect_candidate_tracks(access_token, fallback_queries)

        if not candidate_tracks:
            return error_response(
                "No tracks found for the selected mood and genre.",
                404,
            )

        artist_genre_map = get_artist_genre_map(sp, candidate_tracks)
        selected_tracks = rank_and_select_tracks(
            candidate_tracks,
            mood,
            genre,
            vibe,
            count,
            artist_genre_map,
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

        playlist = create_playlist(access_token, mood, genre, vibe, is_public)
        sp.playlist_add_items(playlist_id=playlist["id"], items=track_uris)

        warning_messages = []

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
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
