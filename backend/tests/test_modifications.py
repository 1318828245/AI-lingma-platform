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

    session_id = created.json()["session_id"]
    messages = client.get(f"/api/sessions/{session_id}/messages", headers=admin_headers).json()
    assert any(message["role"] == "user" and message["content"] == "把标题改成新标题" for message in messages)

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

    version_id = status["diff_json"]["version_id"]
    accepted = client.post(
        f"/api/projects/{project_id}/versions/{version_id}/accept",
        headers=admin_headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert client.get(f"/api/modifications/{modification_id}", headers=admin_headers).json()["diff_json"]["review_status"] == "accepted"

    undone = client.post(
        f"/api/projects/{project_id}/versions/{version_id}/undo",
        headers=admin_headers,
    )
    assert undone.status_code == 200, undone.text
    messages = client.get(f"/api/sessions/{session_id}/messages", headers=admin_headers).json()
    assert [message["msg_type"] for message in messages].count("modification_review") == 2
    with SessionLocal() as db:
        from app.services.project import project_workspace

        assert "旧标题" in (project_workspace(project_id) / "index.html").read_text(encoding="utf-8")


def test_direct_chat_modification_uses_instruction_target(client, admin_headers):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Direct edit", "template": "blank", "tech_stack": "html"},
    ).json()
    with SessionLocal() as db:
        write_project_file(db, project["id"], "index.html", "<h1>旧标题</h1>")
        db.commit()

    created = client.post(
        f"/api/projects/{project['id']}/modifications",
        headers=admin_headers,
        json={"instruction": "把旧标题改成新标题"},
    )
    assert created.status_code == 201, created.text
    modification_id = created.json()["id"]
    for _ in range(100):
        status = client.get(f"/api/modifications/{modification_id}", headers=admin_headers).json()
        if status["status"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.02)
    assert status["status"] == "succeeded", status


def test_active_modification_is_scoped_to_its_project(client, admin_headers):
    from app.models.modification import Modification
    from app.models.session import Session as ChatSession

    project = client.post(
        "/api/projects", headers=admin_headers,
        json={"name": "Active modification", "template": "blank", "tech_stack": "html"},
    ).json()
    with SessionLocal() as db:
        session = db.query(ChatSession).filter(ChatSession.project_id == project["id"]).one()
        modification = Modification(project_id=project["id"], session_id=session.id, instruction="resume", status="running")
        db.add(modification)
        db.commit()
        modification_id = modification.id

    response = client.get(f"/api/projects/{project['id']}/modifications/active", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == modification_id
