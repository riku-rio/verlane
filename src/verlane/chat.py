from __future__ import annotations

import typer

from verlane.ollama import OllamaClient, OllamaError
from verlane.settings import Settings

EXIT_COMMANDS = {"exit", "quit"}


def run_chat(client: OllamaClient, settings: Settings) -> None:
    if settings.model is None:
        raise ValueError("A model must be selected before starting chat.")

    messages: list[dict[str, str]] = []

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
            for part in client.chat(settings.model, messages, settings.ollama_options()):
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
