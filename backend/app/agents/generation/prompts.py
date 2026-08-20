"""Compatibility exports for generation workflow task prompts."""

from app.prompts import load_prompt

PROMPT_PARSE_REQUIREMENT = load_prompt("generation_tasks/requirement_parser.md")
PROMPT_CREATE_PLAN = load_prompt("generation_tasks/implementation_plan.md")
PROMPT_GENERATION_SUMMARY = load_prompt("generation_tasks/delivery_summary.md")
