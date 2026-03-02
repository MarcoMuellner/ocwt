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
    """Run git commands with consistent capture behavior.

    Args:
        repo_root: Repository root used as ``git -C`` target.
        args: Git subcommand arguments.
        check: Whether command failures should raise ``CalledProcessError``.

    Returns:
        Completed process data used by higher-level workflow decisions.
    """
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def get_current_git_root() -> Path | None:
    """Resolve the current working tree root.

    Args:
        None.

    Returns:
        The active git root path, or ``None`` when not inside a git repository.
    """
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
    """Resolve the primary repository root across linked worktrees.

    Args:
        git_root: Current worktree root.

    Returns:
        The shared repository root that owns branch references and common metadata.
    """
    common = run_git(git_root, ["rev-parse", "--git-common-dir"]).stdout.strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (git_root / common_path).resolve()
    return common_path.parent.resolve()


def pick_main_branch(repo_root: Path) -> str:
    """Select the repository base branch used for new worktrees.

    Args:
        repo_root: Repository root where branch references are resolved.

    Returns:
        ``main`` or ``master`` when present, otherwise the current branch name.
    """
    for candidate in ("main", "master"):
        proc = run_git(
            repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"], check=False
        )
        if proc.returncode == 0:
            return candidate
    return run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def worktree_dir_for_branch(repo_root: Path, branch: str, parent_name: str = ".worktrees") -> Path:
    """Build a deterministic filesystem path for a branch worktree.

    Args:
        repo_root: Primary repository root.
        branch: Branch name mapped to a worktree directory.
        parent_name: Parent folder used to hold linked worktrees.

    Returns:
        Absolute path where the branch worktree should live.
    """
    parent = repo_root.parent
    safe = branch.replace("/", "__")
    return (parent / parent_name / safe).resolve()


def list_worktrees(repo_root: Path) -> list[WorktreeEntry]:
    """Read linked worktree metadata from git porcelain output.

    Args:
        repo_root: Repository root used for worktree queries.

    Returns:
        Parsed worktree entries with resolved paths and optional branch names.
    """
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
    """Locate an existing worktree by branch name.

    Args:
        repo_root: Repository root used for worktree enumeration.
        branch: Branch whose worktree path is needed.

    Returns:
        Matching worktree path or ``None`` when no linked worktree is registered.
    """
    for entry in list_worktrees(repo_root):
        if entry.branch == branch:
            return entry.path
    return None


def list_worktree_branches(repo_root: Path) -> list[tuple[str, Path]]:
    """Return branch/path pairs for branch-backed worktrees.

    Args:
        repo_root: Repository root used for worktree enumeration.

    Returns:
        Tuples of ``(branch, path)`` for entries that map to local branches.
    """
    pairs: list[tuple[str, Path]] = []
    for entry in list_worktrees(repo_root):
        if entry.branch:
            pairs.append((entry.branch, entry.path))
    return pairs


def find_branch_for_worktree_path(repo_root: Path, target_path: Path) -> str | None:
    """Resolve a branch name from a concrete worktree directory path.

    Args:
        repo_root: Repository root used for worktree enumeration.
        target_path: Filesystem path provided by the user.

    Returns:
        The matching branch name, or ``None`` when the path is not a registered worktree.
    """
    try:
        resolved_target = target_path.resolve(strict=True)
    except FileNotFoundError:
        return None

    for branch, worktree_path in list_worktree_branches(repo_root):
        if worktree_path.resolve() == resolved_target:
            return branch
    return None


def local_branch_exists(repo_root: Path, branch: str) -> bool:
    """Check whether a local branch reference exists.

    Args:
        repo_root: Repository root where references are queried.
        branch: Branch name to check.

    Returns:
        ``True`` when ``refs/heads/<branch>`` exists locally.
    """
    proc = run_git(
        repo_root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False
    )
    return proc.returncode == 0
