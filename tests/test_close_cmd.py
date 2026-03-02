from ocwt.commands.close_cmd import _is_protected_branch


def test_is_protected_branch() -> None:
    assert _is_protected_branch("main", "develop")
    assert _is_protected_branch("master", "develop")
    assert _is_protected_branch("develop", "develop")
    assert not _is_protected_branch("feat/x", "develop")
