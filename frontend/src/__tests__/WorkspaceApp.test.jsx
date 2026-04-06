import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkspaceApp from "../WorkspaceApp";
import { apiRequest } from "../lib/api";

vi.mock("../lib/api", () => ({
  API_BASE: "http://127.0.0.1:5000",
  apiRequest: vi.fn(),
  getMessage: (payload, fallback) => {
    if (!payload) {
      return fallback;
    }
    if (typeof payload === "string") {
      return payload;
    }
    return payload.error || payload.details || fallback;
  },
  isUnauthorizedResponse: () => false,
  isAuthScopeIssue: () => false
}));

function ok(payload) {
  return {
    response: {
      ok: true,
      status: 200,
      redirected: false,
      url: "http://127.0.0.1:5000/mock",
      headers: { get: () => "application/json" }
    },
    payload
  };
}

describe("WorkspaceApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("renders guest landing when session is not authenticated", async () => {
    apiRequest.mockImplementation(async (path) => {
      if (path === "/check_session") {
        return ok({ authenticated: false });
      }
      return ok({});
    });

    render(<WorkspaceApp />);
    expect(await screen.findByRole("button", { name: /connect spotify/i })).toBeInTheDocument();
  });

  it("redirects to history tab after successful playlist creation", async () => {
    apiRequest.mockImplementation(async (path, options = {}) => {
      if (path === "/check_session") {
        return ok({ authenticated: true });
      }
      if (path === "/whoami") {
        return ok({ id: "user-1", display_name: "Tester" });
      }
      if (path === "/playlist_history") {
        return ok({
          playlists: [
            {
              playlist_name: "Final Mix",
              playlist_url: "https://open.spotify.com/playlist/test",
              mood: "chill",
              genre: "indie",
              vibe: "dreamy",
              count: 1,
              created_at: "2026-04-06T00:00:00Z"
            }
          ]
        });
      }
      if (path === "/insights") {
        return ok({ profile_snapshot: null, top_artists: [], top_tracks: [], top_genres: [] });
      }
      if (path === "/preview_playlist") {
        return ok({
          playlist_name: "Draft Mix",
          playlist_description: "Draft description",
          tracks: [{ id: "track-1", name: "Track 1", artists: ["Artist"] }],
          tracks_found: 1,
          variation: 0
        });
      }
      if (path === "/generate_playlist") {
        expect(options.method).toBe("POST");
        return ok({
          playlist_name: "Final Mix",
          playlist_url: "https://open.spotify.com/playlist/test",
          tracks_added: 1
        });
      }
      return ok({});
    });

    render(<WorkspaceApp />);
    await screen.findByRole("button", { name: /create in spotify/i });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create in spotify/i })).toBeEnabled();
    }, { timeout: 4000 });

    fireEvent.click(screen.getByRole("button", { name: /create in spotify/i }));

    expect(await screen.findByRole("heading", { name: /your generated playlists/i })).toBeInTheDocument();
  });
});
