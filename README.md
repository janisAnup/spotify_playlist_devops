# Spotify Playlist Generator

A full-stack web application that helps Spotify users generate playlists around mood, genre, and vibe instead of manually collecting tracks one by one.

The project combines a React frontend, a Flask backend, Spotify OAuth, Spotify Web API access, and MongoDB-backed history so users can:

- connect their Spotify account
- explore a guided dashboard experience
- generate playlists from mood-based inputs
- preview and refine tracks before saving
- view profile details and listening insights
- keep a history of generated playlists

## Overview

This application is built around a mood-first playlist workflow.

After a user signs in with Spotify, the frontend loads a dashboard with five core modules:

- `Welcome`
- `Profile`
- `Create`
- `Insights`
- `History`

The backend handles authentication, request validation, Spotify API communication, track selection logic, playlist creation, and MongoDB persistence.

## Core Features

### Spotify Authentication

The app uses Spotify OAuth to authenticate the user and request the permissions needed to:

- read user profile information
- read top artists and top tracks
- create public playlists
- create private playlists
- read playlists

Required environment variables are validated in [spotify_auth.py](/d:/Spotify_Project/spotify_playlist_devops/spotify_auth.py).

### Mood-Based Playlist Creation

Users can create playlists by selecting:

- mood
- genre
- vibe
- track count
- playlist visibility
- optional audio tuning values

The current frontend options include:

- Moods: `happy`, `chill`, `energetic`, `focus`, `romantic`, `sad`
- Genres: `pop`, `indie`, `rock`, `hip hop`, `k-pop`, `bollywood`, `lofi`
- Vibes: `soft`, `dreamy`, `party`, `intense`

These options are defined in [frontend/src/constants.js](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/constants.js).

### Playlist Preview Before Creation

The frontend does not immediately create a playlist when the user changes inputs. Instead, it requests a preview from the backend so the user can inspect tracks first.

The preview flow supports:

- refreshing the preview
- regenerating the mix
- removing tracks
- reordering tracks before final save

### Intelligent Track Selection

The backend does more than a simple keyword search. It uses multiple signals to choose tracks:

- search queries built from mood, genre, and vibe
- audio feature matching
- strict and relaxed genre filtering
- artist diversity rules
- duplicate reduction
- popularity-based ranking

This logic lives mainly in [run.py](/d:/Spotify_Project/spotify_playlist_devops/run.py).

### Profile and Listening Insights

The dashboard includes:

- Spotify profile details
- top artists
- top tracks
- top genres derived from artist metadata

These are exposed by backend routes such as `/whoami` and `/insights`.

### Playlist History in MongoDB

Generated playlist metadata is stored in MongoDB so the app can show a history view later.

Stored fields include:

- user id
- mood
- genre
- vibe
- track count
- visibility
- playlist name
- playlist URL
- creation timestamp

The project also includes a history sync step that can backfill app-generated playlists from Spotify into MongoDB when the history route is loaded.

## Project Architecture

### Frontend

The frontend is a React application powered by Vite. It is responsible for:

- rendering the landing page and dashboard
- managing active tab state
- handling authentication redirects
- collecting playlist input values
- requesting previews and final playlist creation
- displaying results, profile data, insights, and history

Main frontend files:

- [frontend/src/WorkspaceApp.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/WorkspaceApp.jsx)
- [frontend/src/constants.js](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/constants.js)
- [frontend/src/lib/api.js](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/lib/api.js)

Module components:

- [frontend/src/components/WelcomeModule.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/components/WelcomeModule.jsx)
- [frontend/src/components/ProfileModule.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/components/ProfileModule.jsx)
- [frontend/src/components/CreateModule.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/components/CreateModule.jsx)
- [frontend/src/components/InsightsModule.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/components/InsightsModule.jsx)
- [frontend/src/components/HistoryModule.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/components/HistoryModule.jsx)

### Backend

The backend is a Flask application that:

- manages Spotify OAuth sessions
- validates incoming playlist requests
- fetches Spotify user data
- searches and ranks tracks
- creates playlists in Spotify
- stores history in MongoDB
- exposes API endpoints for the frontend

Main backend file:

- [run.py](/d:/Spotify_Project/spotify_playlist_devops/run.py)

Spotify OAuth configuration:

- [spotify_auth.py](/d:/Spotify_Project/spotify_playlist_devops/spotify_auth.py)

### Database

MongoDB is used primarily for:

- playlist history persistence
- preset storage

Collections used:

- `playlists`
- `presets`

## Technology Stack

### Frontend

- React
- React DOM
- Vite
- CSS
- Fetch API

### Backend

- Python
- Flask
- Flask-CORS
- Spotipy
- Requests
- PyMongo
- python-dotenv

### Database

- MongoDB

### Testing

- Pytest
- Vitest
- Testing Library
- Selenium

### Containerization

- Docker
- Docker Compose

## Folder Structure

```text
spotify_playlist_devops/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── __tests__/
│   │   ├── lib/
│   │   ├── App.jsx
│   │   ├── WorkspaceApp.jsx
│   │   ├── constants.js
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── backend/
│   └── selenium/
├── run.py
├── spotify_auth.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Environment Variables

Create a `.env` file in the project root with:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
FLASK_SECRET_KEY=your_secret_key
```

Optional variables:

```env
MONGO_URI=mongodb://127.0.0.1:27017/
FRONTEND_DASHBOARD_URL=http://127.0.0.1:5173/
PORT=5000
APP_HOST=0.0.0.0
```

## Running the Project Locally

### Backend

1. Create and activate a virtual environment.
2. Install Python dependencies.
3. Start the Flask backend.

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Default local URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:5000`
- MongoDB: `mongodb://127.0.0.1:27017`

## Running with Docker Compose

From the project root:

```powershell
docker compose up -d --build
```

This starts:

- MongoDB
- Flask API
- React frontend

## API Endpoints

The backend currently exposes these major routes:

- `GET /`
- `GET /health`
- `GET /login`
- `GET /callback`
- `GET /logout`
- `GET /check_session`
- `GET /whoami`
- `GET /insights`
- `GET /playlist_history`
- `POST /preview_playlist`
- `POST /generate_playlist`
- `GET /presets`
- `POST /presets`
- `DELETE /presets/<preset_id>`
- `GET /debug_token`
- `GET /test_create`

## How Playlist Generation Works

At a high level, the playlist generation flow is:

1. The user selects mood, genre, vibe, count, and visibility.
2. The frontend sends a preview request.
3. The backend builds search queries from the selected values.
4. Spotify search results are collected as candidate tracks.
5. Audio features and genre metadata are used to score tracks.
6. The best set of tracks is returned as a preview.
7. When the user confirms, the backend creates the playlist in Spotify.
8. Playlist metadata is stored in MongoDB.

## MongoDB History Behavior

MongoDB stores playlist history records for app-generated playlists.

There are two main ways records can appear:

- directly when `/generate_playlist` creates a playlist successfully
- by syncing app-generated Spotify playlists into MongoDB when `/playlist_history` is requested

This means MongoDB is used as the app history store rather than as a mirror of every playlist that exists in the user’s Spotify account.

## Testing

### Backend Tests

Backend tests are located in [tests/backend/test_api.py](/d:/Spotify_Project/spotify_playlist_devops/tests/backend/test_api.py).

Run them with:

```powershell
python -m pytest tests/backend -q
```

### Frontend Tests

Frontend tests are located in [frontend/src/__tests__/WorkspaceApp.test.jsx](/d:/Spotify_Project/spotify_playlist_devops/frontend/src/__tests__/WorkspaceApp.test.jsx).

Run them with:

```powershell
cd frontend
npm test
```

### Selenium Smoke Test

A browser-based smoke test also exists under:

- [tests/selenium/test_guest_landing_smoke.py](/d:/Spotify_Project/spotify_playlist_devops/tests/selenium/test_guest_landing_smoke.py)

## Current Limitations

- History sync depends on playlists being recognizable as app-generated playlists.
- The app stores playlist history metadata, not full Spotify library data.
- Spotify API permissions and token validity directly affect profile, insights, and playlist creation features.
- MongoDB history is limited to the app’s own playlist workflow rather than all Spotify playlists.

## Future Improvements

- richer playlist history synchronization
- playlist edit and delete support
- better preset management in the frontend
- more advanced recommendation controls
- deeper analytics and listening summaries
- deployment to a public hosting platform

## Screens / Modules

The interface is organized into these pages:

- `Landing Page` for authentication entry
- `Welcome` for workspace overview
- `Profile` for Spotify account details
- `Create` for playlist composition
- `Insights` for listening analytics
- `History` for previously generated playlists

## License

This repository currently does not define a license. Add a `LICENSE` file if you plan to share or open-source the project publicly.
