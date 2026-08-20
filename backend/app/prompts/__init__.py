"""Central prompt registry. Prompt text lives in sibling .md files for review."""

from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def render_prompt(name: str, **values: object) -> str:
    content = load_prompt(name)
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", str(value))
    return content
