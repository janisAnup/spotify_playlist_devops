from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")

db = client.spotify_db
playlists_collection = db.playlists