from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from ocwt.branching import fallback_branch, is_valid_prefixed_branch, sanitize_branch, trim
from ocwt.config_store import OcwtConfig, load_config
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
    agent: str | None
    editor: str | None


SESSION_ID_RE = re.compile(r"^ses_[a-zA-Z0-9]+$")


def complete_at_files(incomplete: str) -> list[str]:
    """Offer ``@file`` completion candidates for intent arguments.

    Args:
        incomplete: Current token fragment being completed.

    Returns:
        Candidate paths prefixed with ``@`` when file completion is active.
    """
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


def complete_files(incomplete: str) -> list[str]:
    """Offer plain file and directory completion candidates.

    Args:
        incomplete: Current token fragment being completed.

    Returns:
        Matching file or directory candidates for direct path completion.
    """
    base = Path()
    matches = sorted(base.glob(f"{incomplete}*"), key=lambda item: item.as_posix())

    output: list[str] = []
    for match in matches:
        text = match.as_posix()
        if match.is_dir() and not text.endswith("/"):
            text = f"{text}/"
        output.append(text)
    return output


def _extract_mentions(build_input: str, cli_mentions: tuple[str, ...]) -> list[str]:
    """Collect explicit file mentions from CLI args or inline intent text.

    Args:
        build_input: Raw open intent string.
        cli_mentions: Parsed positional mention tokens.

    Returns:
        Normalized mention tokens without leading ``@`` and trailing punctuation.
    """
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


def _resolve_direct_file_input(build_input: str) -> Path | None:
    """Detect when the primary open argument is a direct file path.

    Args:
        build_input: User-provided open argument.

    Returns:
        Absolute file path when input resolves to an existing file, otherwise ``None``.
    """
    candidate = Path(build_input).expanduser()
    try:
        if candidate.is_file():
            return candidate.resolve()
    except OSError:
        return None
    return None


def _file_context_slug(file_path: Path) -> str:
    """Derive branch-safe context from file parent and stem.

    Args:
        file_path: Context file used to seed branch naming.

    Returns:
        Hyphenated slug preserving key identifiers from path context.
    """
    parent_name = file_path.parent.name.strip()
    stem = file_path.stem.strip()

    parent_slug = sanitize_branch(parent_name).replace("/", "-").strip("-") if parent_name else ""
    stem_slug = sanitize_branch(stem).replace("/", "-").strip("-") if stem else ""

    parts = [part for part in (parent_slug, stem_slug) if part]
    if not parts:
        return ""
    return "-".join(parts)


def _ensure_branch_has_file_slug(branch: str, file_slug: str) -> str:
    """Append file context to semantic branches when missing.

    Args:
        branch: Semantic branch candidate.
        file_slug: File-derived context slug.

    Returns:
        Updated branch when suffix can be safely enriched.
    """
    normalized_slug = sanitize_branch(file_slug).replace("/", "-").strip("-")
    if not normalized_slug:
        return branch
    if not is_valid_prefixed_branch(branch):
        return branch

    prefix, suffix = branch.split("/", 1)
    if normalized_slug in suffix:
        return branch

    candidate = sanitize_branch(f"{prefix}/{suffix}-{normalized_slug}")
    if is_valid_prefixed_branch(candidate):
        return candidate
    return branch


def _build_branch_prompt(build_desc: str) -> str:
    """Build a constrained prompt for semantic branch generation.

    Args:
        build_desc: User intent enriched with attached file context.

    Returns:
        Prompt text that steers ``opencode`` toward valid branch output.
    """
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


def _generate_branch_name(
    build_desc: str,
    attached_files: list[Path],
    fallback_seed: str,
    agent: str,
) -> str:
    """Ask ``opencode`` for a semantic branch and validate the result.

    Args:
        build_desc: Intent text sent to ``opencode``.
        attached_files: Files attached as context for branch inference.
        fallback_seed: Deterministic seed used when model output is invalid.
        agent: Agent name used for generation.

    Returns:
        Valid semantic branch name, or deterministic fallback when needed.
    """
    file_args: list[str] = []
    for file_path in attached_files:
        file_args.extend(["--file", str(file_path)])

    prompt = _build_branch_prompt(build_desc)
    proc = subprocess.run(
        ["opencode", "run", "--agent", agent, *file_args, "--", prompt],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() if proc.stderr else ""
        stdout = proc.stdout.strip() if proc.stdout else ""
        detail = stderr or stdout or "opencode run returned a non-zero exit code"
        raise RuntimeError(f"Failed to generate branch name with opencode: {detail}")

    non_empty = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    raw_branch = non_empty[-1] if non_empty else ""
    branch = sanitize_branch(raw_branch)
    if is_valid_prefixed_branch(branch):
        return branch
    return fallback_branch(fallback_seed)


def _find_session_id(value: object) -> str | None:
    """Extract an ``opencode`` session id from nested JSON events.

    Args:
        value: Parsed JSON event object or collection.

    Returns:
        Session id when present in supported event shapes, else ``None``.
    """
    if isinstance(value, dict):
        for key in ("session_id", "sessionId", "sessionID"):
            for key_obj, candidate in value.items():
                if key_obj == key and isinstance(candidate, str) and SESSION_ID_RE.match(candidate):
                    return candidate

        for key_obj, candidate in value.items():
            if (
                key_obj == "session"
                and isinstance(candidate, str)
                and SESSION_ID_RE.match(candidate)
            ):
                return candidate

        session_obj: object | None = None
        for key_obj, candidate in value.items():
            if key_obj == "session":
                session_obj = candidate
                break

        if isinstance(session_obj, dict):
            for key_obj, candidate in session_obj.items():
                if (
                    key_obj == "id"
                    and isinstance(candidate, str)
                    and SESSION_ID_RE.match(candidate)
                ):
                    return candidate

        event_obj: object | None = None
        id_obj: object | None = None
        for key_obj, candidate in value.items():
            if event_obj is None and key_obj in {"type", "event"}:
                event_obj = candidate
            elif key_obj == "id" and id_obj is None:
                id_obj = candidate

        if (
            isinstance(event_obj, str)
            and "session" in event_obj.lower()
            and isinstance(id_obj, str)
            and SESSION_ID_RE.match(id_obj)
        ):
            return id_obj

        for nested in value.values():
            nested_id = _find_session_id(nested)
            if nested_id:
                return nested_id
        return None

    if isinstance(value, list):
        for nested in value:
            nested_id = _find_session_id(nested)
            if nested_id:
                return nested_id
    return None


def _summarize_plan_event(payload: object) -> str | None:
    """Convert raw planning events into concise status text.

    Args:
        payload: Parsed planning event payload.

    Returns:
        Human-readable status text for live terminal updates, or ``None``.
    """
    if not isinstance(payload, dict):
        return None

    event_type_obj: object | None = None
    for key_obj, candidate in payload.items():
        if key_obj == "type":
            event_type_obj = candidate
            break
    event_type = event_type_obj if isinstance(event_type_obj, str) else ""

    if event_type == "step_start":
        return "Planning: analyzing context"

    if event_type == "step_finish":
        return "Planning: reasoning over collected data"

    if event_type == "tool_use":
        part_obj: object | None = None
        for key_obj, candidate in payload.items():
            if key_obj == "part":
                part_obj = candidate
                break
        if not isinstance(part_obj, dict):
            return "Planning: using tool"

        tool_obj: object | None = None
        state_obj: object | None = None
        for key_obj, candidate in part_obj.items():
            if key_obj == "tool":
                tool_obj = candidate
            elif key_obj == "state":
                state_obj = candidate
        tool = tool_obj if isinstance(tool_obj, str) else "tool"

        if not isinstance(state_obj, dict):
            return f"Planning: {tool}"

        input_obj: object | None = None
        for key_obj, candidate in state_obj.items():
            if key_obj == "input":
                input_obj = candidate
                break
        if isinstance(input_obj, dict):
            for key in ("filePath", "pattern", "path"):
                for key_obj, value in input_obj.items():
                    if key_obj == key and isinstance(value, str) and value.strip():
                        short = value.strip()
                        if len(short) > 56:
                            short = f"...{short[-53:]}"
                        return f"Planning: {tool} -> {short}"

        return f"Planning: {tool}"

    return None


def _print_live_status(text: str, *, final: bool = False) -> None:
    """Render a single-line live status update in the terminal.

    Args:
        text: Status text to display.
        final: Whether to finalize output with a newline.

    Returns:
        None.
    """
    width = shutil.get_terminal_size(fallback=(100, 20)).columns
    max_len = max(10, width - 2)
    display = text if len(text) <= max_len else f"{text[: max_len - 1]}..."
    sys.stdout.write(f"\r{display.ljust(max_len)}")
    if final:
        sys.stdout.write("\n")
    sys.stdout.flush()


def _plan_and_launch(
    worktree_dir: Path,
    build_desc: str,
    attached_files: list[Path],
    agent: str,
) -> int:
    """Run one-shot planning then continue in an interactive session.

    Args:
        worktree_dir: Working directory for planning and follow-up session.
        build_desc: Planning request text.
        attached_files: Context files to attach to planning request.
        agent: Planning agent identifier.

    Returns:
        Process-style exit code from interactive ``opencode`` continuation.
    """
    typer.echo()
    typer.echo("==============================")
    typer.echo("  Planning session started")
    typer.echo("==============================")

    file_args: list[str] = []
    for file_path in attached_files:
        file_args.extend(["--file", str(file_path)])

    session_id: str | None = None
    proc = subprocess.Popen(
        [
            "opencode",
            "run",
            "--agent",
            agent,
            "--format",
            "json",
            *file_args,
            "--",
            build_desc,
        ],
        cwd=worktree_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    last_status = "Planning: initializing"
    _print_live_status(last_status)

    assert proc.stdout is not None
    for line in proc.stdout:
        stripped = line.rstrip("\n")
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            last_status = f"Planning: {stripped}"
            _print_live_status(last_status)
            continue

        summary = _summarize_plan_event(payload)
        if summary:
            last_status = summary
            _print_live_status(last_status)

        discovered = _find_session_id(payload)
        if discovered:
            session_id = discovered

    returncode = proc.wait()
    _print_live_status(last_status, final=True)
    if returncode != 0:
        typer.echo("Planning step failed.", err=True)
        return int(returncode)

    if session_id:
        interactive = subprocess.run(
            ["opencode", "--session", session_id, str(worktree_dir), "--agent", agent],
            check=False,
        )
        return int(interactive.returncode)

    typer.echo(
        "Warning: could not parse planning session id; falling back to `opencode --continue`.",
        err=True,
    )
    interactive = subprocess.run(
        ["opencode", "--continue", str(worktree_dir), "--agent", agent],
        check=False,
    )
    return int(interactive.returncode)


def _launch_opencode(worktree_dir: Path) -> int:
    """Launch interactive ``opencode`` in a worktree directory.

    Args:
        worktree_dir: Target working directory for interactive session.

    Returns:
        Process-style exit code from ``opencode``.
    """
    proc = subprocess.run(["opencode", "."], cwd=worktree_dir, check=False)
    return int(proc.returncode)


def _load_runtime_config() -> OcwtConfig | None:
    """Load config with user-facing error handling for CLI flows.

    Args:
        None.

    Returns:
        Parsed config object or ``None`` when config is invalid.
    """
    try:
        return load_config()
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        return None


def _ensure_repo_symlinks(repo_root: Path, worktree_dir: Path) -> bool:
    """Apply configured symlink policies for a linked worktree.

    Args:
        repo_root: Primary repository root.
        worktree_dir: Linked worktree that should inherit shared files.

    Returns:
        ``True`` when symlink setup succeeds.
    """
    config = _load_runtime_config()
    if config is None:
        return False
    try:
        messages: list[str] = []
        if config.symlink_opencode:
            messages.extend(ensure_opencode_symlink(repo_root, worktree_dir))
        if config.symlink_idea:
            messages.extend(ensure_idea_symlink(repo_root, worktree_dir))
        if config.symlink_env:
            messages.extend(ensure_env_symlinks(repo_root, worktree_dir))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        return False

    for message in messages:
        typer.echo(message)
    return True


def _open_session(
    worktree_dir: Path,
    build_desc: str,
    attached_files: list[Path],
    plan_mode: bool,
    agent: str,
) -> int:
    """Dispatch to planning or direct interactive mode.

    Args:
        worktree_dir: Target worktree directory.
        build_desc: Intent text used in planning mode.
        attached_files: Context files used in planning mode.
        plan_mode: Whether planning mode is enabled.
        agent: Agent identifier for planning or interactive handoff.

    Returns:
        Process-style exit code from the selected session flow.
    """
    if plan_mode:
        return _plan_and_launch(worktree_dir, build_desc, attached_files, agent)
    return _launch_opencode(worktree_dir)


def _resolve_editor_behavior(options: OpenOptions, config: OcwtConfig) -> tuple[str | None, bool]:
    """Resolve effective editor command and launch policy for one invocation.

    Args:
        options: Per-command overrides from CLI flags.
        config: Persisted config defaults.

    Returns:
        Tuple of ``(editor_command, should_open)``.
    """
    if options.editor is not None:
        raw = options.editor.strip()
        if raw.lower() == "none" or not raw:
            return (None, False)
        return (raw, True)

    editor = config.editor.strip()
    if editor.lower() == "none" or not editor:
        return (None, False)
    return (editor, config.open_editor)


def _launch_editor_if_enabled(worktree_dir: Path, editor: str | None, should_open: bool) -> None:
    """Start editor process when launch policy is enabled.

    Args:
        worktree_dir: Worktree path opened in the editor.
        editor: Effective editor command.
        should_open: Whether editor launch is enabled for this invocation.

    Returns:
        None.
    """
    if not should_open or editor is None:
        return

    if "/" not in editor and shutil.which(editor) is None:
        typer.echo(f"Warning: editor not found in PATH: {editor}", err=True)
        return

    try:
        subprocess.Popen([editor, str(worktree_dir)], cwd=worktree_dir)
    except OSError as exc:
        typer.echo(f"Warning: failed to launch editor '{editor}': {exc}", err=True)


def _pull_repo_if_enabled(repo_root: Path, auto_pull: bool, base: str) -> bool:
    """Run a fast-forward pull gate before creating new worktrees.

    Args:
        repo_root: Repository root where pull should execute.
        auto_pull: Whether pull gate is enabled.
        base: Base branch that should be current before pulling.

    Returns:
        ``True`` when pull gate passes or is disabled.
    """
    if not auto_pull:
        return True

    current_branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
    branch_name = current_branch.stdout.strip() if current_branch.stdout else ""
    if branch_name != base:
        typer.echo(
            f"Auto-pull requires '{base}' checked out in the main repo. "
            f"Current branch is '{branch_name or 'unknown'}'.",
            err=True,
        )
        return False

    typer.echo("Auto-pull enabled: pulling latest changes before creating worktree...")
    try:
        run_git(repo_root, ["pull", "--ff-only"])
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        typer.echo(stderr or "Auto-pull failed.", err=True)
        return False
    return True


def _run_open_flow(options: OpenOptions, *, require_existing_file: bool) -> int:
    """Run shared open/build workflow with mode-specific input gating.

    Args:
        options: Parsed command options.
        require_existing_file: Whether primary input must resolve to a real file.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    if shutil.which("opencode") is None:
        typer.echo("opencode not found in PATH.", err=True)
        return 1

    build_input = trim(options.intent_or_branch or "")
    if not build_input:
        if require_existing_file:
            build_input = trim(typer.prompt("Which file path or existing branch should be opened?"))
        else:
            build_input = trim(typer.prompt("What do you want to build?"))
    if not build_input:
        typer.echo("No description provided. Exiting.", err=True)
        return 1

    direct_file_input = _resolve_direct_file_input(build_input)

    current_git_root = get_current_git_root()
    if current_git_root is None:
        typer.echo("Not inside a git repository.", err=True)
        return 1

    repo_root = primary_repo_root(current_git_root)
    config = _load_runtime_config()
    if config is None:
        return 1
    effective_agent = options.agent or config.agent
    planning_agent = options.agent or "plan"
    plan_mode = options.plan or config.auto_plan
    effective_editor, should_open_editor = _resolve_editor_behavior(options, config)
    mentions = _extract_mentions(build_input, options.at_files)
    if direct_file_input is not None and str(direct_file_input) not in mentions:
        mentions.insert(0, str(direct_file_input))

    existing_direct = None if mentions else find_worktree_for_branch(repo_root, build_input)
    if existing_direct is not None:
        typer.echo(f"Opening existing worktree for branch: {build_input}")
        typer.echo(f"Worktree  : {existing_direct}")
        if not _ensure_repo_symlinks(repo_root, existing_direct):
            return 1
        _launch_editor_if_enabled(existing_direct, effective_editor, should_open_editor)
        return _open_session(
            existing_direct,
            build_desc=build_input,
            attached_files=[],
            plan_mode=plan_mode,
            agent=planning_agent,
        )

    if require_existing_file and direct_file_input is None:
        typer.echo(f"File not found: {build_input}", err=True)
        return 1

    attached_files: list[Path] = []
    fallback_seed = build_input
    build_desc = build_input
    file_slug = ""

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
            file_slug = _file_context_slug(attached_files[0])
            fallback_seed = file_slug or attached_files[0].stem
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
            branch = _generate_branch_name(
                build_desc, attached_files, fallback_seed, effective_agent
            )
        except RuntimeError as exc:
            typer.echo(str(exc), err=True)
            branch = fallback_branch(fallback_seed)
            typer.echo(f"Using fallback branch: {branch}", err=True)

    if file_slug:
        branch = _ensure_branch_has_file_slug(branch, file_slug)

    base = pick_main_branch(repo_root)

    existing_worktree = find_worktree_for_branch(repo_root, branch)
    if existing_worktree is not None:
        typer.echo(f"Opening existing worktree for branch: {branch}")
        typer.echo(f"Worktree  : {existing_worktree}")
        if not _ensure_repo_symlinks(repo_root, existing_worktree):
            return 1
        _launch_editor_if_enabled(existing_worktree, effective_editor, should_open_editor)
        return _open_session(
            existing_worktree,
            build_desc=build_desc,
            attached_files=attached_files,
            plan_mode=plan_mode,
            agent=planning_agent,
        )

    worktree_dir = worktree_dir_for_branch(repo_root, branch, config.worktree_parent)
    worktree_dir.parent.mkdir(parents=True, exist_ok=True)

    if worktree_dir.exists():
        typer.echo(f"Worktree directory already exists: {worktree_dir}", err=True)
        typer.echo("Delete it or choose a different branch name.", err=True)
        return 1

    if not _pull_repo_if_enabled(repo_root, config.auto_pull, base):
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

    _launch_editor_if_enabled(worktree_dir, effective_editor, should_open_editor)

    return _open_session(
        worktree_dir,
        build_desc=build_desc,
        attached_files=attached_files,
        plan_mode=plan_mode,
        agent=planning_agent,
    )


def run_open(options: OpenOptions) -> int:
    """Open flow that accepts only existing file inputs.

    Args:
        options: Parsed open command options.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return _run_open_flow(options, require_existing_file=True)


def run_build(options: OpenOptions) -> int:
    """Build flow that accepts free-form intent text.

    Args:
        options: Parsed build command options.

    Returns:
        Process-style exit code for CLI dispatch.
    """
    return _run_open_flow(options, require_existing_file=False)
