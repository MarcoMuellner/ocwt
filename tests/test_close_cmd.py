from pathlib import Path

import pytest

from ocwt.commands.close_cmd import (
    _choose_closure_branch,
    _is_protected_branch,
    _render_branch_menu,
)


def test_is_protected_branch() -> None:
    assert _is_protected_branch("main", "develop")
    assert _is_protected_branch("master", "develop")
    assert _is_protected_branch("develop", "develop")
    assert not _is_protected_branch("feat/x", "develop")


def test_render_branch_menu_marks_selected_item() -> None:
    frame = _render_branch_menu(["feat/a", "fix/b"], selected_index=1)

    assert " > fix/b" in frame
    assert "   feat/a" in frame


def test_choose_closure_branch_uses_arrow_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ocwt.commands.close_cmd.list_worktree_branches",
        lambda _repo_root: [("main", Path("/repo")), ("feat/a", Path("/wt"))],
    )
    monkeypatch.setattr("ocwt.commands.close_cmd._choose_branch_with_arrows", lambda _c: "feat/a")

    selected = _choose_closure_branch(Path("/repo"), "main")

    assert selected == "feat/a"
