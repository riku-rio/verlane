from __future__ import annotations

import io
import unittest
from collections.abc import Iterator
from unittest.mock import patch

from rich.console import Console

from verlane import chat
from verlane.ollama import ChatChunk
from verlane.settings import Settings


class FakeClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] | None = None

    def model_context_length(self, model: str) -> int | None:
        del model
        return 4096

    def load_model(self, model: str, options: dict[str, int | float]) -> None:
        raise AssertionError("model should already be loaded")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, int | float],
    ) -> Iterator[ChatChunk]:
        del model, options
        self.messages = messages
        yield ChatChunk(content="## Hel")
        yield ChatChunk(content="lo\n\nUse **Rich**.")
        yield ChatChunk(done=True, total_duration_ns=1_000_000_000, prompt_eval_count=10, eval_count=5)


class ChatRenderingTests(unittest.TestCase):
    def test_rendering_does_not_mutate_conversation_markdown(self) -> None:
        client = FakeClient()
        settings = Settings(model="test-model")
        output = io.StringIO()
        test_console = Console(file=output, force_terminal=False, width=80, color_system=None)

        with (
            patch.object(chat, "console", test_console),
            patch("builtins.input", side_effect=["render this", "/exit"]),
            patch.object(chat.typer, "echo"),
        ):
            chat.run_chat(client, settings, render_markdown=True)

        assert client.messages is not None
        self.assertEqual(
            client.messages[-1],
            {"role": "assistant", "content": "## Hello\n\nUse **Rich**."},
        )
        rendered = output.getvalue()
        self.assertIn("Hello", rendered)
        self.assertIn("Use Rich.", rendered)
        self.assertNotIn("## Hello", rendered)
        self.assertNotIn("**Rich**", rendered)


if __name__ == "__main__":
    unittest.main()
