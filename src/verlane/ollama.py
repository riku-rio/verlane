from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OLLAMA_URL = "http://localhost:11434"


class OllamaError(RuntimeError):
    pass


class OllamaNotInstalledError(OllamaError):
    pass


class OllamaStartError(OllamaError):
    pass


@dataclass(frozen=True)
class ChatChunk:
    content: str = ""
    thinking: str = ""
    done: bool = False
    total_duration_ns: int | None = None


class OllamaClient:
    def _request_json(self, path: str) -> dict[str, Any]:
        request = Request(f"{OLLAMA_URL}{path}", method="GET")
        try:
            with urlopen(request, timeout=1) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise OllamaError(str(exc)) from exc

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{OLLAMA_URL}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise OllamaError(detail or f"Ollama returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise OllamaError(str(exc)) from exc

    def is_running(self) -> bool:
        try:
            self._request_json("/api/version")
        except OllamaError:
            return False
        return True

    def list_models(self) -> list[str]:
        payload = self._request_json("/api/tags")
        models = payload.get("models", [])
        if not isinstance(models, list):
            return []

        names: list[str] = []
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("model") or model.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return names

    def is_model_loaded(self, model: str, context_size: int | None = None) -> bool:
        payload = self._request_json("/api/ps")
        models = payload.get("models", [])
        if not isinstance(models, list):
            return False

        for loaded in models:
            if not isinstance(loaded, dict):
                continue
            name = loaded.get("model") or loaded.get("name")
            if name != model:
                continue
            if context_size is None:
                return True
            return loaded.get("context_length") == context_size

        return False

    def load_model(
        self,
        model: str,
        options: dict[str, int | float],
    ) -> None:
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
        }
        if options:
            payload["options"] = options
        self._post_json("/api/generate", payload)

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, int | float],
    ) -> Iterator[ChatChunk]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": True,
        }
        if options:
            payload["options"] = options

        request = Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request) as response:
                for raw_line in response:
                    if not raw_line.strip():
                        continue
                    chunk = json.loads(raw_line)
                    if not isinstance(chunk, dict):
                        continue

                    error = chunk.get("error")
                    if isinstance(error, str) and error:
                        raise OllamaError(error)

                    message = chunk.get("message")
                    content = ""
                    thinking = ""
                    if isinstance(message, dict):
                        raw_content = message.get("content")
                        raw_thinking = message.get("thinking")
                        if isinstance(raw_content, str):
                            content = raw_content
                        if isinstance(raw_thinking, str):
                            thinking = raw_thinking

                    total_duration = chunk.get("total_duration")
                    total_duration_ns = (
                        total_duration
                        if isinstance(total_duration, int) and not isinstance(total_duration, bool)
                        else None
                    )
                    done = chunk.get("done") is True

                    if content or thinking or done:
                        yield ChatChunk(
                            content=content,
                            thinking=thinking,
                            done=done,
                            total_duration_ns=total_duration_ns,
                        )
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise OllamaError(detail or f"Ollama returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise OllamaError(str(exc)) from exc


def start_ollama() -> None:
    executable = shutil.which("ollama")
    if executable is None:
        raise OllamaNotInstalledError("Ollama is not installed or is not available on PATH.")

    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen([executable, "serve"], **kwargs)
    except OSError as exc:
        raise OllamaStartError(str(exc)) from exc


def ensure_ollama_running(client: OllamaClient) -> bool:
    if client.is_running():
        return False

    start_ollama()

    for _ in range(40):
        time.sleep(0.25)
        if client.is_running():
            return True

    raise OllamaStartError("Ollama did not become ready after it was started.")
