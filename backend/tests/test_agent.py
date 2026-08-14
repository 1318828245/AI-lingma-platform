import json
import asyncio

import pytest

from app.agents.generation.agent import run_generation_agent
from app.agents.generation.state import GenerationState
from app.core.config import get_settings
from app.services.llm import LLMClient


def _make_state(project_id: int, user_id: int, requirement: str = "做一个页面") -> GenerationState:
    return {
        "generation_id": 999999,
        "project_id": project_id,
        "session_id": 1,
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
    state = _make_state(project["id"], me["id"])

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
                        "name": "finish",
                        "arguments": json.dumps({"summary": "页面已生成"}),
                    },
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        },
    ]

    async def fake_complete(messages, tools, temperature=0.2):
        return calls.pop(0)

    monkeypatch.setattr(LLMClient, "complete_with_tools", fake_complete)
    result = asyncio.run(run_generation_agent(state))

    ws = get_settings().workspace_dir / str(project["id"])
    assert (ws / "index.html").exists()
    assert "你好，灵码" in (ws / "index.html").read_text(encoding="utf-8")
    assert result["summary"] == "页面已生成"
    assert "index.html" in result["files"]
    assert result["token_usage"] == {"prompt_tokens": 15, "completion_tokens": 8}


def test_agent_guardrail_blocks_dangerous_write(
    client, admin_headers, monkeypatch
):
    project = client.post(
        "/api/projects",
        headers=admin_headers,
        json={"name": "Agent护轨单测", "template": "blank", "tech_stack": "html"},
    ).json()
    me = client.get("/api/users/me", headers=admin_headers).json()
    state = _make_state(project["id"], me["id"])

    async def fake_complete(messages, tools, temperature=0.2):
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

    monkeypatch.setattr(LLMClient, "complete_with_tools", fake_complete)
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
    state = _make_state(project["id"], me["id"])

    async def fake_complete(messages, tools, temperature=0.2):
        return {
            "content": "继续",
            "tool_calls": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    monkeypatch.setattr(LLMClient, "complete_with_tools", fake_complete)
    with pytest.raises(Exception) as exc:
        asyncio.run(run_generation_agent(state, max_iterations=2))
    assert "2 轮" in str(exc.value)
