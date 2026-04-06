import run


class FakeSpotifyClient:
    def __init__(self):
        self.playlist_add_calls = []

    def current_user(self):
        return {"id": "user-1", "country": "IN"}

    def playlist_add_items(self, playlist_id, items):
        self.playlist_add_calls.append({"playlist_id": playlist_id, "items": items})


def test_check_session_guest(client, monkeypatch):
    monkeypatch.setattr(run, "get_token", lambda: None)
    response = client.get("/check_session")
    data = response.get_json()

    assert response.status_code == 200
    assert data["authenticated"] is False


def test_check_session_authenticated(client, monkeypatch):
    monkeypatch.setattr(
        run,
        "get_token",
        lambda: {"access_token": "token", "expires_at": 9999999999},
    )
    response = client.get("/check_session")
    data = response.get_json()

    assert response.status_code == 200
    assert data["authenticated"] is True


def test_generate_playlist_uses_requested_track_ids(client, monkeypatch):
    fake_sp = FakeSpotifyClient()

    monkeypatch.setattr(run, "get_spotify_client", lambda: (fake_sp, None))
    monkeypatch.setattr(run, "get_token", lambda: {"access_token": "token"})
    monkeypatch.setattr(
        run,
        "create_playlist",
        lambda *_args, **_kwargs: {
            "id": "playlist-1",
            "name": "My Playlist",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist-1"},
        },
    )
    monkeypatch.setattr(run, "persist_playlist_history", lambda _payload: None)

    payload = {
        "mood": "chill",
        "genre": "indie",
        "vibe": "dreamy",
        "count": 2,
        "visibility": "false",
        "track_ids": ["track-a", "track-b"],
        "playlist_name": "My Playlist",
        "playlist_description": "A test playlist",
    }
    response = client.post("/generate_playlist", json=payload)
    data = response.get_json()

    assert response.status_code == 200
    assert data["tracks_added"] == 2
    assert fake_sp.playlist_add_calls[0]["playlist_id"] == "playlist-1"
    assert fake_sp.playlist_add_calls[0]["items"] == [
        "spotify:track:track-a",
        "spotify:track:track-b",
    ]


def test_generate_playlist_requires_json_body(client, monkeypatch):
    monkeypatch.setattr(run, "get_spotify_client", lambda: (FakeSpotifyClient(), None))
    response = client.post("/generate_playlist", data="not-json", content_type="text/plain")
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Request body must be valid JSON."

