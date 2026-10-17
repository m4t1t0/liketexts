"""E2E tests: health probes (/health liveness, /health/ready readiness)."""
from __future__ import annotations


class TestHealth:
    def test_liveness(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}

    def test_readiness_checks_database_redis_and_migrations(self, client):
        resp = client.get("/health/ready")
        body = resp.get_json()
        # In the test stack (db + redis up, migrations applied) the app must
        # report ready; every check carries an explicit ok flag either way.
        assert set(body["checks"].keys()) == {"database", "redis", "migrations"}
        assert all(
            isinstance(check["ok"], bool) for check in body["checks"].values()
        )
        assert resp.status_code == 200, body
        assert body["status"] == "ready"
