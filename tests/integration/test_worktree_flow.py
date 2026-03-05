from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ocwt.commands.close_cmd import run_close
from ocwt.commands.open_cmd import OpenOptions, run_build, run_open


def _git(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_repo(repo_root: Path) -> None:
    try:
        _git(repo_root, "init", "-b", "main")
    except subprocess.CalledProcessError:
        _git(repo_root, "init")
        _git(repo_root, "checkout", "-b", "main")

    (repo_root / "README.md").write_text("test\n", encoding="utf-8")
    _git(repo_root, "add", "README.md")
    _git(repo_root, "commit", "-m", "initial")


def _patch_opencode(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    launched_cwds: list[Path] = []

    def fake_which(binary: str) -> str | None:
        if binary == "opencode":
            return "/usr/bin/opencode"
        return None

    def fake_launch(worktree_dir: Path) -> int:
        launched_cwds.append(worktree_dir.resolve())
        return 0

    monkeypatch.setattr("ocwt.commands.open_cmd.shutil.which", fake_which)
    monkeypatch.setattr("ocwt.commands.open_cmd._launch_opencode", fake_launch)
    return launched_cwds


def test_build_creates_worktree_and_reopen_reuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)
    launched_cwds = _patch_opencode(monkeypatch)

    options = OpenOptions(
        intent_or_branch="feat/reopen-flow",
        at_files=(),
        plan=False,
        agent=None,
        editor=None,
    )

    first_exit = run_build(options)
    second_exit = run_build(options)

    expected_worktree = (repo_root.parent / ".worktrees" / "feat__reopen-flow").resolve()
    assert first_exit == 0
    assert second_exit == 0
    assert expected_worktree.exists()
    assert launched_cwds == [expected_worktree, expected_worktree]

    porcelain = _git(repo_root, "worktree", "list", "--porcelain")
    assert porcelain.count("branch refs/heads/feat/reopen-flow") == 1


def test_open_requires_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)
    _patch_opencode(monkeypatch)

    options = OpenOptions(
        intent_or_branch="pm/missing-file.md",
        at_files=(),
        plan=False,
        agent=None,
        editor=None,
    )

    exit_code = run_open(options)

    assert exit_code == 1


def test_open_reuses_existing_branch_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)
    launched_cwds = _patch_opencode(monkeypatch)

    branch = "feat/otto-self-awareness-transparency"
    existing_worktree = (
        repo_root.parent / ".worktrees" / "feat__otto-self-awareness-transparency"
    ).resolve()
    _git(repo_root, "worktree", "add", "-b", branch, str(existing_worktree), "main")

    exit_code = run_open(
        OpenOptions(
            intent_or_branch=branch,
            at_files=(),
            plan=False,
            agent=None,
            editor=None,
        )
    )

    assert exit_code == 0
    assert launched_cwds == [existing_worktree]


def test_close_removes_worktree_and_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)

    worktree = (repo_root.parent / ".worktrees" / "feat__close-flow").resolve()
    _git(repo_root, "worktree", "add", "-b", "feat/close-flow", str(worktree), "main")

    exit_code = run_close("feat/close-flow")
    assert exit_code == 0
    assert not worktree.exists()

    exists_proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/feat/close-flow",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert exists_proc.returncode != 0


def test_close_protects_main_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)

    exit_code = run_close("main")

    assert exit_code == 1


def test_close_accepts_worktree_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(repo_root)

    worktree = (repo_root.parent / ".worktrees" / "feat__close-by-path").resolve()
    _git(repo_root, "worktree", "add", "-b", "feat/close-by-path", str(worktree), "main")

    exit_code = run_close(str(worktree))

    assert exit_code == 0
    assert not worktree.exists()

    exists_proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/feat/close-by-path",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert exists_proc.returncode != 0
