"""E2E tests: profile editing (PATCH /me) and avatar upload (POST /avatar)."""

from __future__ import annotations

import io


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_login(client, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 201, resp.get_json()
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    ).get_json()["access_token"]


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100


class TestUpdateProfile:
    def test_patch_me_updates_names(self, client):
        token = _register_login(client, "profile-a@test.com")

        resp = client.patch(
            "/api/v1/auth/me",
            json={"first_name": "Ada", "last_name": "Lovelace"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["first_name"] == "Ada"
        assert body["last_name"] == "Lovelace"
        assert body["display_name"] == "Ada Lovelace"

        # Partial update leaves other fields untouched
        resp = client.patch(
            "/api/v1/auth/me", json={"first_name": "Grace"}, headers=_auth(token)
        )
        assert resp.get_json()["first_name"] == "Grace"
        assert resp.get_json()["last_name"] == "Lovelace"

        # Empty string clears a field
        resp = client.patch(
            "/api/v1/auth/me", json={"last_name": ""}, headers=_auth(token)
        )
        assert resp.get_json()["last_name"] is None
        assert resp.get_json()["display_name"] == "Grace"

    def test_patch_me_rejects_empty_and_bad_input(self, client):
        token = _register_login(client, "profile-b@test.com")

        resp = client.patch("/api/v1/auth/me", json={}, headers=_auth(token))
        assert resp.status_code == 400

        resp = client.patch(
            "/api/v1/auth/me",
            json={"first_name": "x" * 121},
            headers=_auth(token),
        )
        assert resp.status_code == 400

        resp = client.patch("/api/v1/auth/me", json={"first_name": "Ada"})
        assert resp.status_code == 401


class TestAvatarUpload:
    def test_upload_sets_avatar_and_serves_file(self, client):
        token = _register_login(client, "avatar-a@test.com")

        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(PNG_BYTES), "me.png")},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.get_json()
        avatar_url = resp.get_json()["avatar_url"]
        assert avatar_url.startswith("/uploads/avatars/")
        assert avatar_url.endswith(".png")

        # The stored file is served back with the same bytes
        resp = client.get(avatar_url)
        assert resp.status_code == 200
        assert resp.data == PNG_BYTES

        # A second upload replaces the first (old file removed)
        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(JPEG_BYTES), "me.jpg")},
            headers=_auth(token),
        )
        new_url = resp.get_json()["avatar_url"]
        assert new_url != avatar_url
        assert client.get(avatar_url).status_code == 404
        assert client.get(new_url).status_code == 200

    def test_upload_rejects_bad_files(self, client):
        token = _register_login(client, "avatar-b@test.com")

        # Missing file
        resp = client.post("/api/v1/auth/avatar", data={}, headers=_auth(token))
        assert resp.status_code == 400

        # Non-image content
        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(b"hello world"), "me.png")},
            headers=_auth(token),
        )
        assert resp.status_code == 400

        # Extension/content mismatch
        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(PNG_BYTES), "me.jpg")},
            headers=_auth(token),
        )
        assert resp.status_code == 400

        # Disallowed extension
        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(b"GIF89a" + b"\x00" * 20), "me.bmp")},
            headers=_auth(token),
        )
        assert resp.status_code == 400

        # Unauthenticated
        resp = client.post(
            "/api/v1/auth/avatar",
            data={"file": (io.BytesIO(PNG_BYTES), "me.png")},
        )
        assert resp.status_code == 401
