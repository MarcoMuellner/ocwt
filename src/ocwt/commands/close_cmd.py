from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from ocwt.git_ops import (
    find_branch_for_worktree_path,
    find_worktree_for_branch,
    get_current_git_root,
    list_worktree_branches,
    local_branch_exists,
    pick_main_branch,
    primary_repo_root,
    run_git,
    worktree_dir_for_branch,
)


def _is_protected_branch(branch: str, base: str) -> bool:
    """Guard base branches from destructive close operations.

    Args:
        branch: Candidate branch requested for closure.
        base: Repository base branch resolved at runtime.

    Returns:
        ``True`` when the branch must be protected from deletion.
    """
    return branch in {"main", "master", base}


def _choose_closure_branch(repo_root: Path, base: str) -> str | None:
    """Collect and interactively select a closeable worktree branch.

    Args:
        repo_root: Repository root used for worktree enumeration.
        base: Repository base branch resolved at runtime.

    Returns:
        Selected branch name or ``None`` when selection cannot be completed.
    """
    candidates = [
        branch
        for branch, _path in list_worktree_branches(repo_root)
        if not _is_protected_branch(branch, base)
    ]

    if not candidates:
        typer.echo("No linked worktree branches available to close.", err=True)
        return None

    typer.echo("Select worktree branch to close:")
    for idx, candidate in enumerate(candidates, start=1):
        typer.echo(f"  {idx}. {candidate}")

    selected = typer.prompt("Choice number or branch name", default="1").strip()
    if selected.isdigit():
        index = int(selected)
        if 1 <= index <= len(candidates):
            return candidates[index - 1]
        typer.echo("Invalid numeric selection.", err=True)
        return None

    if selected in candidates:
        return selected

    typer.echo(f"Unknown branch: {selected}", err=True)
    return None


def run_close(branch_or_path: str | None) -> int:
    """Remove a linked worktree and delete its local branch.

    Args:
        branch_or_path: Optional branch name or worktree path selector.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    current_git_root = get_current_git_root()
    if current_git_root is None:
        typer.echo("Not inside a git repository.", err=True)
        return 1

    repo_root = primary_repo_root(current_git_root)
    base = pick_main_branch(repo_root)

    branch = (branch_or_path or "").strip()
    if not branch:
        selected = _choose_closure_branch(repo_root, base)
        if selected is None:
            return 1
        branch = selected
    else:
        maybe_path = Path(branch).expanduser()
        if maybe_path.exists():
            mapped = find_branch_for_worktree_path(repo_root, maybe_path)
            if mapped is None:
                typer.echo(f"Path is not a registered branch worktree: {maybe_path}", err=True)
                return 1
            branch = mapped

    if _is_protected_branch(branch, base):
        typer.echo(f"Refusing to delete protected branch: {branch}", err=True)
        return 1

    registered_worktree = False
    worktree_dir = find_worktree_for_branch(repo_root, branch)
    if worktree_dir is not None:
        registered_worktree = True
    else:
        worktree_dir = worktree_dir_for_branch(repo_root, branch)

    if worktree_dir.resolve() == repo_root.resolve():
        typer.echo("Refusing to remove the main worktree.", err=True)
        return 1

    typer.echo(f"Repo root : {repo_root}")
    typer.echo(f"Branch    : {branch}")
    typer.echo(f"Worktree  : {worktree_dir}")
    typer.echo()

    if registered_worktree:
        try:
            run_git(repo_root, ["worktree", "remove", str(worktree_dir)])
        except subprocess.CalledProcessError:
            try:
                run_git(repo_root, ["worktree", "remove", "--force", str(worktree_dir)])
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.strip() if exc.stderr else ""
                typer.echo(stderr or "Failed to remove worktree.", err=True)
                return int(exc.returncode) if exc.returncode else 1
    elif worktree_dir.exists():
        typer.echo(
            f"Directory exists but is not registered as a worktree: {worktree_dir}",
            err=True,
        )
        return 1

    if local_branch_exists(repo_root, branch):
        try:
            run_git(repo_root, ["branch", "-D", branch])
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else ""
            typer.echo(stderr or "Failed to delete branch.", err=True)
            return int(exc.returncode) if exc.returncode else 1
    else:
        typer.echo(f"Local branch not found (already deleted): {branch}")

    typer.echo()
    typer.echo("Closed worktree and deleted local branch.")
    typer.echo(f"Main directory: {repo_root}")
    return 0
