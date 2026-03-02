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
    config = load_config()
    typer.echo(json.dumps(config.to_json_dict(), indent=2, sort_keys=True))
    return 0


def run_config_get(key: str) -> int:
    if key not in VALID_CONFIG_KEYS:
        typer.echo(f"Unknown config key: {key}", err=True)
        return 1

    config = load_config()
    value = config.to_json_dict()[key]
    typer.echo("null" if value is None else str(value))
    return 0


def run_config_set(key: str, raw_value: str) -> int:
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
    return run_config_set("editor", value)


def run_config_agent(value: str) -> int:
    return run_config_set("agent", value)


def run_config_prompt_file(value: str) -> int:
    return run_config_set("prompt_file", value)


def run_config_branch_prompt_file(value: str) -> int:
    return run_config_set("branch_prompt_file", value)


def run_config_worktree_parent(value: str) -> int:
    return run_config_set("worktree_parent", value)


def run_config_auto_plan(value: str) -> int:
    return run_config_set("auto_plan", value)


def run_config_auto_pull(value: str) -> int:
    return run_config_set("auto_pull", value)


def run_config_open_editor(value: str) -> int:
    return run_config_set("open_editor", value)
