import subprocess
from pathlib import Path

import pytest

from ocwt.commands.open_cmd import (
    OpenOptions,
    _ensure_branch_has_file_slug,
    _file_context_slug,
    _pull_repo_if_enabled,
    _resolve_direct_file_input,
    run_open,
)
from ocwt.config_store import OcwtConfig


def test_file_context_slug_uses_parent_and_stem() -> None:
    file_path = Path("epic_payment/ticket_refund_flow.md")

    assert _file_context_slug(file_path) == "epic-payment-ticket-refund-flow"


def test_file_context_slug_keeps_numeric_identifiers() -> None:
    file_path = Path("epic_123/ticket_456_refund.md")

    assert _file_context_slug(file_path) == "epic-123-ticket-456-refund"


def test_resolve_direct_file_input_ignores_too_long_path() -> None:
    long_intent = "x" * 4096

    resolved = _resolve_direct_file_input(long_intent)

    assert resolved is None


def test_ensure_branch_has_file_slug_appends_slug() -> None:
    branch = _ensure_branch_has_file_slug("feat/add-refund", "epic-payment-ticket-refund-flow")

    assert branch == "feat/add-refund-epic-payment-ticket-refund-flow"


def test_ensure_branch_has_file_slug_keeps_existing_slug() -> None:
    branch = _ensure_branch_has_file_slug(
        "fix/refund-crash-epic-payment-ticket-refund-flow",
        "epic-payment-ticket-refund-flow",
    )

    assert branch == "fix/refund-crash-epic-payment-ticket-refund-flow"


def test_ensure_branch_has_file_slug_preserves_numbers() -> None:
    branch = _ensure_branch_has_file_slug("feat/refund-flow", "epic-123-ticket-456-refund")

    assert branch == "feat/refund-flow-epic-123-ticket-456-refund"


def test_open_plan_auto_injects_direct_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_file = repo_root / "epic_payment" / "ticket_refund.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("details", encoding="utf-8")

    captured: dict[str, object] = {}

    monkeypatch.setattr("ocwt.commands.open_cmd.shutil.which", lambda _name: "/usr/bin/opencode")
    monkeypatch.setattr("ocwt.commands.open_cmd.get_current_git_root", lambda: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.primary_repo_root", lambda _root: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.find_worktree_for_branch", lambda *_args: None)
    monkeypatch.setattr("ocwt.commands.open_cmd.pick_main_branch", lambda _repo_root: "main")
    monkeypatch.setattr("ocwt.commands.open_cmd.local_branch_exists", lambda *_args: False)
    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("ocwt.commands.open_cmd._ensure_repo_symlinks", lambda *_args: True)
    monkeypatch.setattr("ocwt.commands.open_cmd._launch_editor_if_enabled", lambda *_args: None)
    monkeypatch.setattr(
        "ocwt.commands.open_cmd._load_runtime_config",
        lambda: OcwtConfig(
            editor="none",
            open_editor=False,
            agent="build",
            auto_plan=False,
            auto_pull=False,
            prompt_file=None,
            branch_prompt_file=None,
            worktree_parent=".worktrees",
            symlink_opencode=True,
            symlink_idea=True,
            symlink_env=True,
        ),
    )
    monkeypatch.setattr(
        "ocwt.commands.open_cmd._generate_branch_name",
        lambda *_args: "feat/refund-flow",
    )

    def fake_open_session(
        _worktree_dir: Path,
        build_desc: str,
        attached_files: list[Path],
        plan_mode: bool,
        agent: str,
    ) -> int:
        captured["build_desc"] = build_desc
        captured["attached_files"] = attached_files
        captured["plan_mode"] = plan_mode
        captured["agent"] = agent
        return 0

    monkeypatch.setattr("ocwt.commands.open_cmd._open_session", fake_open_session)

    result = run_open(
        OpenOptions(
            intent_or_branch=str(target_file),
            at_files=(),
            plan=True,
            agent=None,
            editor=None,
        )
    )

    assert result == 0
    assert captured["plan_mode"] is True
    assert captured["agent"] == "plan"
    attached = captured["attached_files"]
    assert isinstance(attached, list)
    assert attached == [target_file.resolve()]
    assert "Use these attached files as context" in str(captured["build_desc"])


def test_pull_repo_if_enabled_runs_pull(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run_git(_repo_root: Path, args: list[str], check: bool = True) -> object:
        _ = check
        calls.append(args)
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout="main\n", stderr=""
            )
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", fake_run_git)

    ok = _pull_repo_if_enabled(tmp_path, auto_pull=True, base="main")

    assert ok is True
    assert calls == [["rev-parse", "--abbrev-ref", "HEAD"], ["pull", "--ff-only"]]


def test_pull_repo_if_enabled_fails_on_git_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run_git(_repo_root: Path, args: list[str], check: bool = True) -> object:
        _ = check
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout="main\n", stderr=""
            )
        raise subprocess.CalledProcessError(returncode=1, cmd=["git"], stderr="pull failed")

    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", fake_run_git)

    ok = _pull_repo_if_enabled(tmp_path, auto_pull=True, base="main")

    assert ok is False


def test_pull_repo_if_enabled_requires_base_checked_out(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_git(_repo_root: Path, args: list[str], check: bool = True) -> object:
        _ = check
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout="feat/x\n", stderr=""
            )
        raise AssertionError(f"Unexpected git command: {args!r}")

    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", fake_run_git)

    ok = _pull_repo_if_enabled(tmp_path, auto_pull=True, base="main")

    assert ok is False


def test_open_uses_fallback_branch_when_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_file = repo_root / "epic_011" / "ticket_003_delivery_status.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("details", encoding="utf-8")

    captured: dict[str, object] = {}

    monkeypatch.setattr("ocwt.commands.open_cmd.shutil.which", lambda _name: "/usr/bin/opencode")
    monkeypatch.setattr("ocwt.commands.open_cmd.get_current_git_root", lambda: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.primary_repo_root", lambda _root: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.find_worktree_for_branch", lambda *_args: None)
    monkeypatch.setattr("ocwt.commands.open_cmd.pick_main_branch", lambda _repo_root: "main")
    monkeypatch.setattr("ocwt.commands.open_cmd.local_branch_exists", lambda *_args: False)
    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("ocwt.commands.open_cmd._ensure_repo_symlinks", lambda *_args: True)
    monkeypatch.setattr("ocwt.commands.open_cmd._launch_editor_if_enabled", lambda *_args: None)
    monkeypatch.setattr(
        "ocwt.commands.open_cmd._load_runtime_config",
        lambda: OcwtConfig(
            editor="none",
            open_editor=False,
            agent="build",
            auto_plan=False,
            auto_pull=False,
            prompt_file=None,
            branch_prompt_file=None,
            worktree_parent=".worktrees",
            symlink_opencode=True,
            symlink_idea=True,
            symlink_env=True,
        ),
    )

    def fake_generate(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("opencode failure")

    monkeypatch.setattr("ocwt.commands.open_cmd._generate_branch_name", fake_generate)

    def fake_open_session(
        worktree_dir: Path,
        build_desc: str,
        attached_files: list[Path],
        plan_mode: bool,
        agent: str,
    ) -> int:
        captured["worktree_dir"] = worktree_dir
        captured["build_desc"] = build_desc
        captured["attached_files"] = attached_files
        captured["plan_mode"] = plan_mode
        captured["agent"] = agent
        return 0

    monkeypatch.setattr("ocwt.commands.open_cmd._open_session", fake_open_session)

    result = run_open(
        OpenOptions(
            intent_or_branch=str(target_file),
            at_files=(),
            plan=False,
            agent=None,
            editor=None,
        )
    )

    assert result == 0
    worktree_dir = captured.get("worktree_dir")
    assert isinstance(worktree_dir, Path)
    assert worktree_dir.name.endswith("epic-011-ticket-003-delivery-status")


def test_open_plan_allows_explicit_agent_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_file = repo_root / "epic_011" / "ticket_003.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("details", encoding="utf-8")

    captured: dict[str, object] = {}

    monkeypatch.setattr("ocwt.commands.open_cmd.shutil.which", lambda _name: "/usr/bin/opencode")
    monkeypatch.setattr("ocwt.commands.open_cmd.get_current_git_root", lambda: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.primary_repo_root", lambda _root: repo_root)
    monkeypatch.setattr("ocwt.commands.open_cmd.find_worktree_for_branch", lambda *_args: None)
    monkeypatch.setattr("ocwt.commands.open_cmd.pick_main_branch", lambda _repo_root: "main")
    monkeypatch.setattr("ocwt.commands.open_cmd.local_branch_exists", lambda *_args: False)
    monkeypatch.setattr("ocwt.commands.open_cmd.run_git", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("ocwt.commands.open_cmd._ensure_repo_symlinks", lambda *_args: True)
    monkeypatch.setattr("ocwt.commands.open_cmd._launch_editor_if_enabled", lambda *_args: None)
    monkeypatch.setattr(
        "ocwt.commands.open_cmd._load_runtime_config",
        lambda: OcwtConfig(
            editor="none",
            open_editor=False,
            agent="build",
            auto_plan=False,
            auto_pull=False,
            prompt_file=None,
            branch_prompt_file=None,
            worktree_parent=".worktrees",
            symlink_opencode=True,
            symlink_idea=True,
            symlink_env=True,
        ),
    )
    monkeypatch.setattr("ocwt.commands.open_cmd._generate_branch_name", lambda *_args: "feat/x")

    def fake_open_session(
        worktree_dir: Path,
        build_desc: str,
        attached_files: list[Path],
        plan_mode: bool,
        agent: str,
    ) -> int:
        _ = (worktree_dir, build_desc, attached_files, plan_mode)
        captured["agent"] = agent
        return 0

    monkeypatch.setattr("ocwt.commands.open_cmd._open_session", fake_open_session)

    result = run_open(
        OpenOptions(
            intent_or_branch=str(target_file),
            at_files=(),
            plan=True,
            agent="design",
            editor=None,
        )
    )

    assert result == 0
    assert captured["agent"] == "design"
