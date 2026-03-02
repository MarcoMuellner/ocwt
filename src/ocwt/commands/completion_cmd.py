from __future__ import annotations

import typer


def run_completion(shell: str) -> int:
    normalized = shell.strip().lower()
    if normalized not in {"bash", "zsh"}:
        raise typer.BadParameter("shell must be one of: bash, zsh")

    typer.echo(
        f"Use 'ocwt --show-completion {normalized}' to print completion or "
        "'ocwt --install-completion' to install completion for your current shell."
    )
    return 0
