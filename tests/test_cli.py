from typer.testing import CliRunner

from ocwt.cli import app


def test_root_help_displays_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "open" in result.stdout
    assert "close" in result.stdout
    assert "completion" in result.stdout
    assert "config" in result.stdout
