from flask import Flask, request, jsonify, redirect, session
from pymongo import MongoClient
from spotify_auth import sp_oauth
import spotipy
from spotipy.exceptions import SpotifyException
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

client = MongoClient("mongodb://mongodb:27017/")
db = client["spotify_playlist_db"]
playlists_collection = db["playlists"]


@app.route("/")
def home():
    return jsonify({"message": "Spotify Playlist Generator API is running"})


@app.route("/health")
def health():
    try:
        playlists_collection.insert_one({"status": "API working"})
        return jsonify({"status": "API running and DB connected"})
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500


@app.route("/login")
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return jsonify({"error": "No code received from Spotify"}), 400

    try:
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        session["token_info"] = token_info

        return jsonify({
            "message": "Login successful",
            "note": "Token stored in session",
            "scope": token_info.get("scope")
        })
    except Exception as e:
        return jsonify({
            "error": "Spotify auth failed",
            "details": str(e)
        }), 500


@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.route("/check_session")
def check_session():
    return jsonify(dict(session))


@app.route("/debug_token")
def debug_token():
    token_info = session.get("token_info")
    if not token_info:
        return jsonify({"error": "No token in session"}), 401

    return jsonify({
        "scope": token_info.get("scope"),
        "token_type": token_info.get("token_type"),
        "expires_at": token_info.get("expires_at"),
        "has_access_token": "access_token" in token_info,
        "has_refresh_token": "refresh_token" in token_info
    })


def get_token():
    token_info = session.get("token_info")

    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        refreshed_token = sp_oauth.refresh_access_token(token_info["refresh_token"])

        if "refresh_token" not in refreshed_token:
            refreshed_token["refresh_token"] = token_info["refresh_token"]

        session["token_info"] = refreshed_token
        token_info = refreshed_token

    return token_info


def get_spotify_client():
    token_info = get_token()

    if not token_info:
        return None, jsonify({
            "error": {
                "status": 401,
                "message": "No token provided. Please login first at /login"
            }
        }), 401

    sp = spotipy.Spotify(auth=token_info["access_token"])
    return sp, None, None


@app.route("/whoami")
def whoami():
    sp, error_response, status_code = get_spotify_client()
    if error_response:
        return error_response, status_code

    try:
        me = sp.current_user()
        return jsonify(me)
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch current user",
            "details": str(e)
        }), 500


@app.route("/test_create")
def test_create():
    sp, error_response, status_code = get_spotify_client()
    if error_response:
        return error_response, status_code

    try:
        playlist = sp._post(
            "me/playlists",
            payload={
                "name": "Test Playlist From App",
                "public": False,
                "description": "Testing playlist creation"
            }
        )

        return jsonify({
            "message": "Test playlist created successfully",
            "playlist_name": playlist["name"],
            "playlist_url": playlist["external_urls"]["spotify"]
        })

    except SpotifyException as e:
        return jsonify({
            "error": "Spotify API error while creating test playlist",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Unexpected error while creating test playlist",
            "details": str(e)
        }), 500


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    sp, error_response, status_code = get_spotify_client()
    if error_response:
        return error_response, status_code

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    mood = data.get("mood", "").strip()
    genre = data.get("genre", "").strip()

    if not mood or not genre:
        return jsonify({"error": "Both mood and genre are required"}), 400

    try:
        user = sp.current_user()
        user_id = user["id"]

        query = f"{mood} {genre}"
        results = sp.search(q=query, type="track", limit=10)
        tracks = results["tracks"]["items"]

        if not tracks:
            return jsonify({"error": "No tracks found"}), 404

        playlist = sp._post(
            "me/playlists",
            payload={
                "name": f"{mood.title()} {genre.title()} Playlist",
                "public": False,
                "description": "Generated by Spotify Playlist Generator"
            }
        )

        track_uris = [track["uri"] for track in tracks]

        sp.playlist_add_items(
            playlist_id=playlist["id"],
            items=track_uris
        )

        playlists_collection.insert_one({
            "user_id": user_id,
            "mood": mood,
            "genre": genre,
            "playlist_name": playlist["name"],
            "playlist_url": playlist["external_urls"]["spotify"]
        })

        return jsonify({
            "message": "Playlist created successfully",
            "playlist_name": playlist["name"],
            "playlist_url": playlist["external_urls"]["spotify"]
        })

    except SpotifyException as e:
        return jsonify({
            "error": "Spotify API error",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Unexpected error",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)