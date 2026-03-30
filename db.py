import os

from pymongo import MongoClient

client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
)

db = client.spotify_db
playlists_collection = db.playlists
