from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ocwt.cli import app


def test_config_set_and_get(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    set_result = runner.invoke(app, ["config", "set", "editor", "zed"])
    get_result = runner.invoke(app, ["config", "get", "editor"])

    assert set_result.exit_code == 0
    assert get_result.exit_code == 0
    assert get_result.stdout.strip() == "zed"


def test_config_reset_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    _ = runner.invoke(app, ["config", "set", "agent", "other"])
    reset_result = runner.invoke(app, ["config", "reset"])
    get_result = runner.invoke(app, ["config", "get", "agent"])

    assert reset_result.exit_code == 0
    assert get_result.stdout.strip() == "build"
