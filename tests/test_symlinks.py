from __future__ import annotations

import subprocess
from pathlib import Path

from ocwt.symlinks import ensure_env_symlinks, ensure_opencode_symlink


def test_ensure_opencode_symlink_links_worktree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    worktree_dir = tmp_path / "wt"
    repo_root.mkdir()
    worktree_dir.mkdir()

    messages = ensure_opencode_symlink(repo_root, worktree_dir)

    assert messages == []
    assert (repo_root / ".opencode").is_dir()
    assert (worktree_dir / ".opencode").is_symlink()
    assert (worktree_dir / ".opencode").resolve() == (repo_root / ".opencode").resolve()


def test_ensure_env_symlinks_creates_link_for_untracked_env(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    worktree_dir = tmp_path / "wt"
    repo_root.mkdir()
    worktree_dir.mkdir()
    (repo_root / ".env").write_text("X=1", encoding="utf-8")

    def fake_run_git(
        _repo_root: Path, _args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        return subprocess.CompletedProcess(args=["git"], returncode=1, stdout="", stderr="")

    monkeypatch.setattr("ocwt.symlinks.run_git", fake_run_git)

    messages = ensure_env_symlinks(repo_root, worktree_dir)

    assert messages == []
    assert (worktree_dir / ".env").is_symlink()
    assert (worktree_dir / ".env").resolve() == (repo_root / ".env").resolve()
