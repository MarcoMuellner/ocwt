from __future__ import annotations

from typing import Annotated

import typer

from ocwt.commands.close_cmd import run_close
from ocwt.commands.completion_cmd import run_complete_worktrees, run_completion
from ocwt.commands.config_cmd import (
    run_config_agent,
    run_config_auto_plan,
    run_config_auto_pull,
    run_config_branch_prompt_file,
    run_config_editor,
    run_config_get,
    run_config_open_editor,
    run_config_prompt_file,
    run_config_reset,
    run_config_set,
    run_config_show,
    run_config_worktree_parent,
)
from ocwt.commands.open_cmd import OpenOptions, complete_at_files, run_open

app = typer.Typer(
    name="ocwt",
    no_args_is_help=True,
    add_completion=True,
    help="OpenCode + Git worktree helper",
)
config_app = typer.Typer(help="Manage ocwt configuration")
app.add_typer(config_app, name="config")


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
    agent: Annotated[str | None, typer.Option("--agent", help="OpenCode agent name")] = None,
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


@config_app.command("show")
def config_show_command() -> None:
    exit_code = run_config_show()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("get")
def config_get_command(key: Annotated[str, typer.Argument(help="Config key")]) -> None:
    exit_code = run_config_get(key)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("set")
def config_set_command(
    key: Annotated[str, typer.Argument(help="Config key")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    exit_code = run_config_set(key, value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("reset")
def config_reset_command(
    key: Annotated[str | None, typer.Argument(help="Config key to reset")] = None,
) -> None:
    exit_code = run_config_reset(key)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("editor")
def config_editor_command(
    value: Annotated[str, typer.Argument(help="Editor executable or none")],
) -> None:
    exit_code = run_config_editor(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("agent")
def config_agent_command(
    value: Annotated[str, typer.Argument(help="Default OpenCode agent")],
) -> None:
    exit_code = run_config_agent(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("prompt-file")
def config_prompt_file_command(
    value: Annotated[str, typer.Argument(help="Path or default")],
) -> None:
    exit_code = run_config_prompt_file(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("branch-prompt-file")
def config_branch_prompt_file_command(
    value: Annotated[str, typer.Argument(help="Path or default")],
) -> None:
    exit_code = run_config_branch_prompt_file(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("worktree-parent")
def config_worktree_parent_command(
    value: Annotated[str, typer.Argument(help="Parent folder name")],
) -> None:
    exit_code = run_config_worktree_parent(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("auto-plan")
def config_auto_plan_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    exit_code = run_config_auto_plan(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("auto-pull")
def config_auto_pull_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    exit_code = run_config_auto_pull(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("open-editor")
def config_open_editor_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    exit_code = run_config_open_editor(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("__complete_worktrees", hidden=True)
def complete_worktrees_command() -> None:
    exit_code = run_complete_worktrees()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def run() -> int:
    app()
    return 0
