from ocwt.commands.open_cmd import _find_session_id


def test_find_session_id_from_nested_payload() -> None:
    payload = {
        "type": "run.completed",
        "result": {
            "session": {"id": "ses_123"},
        },
    }

    assert _find_session_id(payload) == "ses_123"


def test_find_session_id_from_event_id() -> None:
    payload = {"event": "session.created", "id": "ses_abc"}

    assert _find_session_id(payload) == "ses_abc"


def test_find_session_id_ignores_non_id_session_string() -> None:
    payload = {"event": "session.created", "session": "created", "id": "not_a_session_id"}

    assert _find_session_id(payload) is None
