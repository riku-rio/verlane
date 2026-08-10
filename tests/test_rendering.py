from __future__ import annotations

import io
import unittest

from rich.console import Console

from verlane.rendering import MarkdownBuffer, MarkdownStreamRenderer


class MarkdownBufferTests(unittest.TestCase):
    def test_paragraph_waits_for_blank_line(self) -> None:
        buffer = MarkdownBuffer()

        self.assertEqual(buffer.feed("This is **bo"), [])
        self.assertEqual(buffer.feed("ld** text.\n"), [])
        self.assertEqual(buffer.feed("\n"), ["This is **bold** text.\n\n"])

    def test_fenced_code_waits_for_closing_fence(self) -> None:
        buffer = MarkdownBuffer()

        chunks = ["```py", "thon\n", "print(", "'hi')\n", "```\n"]
        blocks: list[str] = []
        for chunk in chunks:
            blocks.extend(buffer.feed(chunk))

        self.assertEqual(blocks, ["```python\nprint('hi')\n```\n"])
        self.assertEqual(buffer.finish(), [])

    def test_tilde_fence_and_chunked_closer(self) -> None:
        buffer = MarkdownBuffer()
        blocks: list[str] = []
        for chunk in ["~~~~python\n", "print(1)\n", "~~", "~~\n"]:
            blocks.extend(buffer.feed(chunk))

        self.assertEqual(blocks, ["~~~~python\nprint(1)\n~~~~\n"])

    def test_finish_flushes_unterminated_block(self) -> None:
        buffer = MarkdownBuffer()
        self.assertEqual(buffer.feed("## Heading\nbody"), [])
        self.assertEqual(buffer.finish(), ["## Heading\nbody"])

    def test_chunk_boundaries_do_not_change_source(self) -> None:
        source = "## Title\n\nParagraph with **bold** text.\n\n```python\nprint('ok')\n```\n"
        for chunk_size in range(1, 13):
            buffer = MarkdownBuffer()
            blocks: list[str] = []
            for start in range(0, len(source), chunk_size):
                blocks.extend(buffer.feed(source[start : start + chunk_size]))
            blocks.extend(buffer.finish())
            self.assertEqual("".join(blocks), source)


class MarkdownStreamRendererTests(unittest.TestCase):
    def make_console(self) -> tuple[Console, io.StringIO]:
        output = io.StringIO()
        return Console(file=output, force_terminal=False, width=80, color_system=None), output

    def test_raw_mode_preserves_markdown_exactly(self) -> None:
        console, output = self.make_console()
        renderer = MarkdownStreamRenderer(console, render_markdown=False)

        renderer.feed("## Hello\n\n")
        renderer.feed("Use **Rich**.")
        renderer.finish()

        self.assertEqual(output.getvalue(), "## Hello\n\nUse **Rich**.")

    def test_markdown_mode_renders_complete_blocks(self) -> None:
        console, output = self.make_console()
        renderer = MarkdownStreamRenderer(console, render_markdown=True)

        renderer.feed("## Hel")
        self.assertEqual(output.getvalue(), "")
        renderer.feed("lo\n\nUse **Rich**.\n\n")
        renderer.finish()

        rendered = output.getvalue()
        self.assertIn("Hello", rendered)
        self.assertIn("Use Rich.", rendered)
        self.assertNotIn("## Hello", rendered)
        self.assertNotIn("**Rich**", rendered)

    def test_default_mode_is_raw_for_non_terminal_output(self) -> None:
        console, output = self.make_console()
        renderer = MarkdownStreamRenderer(console)

        renderer.feed("**raw**")
        renderer.finish()

        self.assertEqual(output.getvalue(), "**raw**")

    def test_ensure_line_break_only_adds_one_when_needed(self) -> None:
        console, output = self.make_console()
        renderer = MarkdownStreamRenderer(console, render_markdown=False)

        renderer.feed("hello")
        renderer.finish()
        renderer.ensure_line_break()
        renderer.ensure_line_break()

        self.assertEqual(output.getvalue(), "hello\n")


if __name__ == "__main__":
    unittest.main()
