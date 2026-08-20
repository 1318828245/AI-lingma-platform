from app.prompts import load_prompt, render_prompt


def test_prompt_catalog_contains_every_model_instruction():
    expected = {
        "route_agent.md",
        "generation_agent.md",
        "modification_agent.md",
        "generation_tasks/requirement_parser.md",
        "generation_tasks/implementation_plan.md",
        "generation_tasks/delivery_summary.md",
    }
    role_prompts = {
        "route_agent.md",
        "generation_agent.md",
        "modification_agent.md",
        "generation_tasks/requirement_parser.md",
        "generation_tasks/implementation_plan.md",
    }
    for name in expected:
        content = load_prompt(name)
        assert content
        if name in role_prompts:
            assert "## Role" in content


def test_prompt_renderer_replaces_generation_agent_variables():
    rendered = render_prompt(
        "generation_agent.md",
        tech_stack="html",
        parsed_requirement='{"goal":"landing page"}',
        plan="[]",
    )
    assert "{{" not in rendered
    assert "html" in rendered
