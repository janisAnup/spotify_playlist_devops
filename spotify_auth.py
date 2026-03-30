import os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_SCOPE = (
    "user-read-private user-read-email playlist-modify-public "
    "playlist-modify-private playlist-read-private"
)

REQUIRED_SPOTIFY_ENV_VARS = (
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URI",
)


def validate_spotify_config():
    missing_vars = [
        env_name for env_name in REQUIRED_SPOTIFY_ENV_VARS if not os.getenv(env_name)
    ]
    if missing_vars:
        missing_list = ", ".join(missing_vars)
        raise RuntimeError(
            f"Missing required Spotify configuration: {missing_list}"
        )


def create_spotify_oauth():
    validate_spotify_config()
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SPOTIFY_SCOPE,
        show_dialog=True,
        cache_path=None,
    )


sp_oauth = create_spotify_oauth()
