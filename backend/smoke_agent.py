"""真实 LLM Agent 冒烟：DeepSeek 自主生成一个落地页。

用法：$env:AI_LINGMA_BUILD_MODE='mock'; python smoke_agent.py
"""

import time

from fastapi.testclient import TestClient

from app.core.config import get_settings
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
            json={"name": "真实Agent生成", "template": "blank", "tech_stack": "html"},
        ).json()
        gen = client.post(
            f"/api/projects/{project['id']}/generations",
            headers=headers,
            json={"requirement": "做一个简洁的落地页：深色背景，包含大标题、简介和按钮"},
        ).json()
        print("generation:", gen["id"], flush=True)

        deadline = time.time() + 420
        current = None
        while time.time() < deadline:
            current = client.get(
                f"/api/generations/{gen['id']}", headers=headers
            ).json()
            if current["status"] not in ("pending", "running"):
                break
            time.sleep(1)
        print("status:", current["status"], flush=True)
        print("model:", current["llm_model"], flush=True)
        print("build_attempt:", current["build_attempt"], flush=True)
        print("error:", current["error"], flush=True)

        ws = get_settings().workspace_dir / str(project["id"])
        files = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_file())
        print("files:", files, flush=True)
        index = ws / "index.html"
        if index.exists():
            print(
                "index_head:",
                index.read_text(encoding="utf-8")[:200].replace("\n", " "),
                flush=True,
            )


if __name__ == "__main__":
    main()
