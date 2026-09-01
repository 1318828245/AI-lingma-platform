from app.models.agent_context import AgentContextSnapshot
from app.models.message import Message
from app.models.project import Project
from app.models.session import Session as ChatSession
from app.models.user import User
from app.services.agent_context import build_context_package, persist_context_snapshot


def test_context_package_is_session_scoped_and_auditable(client, user_headers):
    with __import__("app.core.database", fromlist=["SessionLocal"]).SessionLocal() as db:
        user = db.query(User).filter_by(username="alice").one()
        project = Project(owner_id=user.id, name="Memory", slug="memory-test", tech_stack="vue3")
        db.add(project)
        db.flush()
        session = ChatSession(user_id=user.id, project_id=project.id, title="memory")
        db.add(session)
        db.flush()
        db.add_all([
            Message(session_id=session.id, role="user", content="首页要有蓝色按钮", msg_type="text"),
            Message(session_id=session.id, role="assistant", content="已创建首页", msg_type="assistant"),
        ])
        db.commit()
        payload = build_context_package(
            db, owner_id=user.id, project_id=project.id, session_id=session.id,
            current_instruction="把按钮改为绿色", element_snapshot={"text": "立即开始"},
            related_files=["src/App.vue"],
        )
        snapshot = persist_context_snapshot(
            db, owner_id=user.id, project_id=project.id, session_id=session.id,
            kind="modification", modification_id=99, payload=payload,
        )
        db.commit()
        assert payload["selected_element"]["text"] == "立即开始"
        assert payload["candidate_files"] == ["src/App.vue"]
        assert any("蓝色按钮" in row["content"] for row in payload["recent_messages"])
        snapshot_id = snapshot.id

    response = client.get(f"/api/sessions/{session.id}/agent-contexts", headers=user_headers)
    assert response.status_code == 200
    assert response.json()[0]["id"] == snapshot_id
    assert response.json()[0]["payload_json"]["candidate_files"] == ["src/App.vue"]

    cleared = client.delete(f"/api/sessions/{session.id}/agent-contexts", headers=user_headers)
    assert cleared.status_code == 200
    with __import__("app.core.database", fromlist=["SessionLocal"]).SessionLocal() as db:
        assert db.get(AgentContextSnapshot, snapshot_id) is None
