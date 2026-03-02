from __future__ import annotations

import subprocess
import sys
import termios
import tty
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


def _read_menu_key() -> str:
    """Read one keyboard action for interactive branch selection.

    Args:
        None.

    Returns:
        Normalized key token used by the menu loop.
    """
    first = sys.stdin.read(1)
    if first in {"\r", "\n"}:
        return "ENTER"
    if first == "\x03":
        return "CTRL_C"
    if first != "\x1b":
        return "OTHER"

    second = sys.stdin.read(1)
    if second != "[":
        return "ESC"
    third = sys.stdin.read(1)
    if third == "A":
        return "UP"
    if third == "B":
        return "DOWN"
    return "ESC"


def _render_branch_menu(candidates: list[str], selected_index: int) -> str:
    """Render a compact interactive menu for branch selection.

    Args:
        candidates: Closeable branch names.
        selected_index: Currently highlighted option index.

    Returns:
        Full terminal frame text for the current menu state.
    """
    lines = [
        "Select worktree branch to close",
        "Use arrow keys and press Enter",
        "",
    ]
    for index, candidate in enumerate(candidates):
        marker = ">" if index == selected_index else " "
        lines.append(f" {marker} {candidate}")
    lines.append("")
    lines.append("Press Esc to cancel")
    return "\n".join(lines)


def _choose_branch_with_arrows(candidates: list[str]) -> str | None:
    """Collect a branch choice through an arrow-key terminal menu.

    Args:
        candidates: Closeable branch names.

    Returns:
        Selected branch name, or ``None`` when selection is cancelled.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    selected_index = 0
    fd = sys.stdin.fileno()

    try:
        original = termios.tcgetattr(fd)
    except termios.error:
        return None

    try:
        tty.setcbreak(fd)
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()

        while True:
            frame = _render_branch_menu(candidates, selected_index)
            sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write(frame)
            sys.stdout.flush()

            key = _read_menu_key()
            if key == "UP":
                selected_index = (selected_index - 1) % len(candidates)
                continue
            if key == "DOWN":
                selected_index = (selected_index + 1) % len(candidates)
                continue
            if key == "ENTER":
                return candidates[selected_index]
            if key in {"ESC", "CTRL_C"}:
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


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

    choice = _choose_branch_with_arrows(candidates)
    if choice is not None:
        return choice

    if sys.stdin.isatty() and sys.stdout.isatty():
        typer.echo("Selection cancelled.", err=True)
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
