from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum

from rich.cells import cell_len
from rich.console import Console, Group, RenderableType
from rich.control import Control
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.segment import ControlType
from rich.table import Table
from rich.text import Text

console = Console()

CONCISE_PROMPT_LIMIT = 60
CONCISE_THINKING_LIMIT = 240
DURATION_COLUMN_WIDTH = 10
_ERASE_LINE = Control((ControlType.ERASE_IN_LINE, 2))


class ViewMode(str, Enum):
    CONCISE = "concise"
    FULL = "full"

    def toggled(self) -> "ViewMode":
        return ViewMode.FULL if self is ViewMode.CONCISE else ViewMode.CONCISE


@contextmanager
def activity(description: str) -> Iterator[None]:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True,
    )
    with progress:
        progress.add_task(description, total=None)
        yield


def _display_prompt(prompt: str, mode: ViewMode) -> str:
    if mode is ViewMode.FULL or len(prompt) <= CONCISE_PROMPT_LIMIT:
        return prompt
    return f"{prompt[:CONCISE_PROMPT_LIMIT].rstrip()}..."


def request_header(
    prompt: str,
    mode: ViewMode,
    duration_seconds: float | None = None,
) -> Table:
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=1, overflow="fold")
    table.add_column(width=DURATION_COLUMN_WIDTH, justify="right", no_wrap=True)

    request = Text("> ", style="bold")
    request.append(_display_prompt(prompt, mode))
    duration = Text(
        "" if duration_seconds is None else f"{duration_seconds:.2f}s",
        style="dim",
    )
    table.add_row(request, duration)
    return table


def clear_typed_prompt(prompt: str) -> None:
    if not console.is_terminal:
        return

    width = max(console.width, 1)
    cells = max(cell_len(f"> {prompt}"), 1)
    rows = max(1, (cells + width - 1) // width)

    console.control(Control.move(0, -rows), Control.move_to_column(0))
    for index in range(rows):
        console.control(_ERASE_LINE)
        if index < rows - 1:
            console.control(Control.move(0, 1), Control.move_to_column(0))
    if rows > 1:
        console.control(Control.move(0, -(rows - 1)), Control.move_to_column(0))


def render_height(renderable: RenderableType) -> int:
    return max(1, len(console.render_lines(renderable, console.options, pad=False)))


def rewrite_request_header(
    prompt: str,
    mode: ViewMode,
    duration_seconds: float,
    header_rows: int,
    response_rows: int,
) -> None:
    final_header = request_header(prompt, mode, duration_seconds)

    if not console.is_terminal:
        console.print(final_header)
        return

    console.control(
        Control.move(0, -(header_rows + response_rows)),
        Control.move_to_column(0),
    )
    for index in range(header_rows):
        console.control(_ERASE_LINE)
        if index < header_rows - 1:
            console.control(Control.move(0, 1), Control.move_to_column(0))
    if header_rows > 1:
        console.control(Control.move(0, -(header_rows - 1)), Control.move_to_column(0))

    console.print(final_header)
    console.control(Control.move(0, response_rows), Control.move_to_column(0))


def response_row_count(text: str) -> int:
    width = max(console.width, 1)
    rows = 1
    column = 0

    for char in text:
        if char == "\n":
            rows += 1
            column = 0
            continue
        if char == "\r":
            column = 0
            continue
        if char == "\t":
            char_width = 8 - (column % 8)
        else:
            char_width = cell_len(char)
        if char_width <= 0:
            continue
        if column >= width or column + char_width > width:
            rows += 1
            column = 0
        column += char_width

    return rows


def generation_progress() -> Progress:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        auto_refresh=False,
    )
    progress.add_task("Generating response...", total=None)
    return progress


def generation_renderable(
    progress: Progress,
    thinking: str,
    mode: ViewMode,
) -> RenderableType:
    items: list[RenderableType] = [progress.get_renderable()]
    if thinking:
        shown = thinking
        if mode is ViewMode.CONCISE:
            shown = " ".join(thinking.split())
            if len(shown) > CONCISE_THINKING_LIMIT:
                shown = f"...{shown[-CONCISE_THINKING_LIMIT:]}"
        label = Text("Thinking: ", style="bold dim")
        label.append(shown, style="dim")
        items.append(label)
    return Group(*items)
