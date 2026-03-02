from pathlib import Path

from ocwt.commands.open_cmd import complete_at_files


def test_complete_at_files_keeps_at_prefix(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "spec.md"
    file_path.write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    results = complete_at_files("@sp")

    assert "@spec.md" in results
