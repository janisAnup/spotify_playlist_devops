

from flask import Flask, request, jsonify
from db import playlists_collection
import random

app = Flask(__name__)


@app.route("/")
def home():
    return {"message": "Spotify Playlist Generator API"}


@app.route("/health")
def health():
    playlists_collection.insert_one({"status": "API working"})
    return {"status": "API running and DB connected"}


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():

    data = request.json

    mood = data.get("mood")
    genre = data.get("genre")
    activity = data.get("activity")
    energy = data.get("energy")
    max_songs = data.get("max_songs", 10)
    popularity = data.get("popularity")
    remove_explicit = data.get("remove_explicit", False)
    visibility = data.get("visibility", "private")

    # Mock song database (temporary)
    songs_db = [
        {"title": "Blinding Lights", "artist": "The Weeknd", "explicit": False},
        {"title": "Levitating", "artist": "Dua Lipa", "explicit": False},
        {"title": "HUMBLE.", "artist": "Kendrick Lamar", "explicit": True},
        {"title": "Stay", "artist": "Justin Bieber", "explicit": False},
        {"title": "Industry Baby", "artist": "Lil Nas X", "explicit": True},
        {"title": "Peaches", "artist": "Justin Bieber", "explicit": False},
        {"title": "Save Your Tears", "artist": "The Weeknd", "explicit": False},
    ]

    # Filter explicit songs if requested
    if remove_explicit:
        songs_db = [song for song in songs_db if not song["explicit"]]

    # Randomly select songs
    playlist_songs = random.sample(songs_db, min(max_songs, len(songs_db)))

    playlist_name = f"{mood.capitalize()} {genre.capitalize()} {activity.capitalize()} Mix"

    playlist = {
        "playlist_name": playlist_name,
        "mood": mood,
        "genre": genre,
        "activity": activity,
        "energy": energy,
        "popularity": popularity,
        "visibility": visibility,
        "songs": playlist_songs
    }

    # Save to MongoDB
    result = playlists_collection.insert_one(playlist)

# Convert ObjectId to string
    playlist["_id"] = str(result.inserted_id)

    return jsonify({
    "message": "Playlist generated successfully",
    "playlist": playlist
})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)