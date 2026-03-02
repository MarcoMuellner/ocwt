from __future__ import annotations

from pathlib import Path

import pytest

from ocwt.config_store import (
    config_path,
    default_config,
    load_config,
    parse_value_for_key,
    reset_config_key,
    save_config,
    set_config_value,
)


def test_load_config_returns_defaults_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    config = load_config()

    assert config == default_config()


def test_set_and_save_and_reload_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    updated = set_config_value(load_config(), "editor", "zed")
    save_config(updated)

    reloaded = load_config()
    assert reloaded.editor == "zed"


def test_reset_config_key_restores_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    updated = set_config_value(load_config(), "worktree_parent", ".alt-worktrees")
    restored = reset_config_key(updated, "worktree_parent")

    assert restored.worktree_parent == default_config().worktree_parent


def test_parse_value_for_key() -> None:
    assert parse_value_for_key("auto_plan", "true") is True
    assert parse_value_for_key("prompt_file", "default") is None
    assert parse_value_for_key("agent", "build") == "build"


def test_config_path_uses_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_path() == tmp_path / ".config" / "ocwt" / "config.json"
