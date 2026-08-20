import json
from pathlib import Path

from app.prompts import load_prompt
from app.services.route_agent import _fallback_route


CASES_PATH = Path(__file__).parent.parent / "evals" / "agent_regression_cases.json"


def _cases() -> dict:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def test_route_regression_cases():
    for case in _cases()["route"]:
        result = _fallback_route(case["requirement"])
        assert result["recommended_stack"] == case["expected_stack"], case["name"]


def test_generation_prompt_keeps_required_tool_workflow():
    prompt = load_prompt("generation_agent.md")
    for required in _cases()["generation_contract"]:
        assert required in prompt


def test_modification_prompt_keeps_clarification_and_interaction_rules():
    prompt = load_prompt("modification_agent.md")
    for required in _cases()["modification_contract"]:
        assert required in prompt
