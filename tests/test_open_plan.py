from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ocwt.commands.open_cmd import _find_session_id, _generate_branch_name, _plan_and_launch


def test_find_session_id_from_nested_payload() -> None:
    payload = {
        "type": "run.completed",
        "result": {
            "session": {"id": "ses_123"},
        },
    }

    assert _find_session_id(payload) == "ses_123"


def test_find_session_id_from_event_id() -> None:
    payload = {"event": "session.created", "id": "ses_abc"}

    assert _find_session_id(payload) == "ses_abc"


def test_find_session_id_ignores_non_id_session_string() -> None:
    payload = {"event": "session.created", "session": "created", "id": "not_a_session_id"}

    assert _find_session_id(payload) is None


def test_generate_branch_name_uses_separator_before_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        captured["args"] = args
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="feat/example\n", stderr=""
        )

    monkeypatch.setattr("ocwt.commands.open_cmd.subprocess.run", fake_run)

    branch = _generate_branch_name("Build this", [Path("/tmp/spec.md")], "seed", "build")

    assert branch == "feat/example"
    assert "--" in captured["args"]
    assert captured["args"][captured["args"].index("--") + 1].startswith(
        "You are generating a git branch name."
    )


def test_plan_and_launch_uses_separator_before_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_popen: dict[str, list[str]] = {}
    captured_run: dict[str, list[str]] = {}

    class DummyProc:
        def __init__(self) -> None:
            self.stdout = iter(['{"event":"session.created","id":"ses_123"}\n'])

        def wait(self) -> int:
            return 0

    def fake_popen(
        args: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: object,
        text: bool,
    ) -> DummyProc:
        _ = (cwd, stdout, stderr, text)
        captured_popen["args"] = args
        return DummyProc()

    def fake_run(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        captured_run["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ocwt.commands.open_cmd.subprocess.Popen", fake_popen)
    monkeypatch.setattr("ocwt.commands.open_cmd.subprocess.run", fake_run)

    exit_code = _plan_and_launch(tmp_path, "Build message", [Path("/tmp/spec.md")], "build")

    assert exit_code == 0
    assert "--" in captured_popen["args"]
    assert captured_popen["args"][captured_popen["args"].index("--") + 1] == "Build message"
    assert captured_run["args"][:3] == ["opencode", "--session", "ses_123"]
