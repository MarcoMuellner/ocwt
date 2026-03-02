from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer

from ocwt.branching import fallback_branch, is_valid_prefixed_branch, sanitize_branch, trim
from ocwt.git_ops import (
    find_worktree_for_branch,
    get_current_git_root,
    local_branch_exists,
    pick_main_branch,
    primary_repo_root,
    run_git,
    worktree_dir_for_branch,
)
from ocwt.symlinks import ensure_env_symlinks, ensure_idea_symlink, ensure_opencode_symlink


@dataclass(frozen=True)
class OpenOptions:
    intent_or_branch: str | None
    at_files: tuple[str, ...]
    plan: bool
    agent: str
    editor: str | None


def complete_at_files(incomplete: str) -> list[str]:
    if not incomplete.startswith("@"):
        return []

    wants_at_prefix = incomplete.startswith("@")
    needle = incomplete[1:] if wants_at_prefix else incomplete

    base = Path()
    matches = sorted(base.glob(f"{needle}*"), key=lambda item: item.as_posix())

    output: list[str] = []
    for match in matches:
        text = match.as_posix()
        if match.is_dir() and not text.endswith("/"):
            text = f"{text}/"
        if wants_at_prefix:
            text = f"@{text}"
        output.append(text)
    return output


def _extract_mentions(build_input: str, cli_mentions: tuple[str, ...]) -> list[str]:
    mentions: list[str] = []

    for token in cli_mentions:
        cleaned = trim(token)
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]
        cleaned = cleaned.rstrip(",.;:")
        if cleaned:
            mentions.append(cleaned)

    if mentions:
        return mentions

    for token in build_input.split():
        if token.startswith("@"):
            cleaned = token[1:].rstrip(",.;:")
            if cleaned:
                mentions.append(cleaned)
    return mentions


def _build_branch_prompt(build_desc: str) -> str:
    return (
        "You are generating a git branch name.\n\n"
        "Rules:\n"
        "- Output ONLY the branch name, nothing else (no explanations, no code fences).\n"
        "- Use ONE of these prefixes based on semantics:\n"
        "  feat/, bugfix/, fix/, chore/, docs/, refactor/, test/, perf/\n"
        "- Use lowercase.\n"
        "- Use slashes only for the prefix. Use hyphens in the rest.\n"
        "- Keep it reasonably short.\n\n"
        "Task description:\n"
        f"{build_desc}"
    )


def _generate_branch_name(build_desc: str, attached_files: list[Path], fallback_seed: str) -> str:
    file_args: list[str] = []
    for file_path in attached_files:
        file_args.extend(["--file", str(file_path)])

    prompt = _build_branch_prompt(build_desc)
    proc = subprocess.run(
        ["opencode", "run", *file_args, prompt],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("Failed to generate branch name with opencode.")

    non_empty = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    raw_branch = non_empty[-1] if non_empty else ""
    branch = sanitize_branch(raw_branch)
    if is_valid_prefixed_branch(branch):
        return branch
    return fallback_branch(fallback_seed)


def _launch_opencode(worktree_dir: Path) -> int:
    proc = subprocess.run(["opencode", "."], cwd=worktree_dir, check=False)
    return int(proc.returncode)


def _ensure_repo_symlinks(repo_root: Path, worktree_dir: Path) -> bool:
    try:
        messages = [
            *ensure_opencode_symlink(repo_root, worktree_dir),
            *ensure_idea_symlink(repo_root, worktree_dir),
            *ensure_env_symlinks(repo_root, worktree_dir),
        ]
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        return False

    for message in messages:
        typer.echo(message)
    return True


def run_open(options: OpenOptions) -> int:
    if shutil.which("opencode") is None:
        typer.echo("opencode not found in PATH.", err=True)
        return 1

    build_input = trim(options.intent_or_branch or "")
    if not build_input:
        build_input = trim(typer.prompt("What do you want to build?"))
    if not build_input:
        typer.echo("No description provided. Exiting.", err=True)
        return 1

    current_git_root = get_current_git_root()
    if current_git_root is None:
        typer.echo("Not inside a git repository.", err=True)
        return 1

    repo_root = primary_repo_root(current_git_root)
    mentions = _extract_mentions(build_input, options.at_files)

    existing_direct = None if mentions else find_worktree_for_branch(repo_root, build_input)
    if existing_direct is not None:
        typer.echo(f"Opening existing worktree for branch: {build_input}")
        typer.echo(f"Worktree  : {existing_direct}")
        if not _ensure_repo_symlinks(repo_root, existing_direct):
            return 1
        return _launch_opencode(existing_direct)

    attached_files: list[Path] = []
    fallback_seed = build_input
    build_desc = build_input

    if mentions:
        summary_items: list[str] = []
        for mention in mentions:
            file_path = Path(mention).expanduser()
            if not file_path.is_file():
                typer.echo(f"Mentioned file not found: {file_path}", err=True)
                return 1
            abs_path = file_path.resolve()
            attached_files.append(abs_path)
            summary_items.append(f"- {abs_path}")

        if attached_files:
            fallback_seed = attached_files[0].name
        summary_block = "\n".join(summary_items)
        build_desc = (
            f"Build request: {build_input}\n\nUse these attached files as context:\n{summary_block}"
        )

    branch = ""
    if not mentions:
        candidate = sanitize_branch(build_input)
        if is_valid_prefixed_branch(candidate):
            branch = candidate

    if not branch:
        try:
            branch = _generate_branch_name(build_desc, attached_files, fallback_seed)
        except RuntimeError as exc:
            typer.echo(str(exc), err=True)
            return 1

    base = pick_main_branch(repo_root)

    existing_worktree = find_worktree_for_branch(repo_root, branch)
    if existing_worktree is not None:
        typer.echo(f"Opening existing worktree for branch: {branch}")
        typer.echo(f"Worktree  : {existing_worktree}")
        if not _ensure_repo_symlinks(repo_root, existing_worktree):
            return 1
        return _launch_opencode(existing_worktree)

    worktree_dir = worktree_dir_for_branch(repo_root, branch)
    worktree_dir.parent.mkdir(parents=True, exist_ok=True)

    if worktree_dir.exists():
        typer.echo(f"Worktree directory already exists: {worktree_dir}", err=True)
        typer.echo("Delete it or choose a different branch name.", err=True)
        return 1

    typer.echo(f"Repo root : {repo_root}")
    typer.echo(f"Base      : {base}")
    typer.echo(f"Branch    : {branch}")
    typer.echo(f"Worktree  : {worktree_dir}")
    typer.echo()

    try:
        if local_branch_exists(repo_root, branch):
            run_git(repo_root, ["worktree", "add", str(worktree_dir), branch])
        else:
            run_git(repo_root, ["worktree", "add", "-b", branch, str(worktree_dir), base])
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        typer.echo(stderr or "Failed to create worktree.", err=True)
        return int(exc.returncode) if exc.returncode else 1

    if not _ensure_repo_symlinks(repo_root, worktree_dir):
        return 1

    return _launch_opencode(worktree_dir)
