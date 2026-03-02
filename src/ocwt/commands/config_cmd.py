from __future__ import annotations

import json

import typer

from ocwt.config_store import (
    VALID_CONFIG_KEYS,
    default_config,
    load_config,
    parse_value_for_key,
    reset_config_key,
    save_config,
    set_config_value,
)


def run_config_show() -> int:
    """Print the full effective config as JSON.

    Args:
        None.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    config = load_config()
    typer.echo(json.dumps(config.to_json_dict(), indent=2, sort_keys=True))
    return 0


def run_config_get(key: str) -> int:
    """Read a single config value with key validation.

    Args:
        key: Config key requested by the user.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    if key not in VALID_CONFIG_KEYS:
        typer.echo(f"Unknown config key: {key}", err=True)
        return 1

    config = load_config()
    value = config.to_json_dict()[key]
    typer.echo("null" if value is None else str(value))
    return 0


def run_config_set(key: str, raw_value: str) -> int:
    """Persist a single config override from CLI text input.

    Args:
        key: Config key to update.
        raw_value: Raw value text provided on the command line.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    if key not in VALID_CONFIG_KEYS:
        typer.echo(f"Unknown config key: {key}", err=True)
        return 1

    try:
        parsed = parse_value_for_key(key, raw_value)
        updated = set_config_value(load_config(), key, parsed)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        return 1

    path = save_config(updated)
    typer.echo(f"Saved {key} in {path}")
    return 0


def run_config_reset(key: str | None) -> int:
    """Reset one key or the entire config to defaults.

    Args:
        key: Optional key name; when omitted all keys are reset.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    if key is None:
        path = save_config(default_config())
        typer.echo(f"Reset all config keys in {path}")
        return 0

    if key not in VALID_CONFIG_KEYS:
        typer.echo(f"Unknown config key: {key}", err=True)
        return 1

    try:
        updated = reset_config_key(load_config(), key)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        return 1

    path = save_config(updated)
    typer.echo(f"Reset {key} in {path}")
    return 0


def run_config_editor(value: str) -> int:
    """Set default editor command used by ``open`` flows.

    Args:
        value: Editor executable name or ``none``.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("editor", value)


def run_config_agent(value: str) -> int:
    """Set default non-planning agent for branch generation tasks.

    Args:
        value: Agent identifier recognized by ``opencode``.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("agent", value)


def run_config_prompt_file(value: str) -> int:
    """Set the custom prompt file path for runtime prompts.

    Args:
        value: File path or ``default`` to clear override.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("prompt_file", value)


def run_config_branch_prompt_file(value: str) -> int:
    """Set the custom branch prompt template path.

    Args:
        value: File path or ``default`` to clear override.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("branch_prompt_file", value)


def run_config_worktree_parent(value: str) -> int:
    """Set the parent folder name used for linked worktree paths.

    Args:
        value: Folder name relative to the repository parent.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("worktree_parent", value)


def run_config_auto_plan(value: str) -> int:
    """Toggle automatic planning mode for ``open``.

    Args:
        value: Boolean text accepted by config parsing.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("auto_plan", value)


def run_config_auto_pull(value: str) -> int:
    """Toggle automatic fast-forward pull before new worktree creation.

    Args:
        value: Boolean text accepted by config parsing.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("auto_pull", value)


def run_config_open_editor(value: str) -> int:
    """Toggle automatic editor launch during ``open`` workflows.

    Args:
        value: Boolean text accepted by config parsing.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return run_config_set("open_editor", value)
