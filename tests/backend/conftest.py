import os

import pytest

os.environ.setdefault("SPOTIFY_CLIENT_ID", "test-client-id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("MONGO_URI", "mongodb://127.0.0.1:27017/")
os.environ.setdefault("FRONTEND_DASHBOARD_URL", "http://127.0.0.1:5173/")

import run


@pytest.fixture
def client():
    run.app.config.update(TESTING=True)
    with run.app.test_client() as test_client:
        yield test_client

