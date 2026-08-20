from app.services.model.contracts import ModelResponse, ModelToolCall


def test_model_response_normalizes_and_round_trips_tool_calls():
    response = ModelResponse.from_wire(
        {
            "content": "done",
            "reasoning_content": "brief progress",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path":"index.html"}'},
                }
            ],
        },
        {"prompt_tokens": 12, "completion_tokens": 4},
    )

    assert response.content == "done"
    assert response.tool_calls == [ModelToolCall("call_1", "read_file", '{"path":"index.html"}')]
    assert response.to_wire()["tool_calls"][0]["function"]["name"] == "read_file"
    assert response.usage == {"prompt_tokens": 12, "completion_tokens": 4}


def test_model_response_ignores_nested_usage_details():
    response = ModelResponse.from_wire(
        {"content": "ok"},
        {
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "completion_tokens_details": {"reasoning_tokens": 1},
        },
    )

    assert response.usage == {"prompt_tokens": 3, "completion_tokens": 2}
