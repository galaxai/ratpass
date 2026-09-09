"""Live SDK tests: uv run --extra test python tests/live/test_openai.py."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        bool(os.environ.get("CI")) or os.environ.get("RUN_OPENAI_TESTS") != "1",
        reason="Live OpenAI requests require RUN_OPENAI_TESTS=1 and are disabled in CI",
    ),
]


@pytest.fixture(scope="module")
def client(client_options):
    with OpenAI(**client_options) as client:
        yield client


def request(messages, client, model, **kwargs):
    output = []
    with client.responses.create(
        model=model,
        instructions="Answer briefly and follow the user's requested format.",
        input=messages,
        store=False,
        stream=True,
        **kwargs,
    ) as stream:
        for event in stream:
            if event.type == "response.output_item.done":
                output.append(event.item.model_dump(exclude_none=True))
            if event.type == "response.completed":
                # Prefer completed items; the final snapshot can omit their text.
                return output or [
                    item.model_dump(exclude_none=True) for item in event.response.output
                ]
            if event.type in {"error", "response.failed", "response.incomplete"}:
                pytest.fail(f"Response stream ended with {event.type}")
    pytest.fail("Stream ended without a completed response")


def output_text(output):
    text = "".join(
        part["text"]
        for item in output
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ).strip()
    if not text:
        # Keep diagnostics useful without dumping encrypted reasoning payloads.
        item_types = [item.get("type") for item in output]
        received = [
            part.get("text")
            for item in output
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
        raise AssertionError(
            f"Expected a nonempty text response. Item types: {item_types}; "
            f"received text: {received!r}"
        )
    return text


def user(text):
    return {"role": "user", "content": text}


def test_simple_message(client, model):
    reply = output_text(
        request(
            [user("What is the capital of France? Reply with only the city name.")],
            client,
            model,
        )
    )
    print(f"\nSimple message response: {reply}", flush=True)
    assert reply.lower().strip(".!") == "paris", f"Unexpected reply: {reply}"


def test_message_response_message(client, model):
    messages = [user("Choose a number from 10 to 99. Reply with only the number.")]
    output = request(messages, client, model)
    first = output_text(output)
    print(f"\nConversation first response: {first}", flush=True)
    assert first.isdigit() and 10 <= int(first) <= 99, f"Unexpected number: {first}"
    # Replay the actual assistant reply; storage is disabled on this endpoint.
    messages += [item for item in output if item.get("type") == "message"]
    messages.append(
        user("Add 1 to the number you just chose. Reply with only the number.")
    )
    second = output_text(request(messages, client, model))
    print(f"Conversation follow-up response: {second}", flush=True)
    assert second == str(int(first) + 1), f"Context check failed: {first} -> {second}"


def test_message_with_image(client, model, red_png):
    message = {
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": "What color is this image? Reply with one word.",
            },
            {
                "type": "input_image",
                "image_url": "data:image/png;base64,"
                + base64.b64encode(red_png).decode(),
            },
        ],
    }
    reply = output_text(request([message], client, model))
    print(f"\nImage response: {reply}", flush=True)
    assert reply.lower().strip(".!") == "red", f"Unexpected image answer: {reply}"


class Capital(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: str
    capital: str


def test_structured_output(client, model):
    output = request(
        [user("What is the capital of France? Return the country and capital.")],
        client,
        model,
        text={
            "format": {
                "type": "json_schema",
                "name": "capital",
                "strict": True,
                "schema": Capital.model_json_schema(),
            }
        },
    )
    text = output_text(output)
    print(f"\nOpenAI structured response: {text}", flush=True)
    reply = Capital.model_validate_json(text, strict=True)
    assert reply.country == "France"
    assert reply.capital == "Paris"


def test_tool_call(client, model):
    tools = [
        {
            "type": "function",
            "name": "add",
            "description": "Add two integers.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        }
    ]
    messages = [user("Use the add tool to add 17 and 25. Reply with only the result.")]
    output = request(
        messages,
        client,
        model,
        tools=tools,
        tool_choice={"type": "function", "name": "add"},
        include=["reasoning.encrypted_content"],
    )
    calls = [item for item in output if item.get("type") == "function_call"]
    assert len(calls) == 1, f"Expected one tool call, got {len(calls)}"
    call = calls[0]
    assert call["name"] == "add"
    args = json.loads(call["arguments"])
    assert args == {"a": 17, "b": 25}
    result = args["a"] + args["b"]
    print(f"\nOpenAI tool call: add({args['a']}, {args['b']}) -> {result}", flush=True)
    messages += output
    messages.append(
        {
            "type": "function_call_output",
            "call_id": call["call_id"],
            "output": str(result),
        }
    )
    # This Codex endpoint/model can return whitespace with tool_choice="none"
    # after a tool result. Allow normal continuation and verify it answers.
    continuation = request(messages, client, model, tools=tools, tool_choice="auto")
    assert not any(item.get("type") == "function_call" for item in continuation), (
        "Expected a final answer after the tool result, got another tool call"
    )
    reply = output_text(continuation)
    print(f"OpenAI tool response: {reply}", flush=True)
    assert reply.strip() == "42"


if __name__ == "__main__":
    # Running this file explicitly opts in; the CI skip still takes precedence.
    os.environ["RUN_OPENAI_TESTS"] = "1"
    raise SystemExit(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(Path(__file__).resolve()),
                *sys.argv[1:],
                "-v",
                "-s",
            ],
            check=False,
        ).returncode
    )
