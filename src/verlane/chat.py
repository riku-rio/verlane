from __future__ import annotations

from time import perf_counter

import typer
from rich.live import Live

from verlane.ollama import ChatChunk, OllamaClient, OllamaError
from verlane.settings import Settings
from verlane.ui import (
    ViewMode,
    activity,
    clear_rendered_block,
    clear_typed_prompt,
    console,
    duration_footer,
    generation_progress,
    generation_renderable,
    render_height,
    request_header,
)

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}
VIEW_COMMAND = "/view"
HELP_COMMAND = "/help"


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


def _show_help() -> None:
    typer.echo("\nCommands:\n")
    typer.echo("  /help        Show available commands")
    typer.echo("  /view        Toggle concise/full view")
    typer.echo("  /exit        Exit Verlane")
    typer.echo("  /quit        Exit Verlane\n")


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

    typer.echo("Type /help for commands.\n")

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
        if lowered == HELP_COMMAND:
            _show_help()
            continue
        if lowered == VIEW_COMMAND:
            view_mode = view_mode.toggled()
            typer.echo(f"View mode: {view_mode.value}\n")
            continue
        if prompt.startswith("/"):
            command = prompt.split(maxsplit=1)[0]
            typer.echo(f"Unknown command: {command}", err=True)
            typer.echo("Type /help for commands.\n", err=True)
            continue

        clear_typed_prompt(prompt)
        console.print(request_header(prompt, view_mode))
        messages.append({"role": "user", "content": prompt})

        assistant_parts: list[str] = []
        thinking_parts: list[str] = []
        final_chunk: ChatChunk | None = None
        started_at = perf_counter()
        answer_started = False

        live: Live | None = None
        live_active = False
        live_rows = 0

        try:
            ensure_model_loaded(client, settings)

            if console.is_terminal:
                progress = generation_progress()
                renderable = generation_renderable(progress, "", view_mode)
                live_rows = render_height(renderable)
                live = Live(
                    renderable,
                    console=console,
                    refresh_per_second=12,
                    transient=False,
                    vertical_overflow="ellipsis",
                )
                live.start()
                live_active = True

            try:
                for chunk in client.chat(
                    settings.model,
                    messages,
                    settings.ollama_options(),
                ):
                    final_chunk = chunk

                    if chunk.thinking and not answer_started:
                        thinking_parts.append(chunk.thinking)
                        if live_active and live is not None:
                            renderable = generation_renderable(
                                progress,
                                "".join(thinking_parts),
                                view_mode,
                            )
                            live_rows = render_height(renderable)
                            live.update(renderable, refresh=True)

                    if chunk.content:
                        if not answer_started:
                            answer_started = True
                            if live_active and live is not None:
                                live.stop()
                                live_active = False
                                clear_rendered_block(live_rows)
                        typer.echo(chunk.content, nl=False)
                        assistant_parts.append(chunk.content)
            finally:
                if live_active and live is not None:
                    live.stop()
                    live_active = False
                    clear_rendered_block(live_rows)
        except KeyboardInterrupt:
            typer.echo()
            return
        except OllamaError as exc:
            messages.pop()
            if answer_started:
                typer.echo()
            typer.echo(f"Error: {exc}", err=True)
            typer.echo()
            continue

        answer = "".join(assistant_parts)
        typer.echo()
        console.print(duration_footer(_duration_seconds(final_chunk, started_at)))
        typer.echo()
        messages.append({"role": "assistant", "content": answer})
