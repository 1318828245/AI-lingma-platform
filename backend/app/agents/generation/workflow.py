"""生成工作流（LangGraph StateGraph）。

节点顺序：input_guardrail → parse_requirements → create_plan →
generate_code → output_guardrail → validate_build ⇄(repair) generate_code → summarize
"""

from langgraph.graph import END, StateGraph

from app.agents.generation.nodes import (
    create_plan,
    generate_code,
    input_guardrail,
    output_guardrail,
    parse_requirements,
    summarize,
    validate_build,
)
from app.agents.generation.state import GenerationState


def _route_after_build(state: GenerationState) -> str:
    return "repair" if state.get("status") == "repair" else "done"


def build_generation_graph() -> StateGraph:
    graph = StateGraph(GenerationState)
    graph.add_node("input_guardrail", input_guardrail)
    graph.add_node("parse_requirements", parse_requirements)
    graph.add_node("create_plan", create_plan)
    graph.add_node("generate_code", generate_code)
    graph.add_node("output_guardrail", output_guardrail)
    graph.add_node("validate_build", validate_build)
    graph.add_node("summarize", summarize)

    graph.set_entry_point("input_guardrail")
    graph.add_edge("input_guardrail", "parse_requirements")
    graph.add_edge("parse_requirements", "create_plan")
    graph.add_edge("create_plan", "generate_code")
    graph.add_edge("generate_code", "output_guardrail")
    graph.add_edge("output_guardrail", "validate_build")
    graph.add_conditional_edges(
        "validate_build",
        _route_after_build,
        {"repair": "generate_code", "done": "summarize"},
    )
    graph.add_edge("summarize", END)
    return graph


_compiled_graph = None


async def run_generation_workflow(state: GenerationState) -> GenerationState:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_generation_graph().compile()
    return await _compiled_graph.ainvoke(state)
