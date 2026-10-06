"""E2E tests: follow/unfollow, writer subscriber-count metric, post error mapping."""
from __future__ import annotations

import uuid

from tests.e2e.test_reader_experience import (
    _auth,
    _login,
    _publish,
    _register,
    _user_id,
)


class TestFollow:
    def test_follow_unfollow_roundtrip(self, client):
        _register(client, "follow-w@test.com")
        wt = _login(client, "follow-w@test.com")["access_token"]
        _publish(client, wt, "F", "PRE", "FULL")  # grants WRITER
        writer_id = _user_id(wt)

        _register(client, "follower@test.com")
        rt = _login(client, "follower@test.com")["access_token"]

        # Follow
        resp = client.post(f"/api/v1/writers/{writer_id}/follow", headers=_auth(client, rt))
        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json() == {"following": True}

        # Detail reflects is_following for the authenticated reader
        resp = client.get(f"/api/v1/writers/{writer_id}", headers=_auth(client, rt))
        assert resp.get_json()["is_following"] is True
        resp = client.get(f"/api/v1/writers/{writer_id}")
        assert resp.get_json()["is_following"] is False  # anonymous: no reader

        # Unfollow
        resp = client.delete(f"/api/v1/writers/{writer_id}/follow", headers=_auth(client, rt))
        assert resp.status_code == 200
        assert resp.get_json() == {"following": False}
        resp = client.get(f"/api/v1/writers/{writer_id}", headers=_auth(client, rt))
        assert resp.get_json()["is_following"] is False

    def test_follow_requires_auth_and_existing_writer(self, client):
        missing = uuid.uuid4()
        resp = client.post(f"/api/v1/writers/{missing}/follow")
        assert resp.status_code == 401

        _register(client, "authonly@test.com")
        rt = _login(client, "authonly@test.com")["access_token"]
        resp = client.post(f"/api/v1/writers/{missing}/follow", headers=_auth(client, rt))
        assert resp.status_code == 404

    def test_cannot_follow_self(self, client):
        _register(client, "selffollow@test.com")
        wt = _login(client, "selffollow@test.com")["access_token"]
        _publish(client, wt, "S", "PRE", "FULL")
        resp = client.post(
            f"/api/v1/writers/{_user_id(wt)}/follow", headers=_auth(client, wt)
        )
        assert resp.status_code == 400


class TestWriterMetrics:
    def test_writer_posts_includes_subscriber_count(self, client):
        _register(client, "metrics-w@test.com")
        wt = _login(client, "metrics-w@test.com")["access_token"]
        writer_id = _user_id(wt)
        _publish(client, wt, "M", "PRE", "FULL")

        resp = client.get("/api/v1/posts/writer", headers=_auth(client, wt))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["subscriber_count"] == 0  # no allocation yet

        # A reader subscribes + allocates this writer -> count is 1
        _register(client, "metrics-r@test.com")
        rt = _login(client, "metrics-r@test.com")["access_token"]
        sub_resp = client.post(
            "/api/v1/subscriptions/subscribe",
            json={"payment_method_id": "pm_mock_default"},
            headers=_auth(client, rt),
        )
        assert sub_resp.status_code == 201, sub_resp.get_json()
        resp = client.post(
            "/api/v1/subscriptions/allocations/assign",
            json={"writer_id": writer_id},
            headers=_auth(client, rt),
        )
        assert resp.status_code == 200, resp.get_json()

        resp = client.get("/api/v1/posts/writer", headers=_auth(client, wt))
        assert resp.get_json()["subscriber_count"] == 1


class TestPostErrorMapping:
    def test_publish_missing_post_is_404(self, client):
        _register(client, "map404@test.com")
        wt = _login(client, "map404@test.com")["access_token"]
        _publish(client, wt, "Map", "PRE", "FULL")  # grants WRITER
        missing = uuid.uuid4()
        resp = client.post(f"/api/v1/posts/{missing}/publish", headers=_auth(client, wt))
        assert resp.status_code == 404
        assert resp.get_json()["status"] == 404

    def test_foreign_post_operations_are_403(self, client):
        _register(client, "owner@test.com")
        own = _login(client, "owner@test.com")["access_token"]
        post_id = client.post(
            "/api/v1/posts",
            json={"title": "Owned", "preview_content": "PRE", "subscriber_content": "FULL"},
            headers=_auth(client, own),
        ).get_json()["id"]

        _register(client, "intruder@test.com")
        other = _login(client, "intruder@test.com")["access_token"]
        # Grants WRITER with own post so role check passes; foreign post is 403
        _publish(client, other, "Other", "PRE", "FULL")

        resp = client.post(f"/api/v1/posts/{post_id}/publish", headers=_auth(client, other))
        assert resp.status_code == 403
        resp = client.patch(
            f"/api/v1/posts/{post_id}", json={"title": "Hacked"}, headers=_auth(client, other)
        )
        assert resp.status_code == 403
