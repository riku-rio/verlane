from __future__ import annotations

from collections.abc import Iterator

import typer

from verlane.ollama import OllamaClient, OllamaError
from verlane.settings import Settings
from verlane.ui import activity

EXIT_COMMANDS = {"exit", "quit"}


def ensure_model_loaded(client: OllamaClient, settings: Settings) -> None:
    if settings.model is None:
        raise ValueError("A model must be selected before loading it.")

    if client.is_model_loaded(settings.model, settings.context_size):
        return

    with activity(f"Loading {settings.model}..."):
        client.load_model(settings.model, settings.ollama_load_options())


def _first_response_part(stream: Iterator[str]) -> str | None:
    with activity("Generating response..."):
        return next(stream, None)


def run_chat(client: OllamaClient, settings: Settings) -> None:
    if settings.model is None:
        raise ValueError("A model must be selected before starting chat.")

    messages: list[dict[str, str]] = []

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
        if prompt.lower() in EXIT_COMMANDS:
            return

        messages.append({"role": "user", "content": prompt})
        assistant_parts: list[str] = []

        try:
            ensure_model_loaded(client, settings)
            stream = client.chat(settings.model, messages, settings.ollama_options())
            first_part = _first_response_part(stream)
            if first_part is not None:
                typer.echo(first_part, nl=False)
                assistant_parts.append(first_part)
            for part in stream:
                typer.echo(part, nl=False)
                assistant_parts.append(part)
        except KeyboardInterrupt:
            typer.echo()
            return
        except OllamaError as exc:
            messages.pop()
            typer.echo(f"Error: {exc}", err=True)
            continue

        typer.echo("\n")
        messages.append({"role": "assistant", "content": "".join(assistant_parts)})
