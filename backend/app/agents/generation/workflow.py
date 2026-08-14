"""生成工作流执行器。

当前为与 LangGraph 等价的轻量状态机（节点 + 条件边），节点签名保持
`(state) -> state`，后续环境允许安装 langgraph-core 时可直接平替。

节点顺序：input_guardrail → parse_requirements → create_plan →
generate_code → output_guardrail → validate_build ⇄(repair) generate_code → summarize
"""

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


async def run_generation_workflow(state: GenerationState) -> GenerationState:
    state = {**state, **await input_guardrail(state)}
    state = {**state, **await parse_requirements(state)}
    state = {**state, **await create_plan(state)}

    while True:
        state = {**state, **await generate_code(state)}
        state = {**state, **await output_guardrail(state)}
        state = {**state, **await validate_build(state)}
        if state["status"] == "repair":
            state["repair_mode"] = True
            continue
        break

    state = {**state, **await summarize(state)}
    return state
