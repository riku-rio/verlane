from __future__ import annotations

from time import perf_counter

import typer
from rich.live import Live

from verlane.ollama import ChatChunk, OllamaClient, OllamaError
from verlane.settings import Settings
from verlane.ui import (
    ViewMode,
    activity,
    clear_typed_prompt,
    console,
    generation_progress,
    generation_renderable,
    render_height,
    request_header,
    response_row_count,
    rewrite_request_header,
)

EXIT_COMMANDS = {"exit", "quit"}
VIEW_COMMAND = "/view"


def ensure_model_loaded(client: OllamaClient, settings: Settings) -> None:
    if settings.model is None:
        raise ValueError("A model must be selected before loading it.")

    if client.is_model_loaded(settings.model, settings.context_size):
        return

    with activity(f"Loading {settings.model}..."):
        client.load_model(settings.model, settings.ollama_load_options())


def _duration_seconds(chunk: ChatChunk | None, started_at: float) -> float:
    if chunk is not None and chunk.total_duration_ns is not None:
        return chunk.total_duration_ns / 1_000_000_000
    return perf_counter() - started_at


def run_chat(client: OllamaClient, settings: Settings) -> None:
    if settings.model is None:
        raise ValueError("A model must be selected before starting chat.")

    messages: list[dict[str, str]] = []
    view_mode = ViewMode.CONCISE

    try:
        ensure_model_loaded(client, settings)
    except OllamaError as exc:
        typer.echo(f"Error: Could not load {settings.model}: {exc}", err=True)
        return

    while True:
        try:
            prompt = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            return

        if not prompt:
            continue
        lowered = prompt.lower()
        if lowered in EXIT_COMMANDS:
            return
        if lowered == VIEW_COMMAND:
            view_mode = view_mode.toggled()
            typer.echo(f"View mode: {view_mode.value}\n")
            continue

        clear_typed_prompt(prompt)
        header = request_header(prompt, view_mode)
        header_rows = render_height(header)
        console.print(header)

        messages.append({"role": "user", "content": prompt})
        assistant_parts: list[str] = []
        thinking_parts: list[str] = []
        final_chunk: ChatChunk | None = None
        started_at = perf_counter()

        try:
            ensure_model_loaded(client, settings)
            progress = generation_progress()
            live = Live(
                generation_renderable(progress, "", view_mode),
                console=console,
                refresh_per_second=12,
                transient=True,
                vertical_overflow="ellipsis",
            )
            live_active = False
            live.start()
            live_active = True

            try:
                for chunk in client.chat(
                    settings.model,
                    messages,
                    settings.ollama_options(),
                ):
                    final_chunk = chunk
                    if chunk.thinking and live_active:
                        thinking_parts.append(chunk.thinking)
                        live.update(
                            generation_renderable(
                                progress,
                                "".join(thinking_parts),
                                view_mode,
                            )
                        )
                    if chunk.content:
                        if live_active:
                            live.stop()
                            live_active = False
                        typer.echo(chunk.content, nl=False)
                        assistant_parts.append(chunk.content)
            finally:
                if live_active:
                    live.stop()
        except KeyboardInterrupt:
            typer.echo()
            return
        except OllamaError as exc:
            messages.pop()
            typer.echo(f"Error: {exc}", err=True)
            continue

        answer = "".join(assistant_parts)
        typer.echo()
        rewrite_request_header(
            prompt,
            view_mode,
            _duration_seconds(final_chunk, started_at),
            header_rows,
            response_row_count(answer),
        )
        typer.echo()
        messages.append({"role": "assistant", "content": answer})
