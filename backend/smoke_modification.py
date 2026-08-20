"""Real-model smoke test: add a clickable button through Modification Agent."""

import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.project import Project
from app.services.project import project_workspace, write_project_file
from app.services.seed import ensure_admin, seed_templates

SOURCE = """<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>Demo Page</title></head>
<body><main><h1>Demo Page</h1><p>Original content</p></main></body></html>
"""


def main() -> None:
    with TestClient(app) as client:
        with SessionLocal() as db:
            ensure_admin(db)
            seed_templates(db)
        login = client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        ).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        project_response = client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Modification Smoke", "template": "blank", "tech_stack": "html"},
        )
        assert project_response.status_code == 201, project_response.text
        project = project_response.json()
        with SessionLocal() as db:
            write_project_file(db, project["id"], "index.html", SOURCE)
            db.commit()

        response = client.post(
            f"/api/projects/{project['id']}/modifications",
            headers=headers,
            json={
                "instruction": "在页面中新增一个“显示提示”按钮，点击后显示“已收到你的操作”提示。",
                "element_snapshot": {"tag": "h1", "text": "Demo Page"},
                "related_files": ["index.html"],
            },
        )
        assert response.status_code == 201, response.text
        modification_id = response.json()["id"]
        deadline = time.time() + 420
        current = None
        while time.time() < deadline:
            current = client.get(
                f"/api/modifications/{modification_id}", headers=headers
            ).json()
            if current["status"] not in {"pending", "running"}:
                break
            time.sleep(1)
        assert current is not None and current["status"] == "succeeded", current
        content = (project_workspace(project["id"]) / "index.html").read_text(encoding="utf-8")
        assert "显示提示" in content
        assert "已收到你的操作" in content
        assert "onclick" in content.lower() or "addEventListener" in content
        print("status:", current["status"])
        print("summary:", current["diff_json"])


if __name__ == "__main__":
    main()
