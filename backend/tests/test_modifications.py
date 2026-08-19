import time

from app.core.database import SessionLocal
from app.services.project import write_project_file


def test_modification_text_edit_diff_and_version(client, admin_headers):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "点选修改测试", "template": "blank", "tech_stack": "html"},
    ).json()
    project_id = project["id"]
    with SessionLocal() as db:
        write_project_file(db, project_id, "index.html", "<main><h1 id='title'>旧标题</h1></main>")
        db.commit()

    created = client.post(
        f"/api/projects/{project_id}/modifications",
        headers=admin_headers,
        json={
            "selector": {"css": "#title"},
            "element_snapshot": {
                "tag": "h1",
                "id": "title",
                "text": "旧标题",
                "selector": "#title",
            },
            "instruction": "把标题改成新标题",
        },
    )
    assert created.status_code == 201, created.text
    modification_id = created.json()["id"]

    status = None
    for _ in range(100):
        status = client.get(
            f"/api/modifications/{modification_id}", headers=admin_headers
        ).json()
        if status["status"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.02)
    assert status["status"] == "succeeded", status
    assert status["related_files_json"] == ["index.html"]
    assert "旧标题" in status["diff_json"]["files"][0]["diff"]

    with SessionLocal() as db:
        from app.services.project import project_workspace

        workspace = project_workspace(project_id)
        assert "新标题" in (workspace / "index.html").read_text(encoding="utf-8")
