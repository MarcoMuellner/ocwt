from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer


@dataclass(frozen=True)
class OpenOptions:
    intent_or_branch: str | None
    at_files: tuple[str, ...]
    plan: bool
    agent: str
    editor: str | None


def complete_at_files(incomplete: str) -> list[str]:
    wants_at_prefix = incomplete.startswith("@")
    needle = incomplete[1:] if wants_at_prefix else incomplete

    base = Path()
    matches = sorted(base.glob(f"{needle}*"), key=lambda item: item.as_posix())

    output: list[str] = []
    for match in matches:
        text = match.as_posix()
        if match.is_dir() and not text.endswith("/"):
            text = f"{text}/"
        if wants_at_prefix:
            text = f"@{text}"
        output.append(text)
    return output


def run_open(options: OpenOptions) -> int:
    message_parts = [
        "open is not implemented yet",
        f"target={options.intent_or_branch!r}",
        f"files={list(options.at_files)!r}",
        f"plan={options.plan}",
        f"agent={options.agent!r}",
        f"editor={options.editor!r}",
    ]
    typer.echo("; ".join(message_parts))
    return 0
