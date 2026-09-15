import asyncio
import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base
from app.services.llm import LLMClient


@pytest.mark.parametrize("wrapped", [True, False])
def test_plan_accepts_object_contract_and_legacy_array(monkeypatch, wrapped):
    client = LLMClient()
    monkeypatch.setattr(type(client), "mode", property(lambda self: "real"))
    steps = [{"step": "实现 Vue 页面", "detail": "src/App.vue"}]

    async def complete(*args, **kwargs):
        return json.dumps({"steps": steps} if wrapped else steps)

    monkeypatch.setattr(client, "_real_complete", complete)
    assert asyncio.run(client.create_plan({"goal": "看板"}, "vue3")) == steps


def test_plan_rejects_invalid_shape(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(type(client), "mode", property(lambda self: "real"))

    async def complete(*args, **kwargs):
        return '{"steps": ["invalid"]}'

    monkeypatch.setattr(client, "_real_complete", complete)
    with pytest.raises(ValueError, match="计划格式无效"):
        asyncio.run(client.create_plan({"goal": "看板"}, "vue3"))


def test_real_repair_invokes_agent_with_build_diagnostics(monkeypatch, tmp_path):
    from app.agents.generation import agent, nodes

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(nodes, "_check_cancel", lambda state: None)

    async def emit(*args):
        pass

    async def repair(state):
        prompt = agent._build_user_prompt(state)
        assert "src/App.vue: invalid end tag" in prompt
        assert state.get("current_task") is None
        return {"files": ["src/App.vue"], "summary": "修复完成", "token_usage": {"prompt_tokens": 2, "completion_tokens": 3}}

    monkeypatch.setattr(nodes, "publish_event", emit)
    monkeypatch.setattr(agent, "run_generation_agent", repair)
    state = {
        "generation_id": 1, "workspace": str(tmp_path), "requirement": "任务看板",
        "tech_stack": "vue3", "repair_mode": True,
        "errors": ["npm run build 失败"],
        "build_log": ["src/App.vue: invalid end tag"],
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }
    result = asyncio.run(nodes.generate_code(state))
    assert result["status"] == "repairing"
    assert result["token_usage"] == {"prompt_tokens": 12, "completion_tokens": 23}


def test_build_exception_returns_failure_for_repair(monkeypatch, tmp_path):
    from app.services import sandbox

    monkeypatch.setattr(get_settings(), "build_mode", "real")

    async def build(*args):
        raise sandbox.BuildError("命令超时: npm run build")

    monkeypatch.setattr(sandbox, "_real_build", build)
    ok, log, errors = asyncio.run(sandbox.validate_build(tmp_path, "vue3"))
    assert not ok
    assert "命令超时" in errors[0]


def test_delete_generated_vue_with_foreign_keys_enabled(monkeypatch, tmp_path):
    from app.models.agent_context import AgentContextSnapshot
    from app.models.agent_memory import AgentMemory
    from app.models.asset import AssetJob
    from app.models.generation import Generation
    from app.models.generation_task import GenerationTask
    from app.models.modification import Modification
    from app.models.project import Project
    from app.models.session import Session as ChatSession
    from app.models.user import User
    from app.schemas.project import ProjectCreate
    from app.services.project import create_project, delete_project, project_workspace

    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setattr(get_settings(), "storage_dir", tmp_path)
    try:
        with Session(engine, expire_on_commit=False) as db:
            user = User(username="delete-test", password_hash="unused")
            db.add(user)
            db.commit()
            project = create_project(db, user.id, ProjectCreate(name="Vue 删除回归", tech_stack="vue3"), None)
            other = create_project(db, user.id, ProjectCreate(name="保留项目", tech_stack="html"), None)
            session = db.query(ChatSession).filter_by(project_id=project.id).one()
            gen = Generation(project_id=project.id, session_id=session.id, requirement="看板", status="failed")
            db.add(gen)
            db.flush()
            modification = Modification(project_id=project.id, session_id=session.id, generation_id=gen.id, instruction="修改", status="failed")
            db.add(modification)
            db.flush()
            db.add_all([
                GenerationTask(generation_id=gen.id, sequence_no=1, title="页面"),
                AgentMemory(owner_id=user.id, project_id=project.id, session_id=session.id, scope="session", content="看板"),
                AgentContextSnapshot(owner_id=user.id, project_id=project.id, session_id=session.id, generation_id=gen.id, modification_id=modification.id, kind="generation", payload_json={}),
                AssetJob(project_id=project.id, session_id=session.id, generation_id=gen.id, modification_id=modification.id),
            ])
            db.commit()
            workspace = project_workspace(project)
            delete_project(db, project)
            assert db.get(Project, project.id) is None
            assert db.get(Project, other.id) is not None
            assert not workspace.exists()
            for model in (GenerationTask, AgentMemory, AgentContextSnapshot, AssetJob, Modification):
                assert db.query(model).count() == 0
    finally:
        engine.dispose()
