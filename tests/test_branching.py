from ocwt.branching import fallback_branch, is_valid_prefixed_branch, sanitize_branch


def test_sanitize_branch_normalizes_llm_noise() -> None:
    value = sanitize_branch('"```Feat/New Branch__Name!!!```"')
    assert value == "feat/new-branch-name"


def test_valid_prefixed_branch() -> None:
    assert is_valid_prefixed_branch("feat/add-tests")
    assert not is_valid_prefixed_branch("feature/add-tests")


def test_fallback_branch_never_empty() -> None:
    assert fallback_branch("!!!") == "feat/worktree"
