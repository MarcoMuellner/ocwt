from ocwt.commands.open_cmd import OpenOptions, _resolve_editor_behavior
from ocwt.config_store import default_config


def test_resolve_editor_behavior_prefers_cli_override() -> None:
    config = default_config()
    options = OpenOptions(
        intent_or_branch="x",
        at_files=(),
        plan=False,
        agent=None,
        editor="zed",
    )

    editor, should_open = _resolve_editor_behavior(options, config)

    assert editor == "zed"
    assert should_open is True


def test_resolve_editor_behavior_none_disables_open() -> None:
    config = default_config()
    options = OpenOptions(
        intent_or_branch="x",
        at_files=(),
        plan=False,
        agent=None,
        editor="none",
    )

    editor, should_open = _resolve_editor_behavior(options, config)

    assert editor is None
    assert should_open is False
