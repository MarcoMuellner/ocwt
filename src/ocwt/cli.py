from __future__ import annotations

from typing import Annotated

import typer

from ocwt.commands.close_cmd import run_close
from ocwt.commands.completion_cmd import run_completion
from ocwt.commands.config_cmd import run_config
from ocwt.commands.open_cmd import OpenOptions, complete_at_files, run_open

app = typer.Typer(
    name="ocwt",
    no_args_is_help=True,
    add_completion=True,
    help="OpenCode + Git worktree helper",
)


@app.command("open")
def open_command(
    intent_or_branch: Annotated[
        str | None,
        typer.Argument(help="Build intent or branch name.", autocompletion=complete_at_files),
    ] = None,
    at_files: Annotated[
        list[str] | None,
        typer.Argument(help="Optional @file references.", autocompletion=complete_at_files),
    ] = None,
    plan: Annotated[bool, typer.Option("--plan", help="Enable one-shot planning mode")] = False,
    agent: Annotated[str, typer.Option("--agent", help="OpenCode agent name")] = "build",
    editor: Annotated[
        str | None,
        typer.Option("--editor", help="Editor command override, or 'none'"),
    ] = None,
) -> None:
    normalized_at_files = tuple(at_files or [])
    exit_code = run_open(
        OpenOptions(
            intent_or_branch=intent_or_branch,
            at_files=normalized_at_files,
            plan=plan,
            agent=agent,
            editor=editor,
        )
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("close")
def close_command(
    branch_or_path: Annotated[
        str | None, typer.Argument(help="Branch name or worktree path")
    ] = None,
) -> None:
    exit_code = run_close(branch_or_path)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("completion")
def completion_command(
    shell: Annotated[str, typer.Argument(help="Shell name: bash or zsh")],
) -> None:
    exit_code = run_completion(shell)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("config")
def config_command() -> None:
    exit_code = run_config()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def run() -> int:
    app()
    return 0
