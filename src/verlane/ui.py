from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


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
