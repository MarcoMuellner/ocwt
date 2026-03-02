from __future__ import annotations

from pathlib import Path

import pytest

from ocwt.commands.completion_cmd import completion_worktree_branches, run_completion


def test_run_completion_prints_shell_script(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_completion("bash")
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "_ocwt_complete()" in output
    assert "complete -o bashdefault -o default -F _ocwt_complete ocwt" in output


def test_completion_worktree_branches_filters_protected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ocwt.commands.completion_cmd.get_current_git_root",
        lambda: Path("/tmp/repo"),
    )
    monkeypatch.setattr(
        "ocwt.commands.completion_cmd.primary_repo_root",
        lambda _git_root: Path("/tmp/repo"),
    )
    monkeypatch.setattr(
        "ocwt.commands.completion_cmd.pick_main_branch", lambda _repo_root: "develop"
    )
    monkeypatch.setattr(
        "ocwt.commands.completion_cmd.list_worktree_branches",
        lambda _repo_root: [
            ("main", Path("/tmp/repo")),
            ("master", Path("/tmp/repo")),
            ("develop", Path("/tmp/repo")),
            ("feat/a", Path("/tmp/repo-wt")),
        ],
    )

    result = completion_worktree_branches()

    assert result == ["feat/a"]
