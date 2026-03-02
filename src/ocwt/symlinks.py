from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ocwt.git_ops import run_git


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _backup_existing(path: Path) -> Path:
    backup = Path(f"{path}.local-{_timestamp()}")
    shutil.move(str(path), str(backup))
    return backup


def _symlink_points_to(path: Path, target: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve() == target.resolve()
    except FileNotFoundError:
        return False


def ensure_opencode_symlink(repo_root: Path, worktree_dir: Path) -> list[str]:
    messages: list[str] = []
    if worktree_dir.resolve() == repo_root.resolve():
        return messages

    main_opencode = repo_root / ".opencode"
    wt_opencode = worktree_dir / ".opencode"

    if (
        not main_opencode.exists()
        and not main_opencode.is_symlink()
        and wt_opencode.exists()
        and not wt_opencode.is_symlink()
    ):
        shutil.move(str(wt_opencode), str(main_opencode))
        messages.append(f"Promoted existing worktree .opencode to main: {main_opencode}")

    if main_opencode.exists() and not main_opencode.is_dir():
        raise ValueError(f"Main .opencode exists but is not a directory: {main_opencode}")

    main_opencode.mkdir(parents=True, exist_ok=True)

    if _symlink_points_to(wt_opencode, main_opencode):
        return messages

    if wt_opencode.exists() or wt_opencode.is_symlink():
        backup = _backup_existing(wt_opencode)
        messages.append(f"Moved existing worktree .opencode to: {backup}")

    wt_opencode.symlink_to(main_opencode)
    return messages


def ensure_idea_symlink(repo_root: Path, worktree_dir: Path) -> list[str]:
    messages: list[str] = []
    if worktree_dir.resolve() == repo_root.resolve():
        return messages

    main_idea = repo_root / ".idea"
    wt_idea = worktree_dir / ".idea"

    if not main_idea.exists() and not main_idea.is_symlink():
        return messages

    if main_idea.exists() and not main_idea.is_dir():
        raise ValueError(f"Main .idea exists but is not a directory: {main_idea}")

    if _symlink_points_to(wt_idea, main_idea):
        return messages

    if wt_idea.exists() or wt_idea.is_symlink():
        backup = _backup_existing(wt_idea)
        messages.append(f"Moved existing worktree .idea to: {backup}")

    wt_idea.symlink_to(main_idea)
    return messages


def ensure_env_symlinks(repo_root: Path, worktree_dir: Path) -> list[str]:
    messages: list[str] = []
    if worktree_dir.resolve() == repo_root.resolve():
        return messages

    candidates: list[Path] = []
    exact_env = repo_root / ".env"
    if exact_env.exists() or exact_env.is_symlink():
        candidates.append(exact_env)
    candidates.extend(sorted(repo_root.glob(".env.*"), key=lambda path: path.name))

    for main_env in candidates:
        if not main_env.exists() and not main_env.is_symlink():
            continue
        if main_env.is_dir():
            continue

        rel = main_env.name
        tracked = run_git(
            repo_root,
            ["ls-files", "--error-unmatch", "--", rel],
            check=False,
        )
        if tracked.returncode == 0:
            continue

        wt_env = worktree_dir / rel

        if _symlink_points_to(wt_env, main_env):
            continue

        if wt_env.exists() or wt_env.is_symlink():
            backup = _backup_existing(wt_env)
            messages.append(f"Moved existing worktree {rel} to: {backup}")

        wt_env.symlink_to(main_env)

    return messages
