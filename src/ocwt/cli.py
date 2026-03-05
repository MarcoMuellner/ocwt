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
from ocwt.commands.open_cmd import (
    OpenOptions,
    complete_at_files,
    complete_files,
    run_build,
    run_open,
)

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
    file_path: Annotated[
        str | None,
        typer.Argument(help="File path used as work context.", autocompletion=complete_files),
    ] = None,
    plan: Annotated[bool, typer.Option("--plan", help="Enable one-shot planning mode")] = False,
    agent: Annotated[str | None, typer.Option("--agent", help="OpenCode agent name")] = None,
    editor: Annotated[
        str | None,
        typer.Option("--editor", help="Editor command override, or 'none'"),
    ] = None,
) -> None:
    """Open or create a worktree from a required file context.

    Args:
        file_path: Existing file path used as primary work context.
        plan: Whether planning mode should run before interactive session start.
        agent: Optional agent override for planning or branch generation.
        editor: Optional editor override for this invocation.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_open(
        OpenOptions(
            intent_or_branch=file_path,
            at_files=(),
            plan=plan,
            agent=agent,
            editor=editor,
        )
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("build")
def build_command(
    intent: Annotated[
        str | None,
        typer.Argument(help="Build intent text.", autocompletion=complete_at_files),
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
    """Open or create a worktree from intent text.

    Args:
        intent: Build intent text used for branch generation.
        at_files: Optional file mentions used as planning/build context.
        plan: Whether planning mode should run before interactive session start.
        agent: Optional agent override for planning or branch generation.
        editor: Optional editor override for this invocation.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    normalized_at_files = tuple(at_files or [])
    exit_code = run_build(
        OpenOptions(
            intent_or_branch=intent,
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
    """Close a branch worktree and delete its local branch.

    Args:
        branch_or_path: Optional branch name or worktree path.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_close(branch_or_path)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("completion")
def completion_command(
    shell: Annotated[str, typer.Argument(help="Shell name: bash or zsh")],
) -> None:
    """Print completion script content for supported shells.

    Args:
        shell: Target shell name.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_completion(shell)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("show")
def config_show_command() -> None:
    """Print the full effective config payload.

    Args:
        None.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_show()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("get")
def config_get_command(key: Annotated[str, typer.Argument(help="Config key")]) -> None:
    """Print a single config value.

    Args:
        key: Config key to read.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_get(key)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("set")
def config_set_command(
    key: Annotated[str, typer.Argument(help="Config key")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    """Persist one config key override.

    Args:
        key: Config key to change.
        value: Raw value string from CLI input.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_set(key, value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("reset")
def config_reset_command(
    key: Annotated[str | None, typer.Argument(help="Config key to reset")] = None,
) -> None:
    """Reset one key or all config keys to defaults.

    Args:
        key: Optional key name; omitted means reset all.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_reset(key)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("editor")
def config_editor_command(
    value: Annotated[str, typer.Argument(help="Editor executable or none")],
) -> None:
    """Set default editor command for open flows.

    Args:
        value: Editor executable or ``none``.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_editor(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("agent")
def config_agent_command(
    value: Annotated[str, typer.Argument(help="Default OpenCode agent")],
) -> None:
    """Set default non-planning agent.

    Args:
        value: Agent identifier.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_agent(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("prompt-file")
def config_prompt_file_command(
    value: Annotated[str, typer.Argument(help="Path or default")],
) -> None:
    """Set or clear the main prompt file override.

    Args:
        value: Path value or ``default``.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_prompt_file(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("branch-prompt-file")
def config_branch_prompt_file_command(
    value: Annotated[str, typer.Argument(help="Path or default")],
) -> None:
    """Set or clear the branch prompt file override.

    Args:
        value: Path value or ``default``.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_branch_prompt_file(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("worktree-parent")
def config_worktree_parent_command(
    value: Annotated[str, typer.Argument(help="Parent folder name")],
) -> None:
    """Set parent folder name used for linked worktree directories.

    Args:
        value: Parent directory name.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_worktree_parent(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("auto-plan")
def config_auto_plan_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    """Toggle automatic planning mode.

    Args:
        value: Boolean text value.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_auto_plan(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("auto-pull")
def config_auto_pull_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    """Toggle automatic repository pull before worktree creation.

    Args:
        value: Boolean text value.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_auto_pull(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("open-editor")
def config_open_editor_command(value: Annotated[str, typer.Argument(help="true or false")]) -> None:
    """Toggle automatic editor launch during ``open``.

    Args:
        value: Boolean text value.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_config_open_editor(value)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command("__complete_worktrees", hidden=True)
def complete_worktrees_command() -> None:
    """Emit internal close-completion branch candidates.

    Args:
        None.

    Returns:
        None. Raises ``typer.Exit`` when command execution fails.
    """
    exit_code = run_complete_worktrees()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def run() -> int:
    """Launch the Typer application entrypoint.

    Args:
        None.

    Returns:
        Process-style exit code for script entrypoints.
    """
    app()
    return 0
