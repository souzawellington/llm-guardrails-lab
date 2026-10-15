"""Import the app and hit the health and chat-page routes. No API key required."""

from __future__ import annotations


def main() -> int:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    health = client.get("/health")
    if health.status_code != 200 or health.json().get("status") != "ok":
        print("health check failed")
        return 1
    page = client.get("/ui")
    if page.status_code != 200 or "Send" not in page.text:
        print("chat page check failed")
        return 1
    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
