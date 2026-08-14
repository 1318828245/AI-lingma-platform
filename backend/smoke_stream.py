"""真实 LLM 流式冒烟：验证 SSE 逐字思考 + 工具调用 started/completed。

用法：$env:AI_LINGMA_BUILD_MODE='mock'; python smoke_stream.py
"""

import json
import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.services.seed import ensure_admin, seed_templates


def main() -> None:
    with TestClient(app) as client:
        with SessionLocal() as db:
            ensure_admin(db)
            seed_templates(db)
        login = client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        ).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        project = client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Stream Smoke", "template": "blank", "tech_stack": "html"},
        ).json()
        gen = client.post(
            f"/api/projects/{project['id']}/generations",
            headers=headers,
            json={"requirement": "Build a simple landing page with title and button"},
        ).json()
        gen_id = gen["id"]

        events = []
        with client.stream(
            "GET", f"/api/generations/{gen_id}/events?token={login['access_token']}"
        ) as stream:
            for line in stream.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        counts: dict[str, int] = {}
        reasoning_chars = 0
        for event in events:
            counts[event["type"]] = counts.get(event["type"], 0) + 1
            if event["type"] == "reasoning_delta":
                reasoning_chars += len(event.get("text") or "")
        print("event_counts:", counts, flush=True)
        print("reasoning_chars:", reasoning_chars, flush=True)

        deadline = time.time() + 30
        current = None
        while time.time() < deadline:
            current = client.get(
                f"/api/generations/{gen_id}", headers=headers
            ).json()
            if current["status"] not in ("pending", "running"):
                break
            time.sleep(0.5)
        print("status:", current["status"], "| error:", current["error"], flush=True)


if __name__ == "__main__":
    main()
