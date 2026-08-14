import json
import asyncio

import pytest

from app.agents.generation.agent import run_generation_agent
from app.agents.generation.state import GenerationState
from app.core.config import get_settings
from app.services.events import get_broker
from app.services.llm import LLMClient


def _make_state(
    project_id: int,
    user_id: int,
    session_id: int,
    requirement: str = "做一个页面",
) -> GenerationState:
    return {
        "generation_id": 999999,
        "project_id": project_id,
        "session_id": session_id,
        "user_id": user_id,
        "workspace": str(get_settings().workspace_dir / str(project_id)),
        "requirement": requirement,
        "tech_stack": "html",
        "llm_model": "fake",
        "parsed_requirement": {"goal": requirement, "features": [], "pages": ["主页"]},
        "plan": [{"step": "写页面", "detail": "创建 index.html"}],
        "files": [],
        "guardrails": [],
        "build_log": [],
        "errors": [],
        "build_attempt": 0,
        "max_build_attempts": 3,
        "eval_attempt": 0,
        "max_eval_attempts": 2,
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0},
        "status": "pending",
        "cancel_requested": False,
        "summary": "",
    }


def test_agent_loop_writes_files_and_finishes(
    client, admin_headers, monkeypatch
):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Agent单测", "template": "blank", "tech_stack": "html"},
    ).json()
    me = client.get("/api/users/me", headers=admin_headers).json()
    sessions = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()
    state = _make_state(project["id"], me["id"], sessions[0]["id"])

    calls = [
        {
            "content": "先创建页面",
            "reasoning_content": "思考：需要 index.html",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps(
                            {"path": "index.html", "content": "<h1>你好，灵码</h1>"}
                        ),
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "index.html"}),
                    },
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        },
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_3",
                    "type": "function",
                    "function": {
                        "name": "finish",
                        "arguments": json.dumps({"summary": "页面已生成"}),
                    },
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        },
    ]

    async def fake_complete(
        self, messages, tools, on_reasoning=None, on_content=None, temperature=0.2
    ):
        if on_reasoning:
            await on_reasoning("这是流式思考内容")
        return calls.pop(0)

    monkeypatch.setattr(LLMClient, "stream_complete_with_tools", fake_complete)

    async def scenario():
        broker = get_broker()
        queue = await broker.subscribe(state["generation_id"])
        try:
            result = await run_generation_agent(state)
        finally:
            await broker.unsubscribe(state["generation_id"], queue)
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())
        return result, events

    result, events = asyncio.run(scenario())

    ws = get_settings().workspace_dir / str(project["id"])
    assert (ws / "index.html").exists()
    assert "你好，灵码" in (ws / "index.html").read_text(encoding="utf-8")
    assert result["summary"] == "页面已生成"
    assert "index.html" in result["files"]
    assert result["token_usage"] == {"prompt_tokens": 20, "completion_tokens": 10}
    types = {e["type"] for e in events}
    assert "reasoning_delta" in types
    assert "stream_end" in types
    assert "tool_call_started" in types
    assert "tool_call_completed" in types
    assert "file_written" in types
    assert any(e.get("type") == "reasoning_delta" and e.get("text") for e in events)
    read_events = [
        e
        for e in events
        if e.get("type") == "tool_call_completed" and e.get("tool") == "read_file"
    ]
    assert read_events and read_events[0]["ok"] is True

    from app.core.database import SessionLocal
    from app.models.message import Message

    with SessionLocal() as db:
        saved = [
            row.msg_type
            for row in db.query(Message)
            .filter(Message.session_id == sessions[0]["id"])
            .all()
        ]
    assert "think" in saved
    assert "tool_call" in saved
    assert "file_written" in saved


def test_agent_guardrail_blocks_dangerous_write(
    client, admin_headers, monkeypatch
):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Agent护轨单测", "template": "blank", "tech_stack": "html"},
    ).json()
    me = client.get("/api/users/me", headers=admin_headers).json()
    sessions = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()
    state = _make_state(project["id"], me["id"], sessions[0]["id"])

    async def fake_complete(
        self, messages, tools, on_reasoning=None, on_content=None, temperature=0.2
    ):
        return {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps(
                            {
                                "path": "evil.sh",
                                "content": "rm -rf /important",
                            }
                        ),
                    },
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    monkeypatch.setattr(LLMClient, "stream_complete_with_tools", fake_complete)
    with pytest.raises(Exception) as exc:
        # 假 LLM 只返回一个危险写入，没有 finish → 轮次耗尽抛 GenerationFailed
        asyncio.run(run_generation_agent(state, max_iterations=1))
    assert "生成未在" in str(exc.value)

    ws = get_settings().workspace_dir / str(project["id"])
    assert not (ws / "evil.sh").exists()


def test_agent_max_iterations(client, admin_headers, monkeypatch):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Agent轮次单测", "template": "blank", "tech_stack": "html"},
    ).json()
    me = client.get("/api/users/me", headers=admin_headers).json()
    sessions = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()
    state = _make_state(project["id"], me["id"], sessions[0]["id"])

    async def fake_complete(
        self, messages, tools, on_reasoning=None, on_content=None, temperature=0.2
    ):
        return {
            "content": "",
            "tool_calls": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    monkeypatch.setattr(LLMClient, "stream_complete_with_tools", fake_complete)
    with pytest.raises(Exception) as exc:
        asyncio.run(run_generation_agent(state, max_iterations=2))
    assert "2 轮" in str(exc.value)


def test_agent_run_command_string_normalized(client, admin_headers, monkeypatch):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Agent命令单测", "template": "blank", "tech_stack": "html"},
    ).json()
    me = client.get("/api/users/me", headers=admin_headers).json()
    sessions = client.get(
        "/api/sessions", headers=admin_headers, params={"project_id": project["id"]}
    ).json()
    state = _make_state(project["id"], me["id"], sessions[0]["id"])

    calls = [
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_cmd",
                    "type": "function",
                    "function": {
                        "name": "run_command",
                        "arguments": json.dumps(
                            {"command": "node -e console.log(1)"}
                        ),
                    },
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_done",
                    "type": "function",
                    "function": {
                        "name": "finish",
                        "arguments": json.dumps({"summary": "完成"}),
                    },
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
    ]

    async def fake_complete(
        self, messages, tools, on_reasoning=None, on_content=None, temperature=0.2
    ):
        return calls.pop(0)

    monkeypatch.setattr(LLMClient, "stream_complete_with_tools", fake_complete)

    async def scenario():
        broker = get_broker()
        queue = await broker.subscribe(state["generation_id"])
        try:
            await run_generation_agent(state)
        finally:
            await broker.unsubscribe(state["generation_id"], queue)
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())
        return events

    events = asyncio.run(scenario())
    completed = [
        e
        for e in events
        if e.get("type") == "tool_call_completed" and e.get("tool") == "run_command"
    ]
    assert completed
    assert completed[0]["ok"] is True
    assert completed[0]["detail"] == "node -e console.log(1)"
