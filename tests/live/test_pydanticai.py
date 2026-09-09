"""Live Pydantic AI tests: uv run --extra test python tests/live/test_pydanticai.py."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, BinaryContent, NativeOutput
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        bool(os.environ.get("CI")) or os.environ.get("RUN_OPENAI_TESTS") != "1",
        reason="Live OpenAI requests require RUN_OPENAI_TESTS=1 and are disabled in CI",
    ),
]


def run_agent(
    client_options,
    model,
    prompt,
    *,
    message_history=None,
    return_history=False,
    **kwargs,
):
    async def consume_events(_ctx, events):
        # The Codex endpoint requires streaming transport, even with Agent.run().
        async for _event in events:
            pass

    async def run():
        async with AsyncOpenAI(**client_options) as client:
            agent = Agent(
                OpenAIResponsesModel(
                    model, provider=OpenAIProvider(openai_client=client)
                ),
                instructions="Answer briefly and follow the user's requested format.",
                model_settings=OpenAIResponsesModelSettings(openai_store=False),
                **kwargs,
            )
            result = await agent.run(
                prompt,
                message_history=message_history,
                event_stream_handler=consume_events,
            )
            reply = result.output
            return (reply, result.all_messages()) if return_history else reply

    return asyncio.run(run())


def test_simple_message(client_options, model):
    reply = run_agent(
        client_options,
        model,
        "What is the capital of France? Reply with only the city name.",
    )
    print(f"\nPydantic AI response: {reply}", flush=True)
    assert reply.lower().strip(".!") == "paris"


def test_message_response_message(client_options, model):
    first, history = run_agent(
        client_options,
        model,
        "Choose a number from 10 to 99. Reply with only the number.",
        return_history=True,
    )
    print(f"\nPydantic AI conversation first response: {first}", flush=True)
    assert first.isdigit() and 10 <= int(first) <= 99
    # Pass the SDK's actual conversation history into the follow-up request.
    second = run_agent(
        client_options,
        model,
        "Add 1 to the number you just chose. Reply with only the number.",
        message_history=history,
    )
    print(f"Pydantic AI conversation follow-up response: {second}", flush=True)
    assert second == str(int(first) + 1), f"Context check failed: {first} -> {second}"


def test_message_with_image(client_options, model, red_png):
    reply = run_agent(
        client_options,
        model,
        [
            "What color is this image? Reply with one word.",
            BinaryContent(data=red_png, media_type="image/png"),
        ],
    )
    print(f"\nPydantic AI image response: {reply}", flush=True)
    assert reply.lower().strip(".!") == "red"


def test_tool_call(client_options, model):
    calls = []

    def add(a: int, b: int) -> int:
        """Add two integers."""
        calls.append((a, b))
        result = a + b
        print(f"\nPydantic AI tool call: add({a}, {b}) -> {result}", flush=True)
        return result

    reply = run_agent(
        client_options,
        model,
        "Use the add tool to add 17 and 25. Reply with only the result.",
        tools=[add],
    )
    print(f"Pydantic AI tool response: {reply}", flush=True)
    assert calls == [(17, 25)]
    assert reply.strip() == "42"


class Capital(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: str
    capital: str


def test_structured_output(client_options, model):
    reply = run_agent(
        client_options,
        model,
        "What is the capital of France? Return the country and capital.",
        output_type=NativeOutput(Capital),
    )
    print(f"\nPydantic AI structured response: {reply.model_dump_json()}", flush=True)
    assert isinstance(reply, Capital)
    assert reply.country == "France"
    assert reply.capital == "Paris"


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
