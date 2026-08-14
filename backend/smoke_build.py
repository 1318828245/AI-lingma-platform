"""真实构建冒烟：任务看板模板 → 生成 → npm install/build → 检查 dist。

用法：python smoke_build.py（需联网；仅开发验证用）
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
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = client.post(
            "/api/projects",
            headers=headers,
            json={
                "name": "真实构建看板",
                "template": "任务看板",
                "tech_stack": "vue3",
            },
        )
        print("create:", resp.status_code, resp.text[:200], flush=True)
        project = resp.json()
        gen_resp = client.post(
            f"/api/projects/{project['id']}/generations",
            headers=headers,
            json={"requirement": "生成一个任务看板，支持任务增删移"},
        )
        print("generation:", gen_resp.status_code, flush=True)
        gen_id = gen_resp.json()["id"]

        deadline = time.time() + 420
        current = None
        while time.time() < deadline:
            current = client.get(
                f"/api/generations/{gen_id}", headers=headers
            ).json()
            if current["status"] not in ("pending", "running"):
                break
            time.sleep(1)
        print("status:", current["status"], flush=True)
        print("build_attempt:", current["build_attempt"], flush=True)
        print("error:", current["error"], flush=True)

        ws = get_settings().workspace_dir / str(project["id"])
        dist = ws / "dist" / "index.html"
        print("dist_exists:", dist.exists(), flush=True)
        if dist.exists():
            print(
                "dist_head:",
                dist.read_text(encoding="utf-8")[:120].replace("\n", " "),
                flush=True,
            )


if __name__ == "__main__":
    main()
