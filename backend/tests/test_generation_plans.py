import asyncio
import time

import pytest

from app.core.config import get_settings
from app.services.events import get_broker
from app.services.llm import LLMClient


@pytest.mark.parametrize("fail", [False, True])
def test_plan_events_history_and_current_progress(client, admin_headers, user_headers, monkeypatch, fail):
    from app.agents.generation import agent

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_model", "test-plan")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    async def parse(self, requirement, tech_stack):
        return {"goal": "看板", "features": ["任务列表"]}

    async def plan(self, parsed, tech_stack):
        return [{"step": "页面结构", "detail": "检查 src/App.vue"}, {"step": "交互检查", "detail": "检查任务列表"}]

    async def execute(state):
        if fail:
            raise RuntimeError("test task failure")
        return {"files": [], "summary": "完成检查", "token_usage": {"prompt_tokens": 0, "completion_tokens": 0}}

    monkeypatch.setattr(LLMClient, "parse_requirement", parse)
    monkeypatch.setattr(LLMClient, "create_plan", plan)
    monkeypatch.setattr(agent, "run_generation_agent", execute)
    project = client.post("/api/projects", headers=admin_headers, json={"name": "计划展示", "template": "任务看板", "tech_stack": "vue3"}).json()
    response = client.post(f"/api/projects/{project['id']}/generations", headers=admin_headers, json={"requirement": "检查任务看板"})
    assert response.status_code == 201, response.text
    generation = response.json()
    generation_id = generation["id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        current = client.get(f"/api/generations/{generation_id}", headers=admin_headers).json()
        if current["status"] in {"succeeded", "failed"}:
            break
        time.sleep(.05)
    assert current["status"] == ("failed" if fail else "succeeded"), current

    payload = client.get(f"/api/generations/{generation_id}/plan", headers=admin_headers).json()
    assert payload["status"] == current["status"]
    assert [task["status"] for task in payload["tasks"]] == (["failed", "pending"] if fail else ["succeeded", "succeeded"])
    assert client.get(f"/api/generations/{generation_id}/plan", headers=user_headers).status_code == 403

    history = client.get(f"/api/sessions/{generation['session_id']}/messages", headers=admin_headers).json()
    plans = [message for message in history if message["msg_type"] == "plan"]
    assert len(plans) == 1
    assert plans[0]["tool_call_json"]["generation_id"] == generation_id
    assert len(plans[0]["tool_call_json"]["tasks"]) == 2
    assert not any(message["content"].startswith("实施计划：") for message in history)

    events = asyncio.run(get_broker().replay(generation_id, 0))
    assert len([event for event in events if event["type"] == "plan_created"]) == 1
    updates = [event for event in events if event["type"] == "plan_updated"]
    assert updates[0]["tasks"][0]["status"] == "running"
    assert updates[-1]["tasks"][0]["status"] == ("failed" if fail else "succeeded")
