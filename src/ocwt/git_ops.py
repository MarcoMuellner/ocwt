from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeEntry:
    path: Path
    branch: str | None


def run_git(
    repo_root: Path, args: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def get_current_git_root() -> Path | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def primary_repo_root(git_root: Path) -> Path:
    common = run_git(git_root, ["rev-parse", "--git-common-dir"]).stdout.strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (git_root / common_path).resolve()
    return common_path.parent.resolve()


def pick_main_branch(repo_root: Path) -> str:
    for candidate in ("main", "master"):
        proc = run_git(
            repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"], check=False
        )
        if proc.returncode == 0:
            return candidate
    return run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def worktree_dir_for_branch(repo_root: Path, branch: str, parent_name: str = ".worktrees") -> Path:
    parent = repo_root.parent
    safe = branch.replace("/", "__")
    return (parent / parent_name / safe).resolve()


def list_worktrees(repo_root: Path) -> list[WorktreeEntry]:
    output = run_git(repo_root, ["worktree", "list", "--porcelain"]).stdout.splitlines()
    entries: list[WorktreeEntry] = []
    current_path: Path | None = None
    current_branch: str | None = None

    for line in output:
        if line.startswith("worktree "):
            if current_path is not None:
                entries.append(WorktreeEntry(path=current_path, branch=current_branch))
            current_path = Path(line.removeprefix("worktree ")).resolve()
            current_branch = None
            continue
        if line.startswith("branch refs/heads/"):
            current_branch = line.removeprefix("branch refs/heads/")

    if current_path is not None:
        entries.append(WorktreeEntry(path=current_path, branch=current_branch))

    return entries


def find_worktree_for_branch(repo_root: Path, branch: str) -> Path | None:
    for entry in list_worktrees(repo_root):
        if entry.branch == branch:
            return entry.path
    return None


def local_branch_exists(repo_root: Path, branch: str) -> bool:
    proc = run_git(
        repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False
    )
    return proc.returncode == 0
