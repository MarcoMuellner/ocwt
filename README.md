# ocwt

ocwt spins up Git worktrees fast, plans with OpenCode, and then drops into build mode.

## Development

Requirements:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

Install dependencies:

```bash
uv sync --group dev
```

Run checks:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

Run the CLI:

```bash
uv run ocwt --help
uv run ocwt open "add config command" --plan
```

Config:

```bash
uv run ocwt config show
uv run ocwt config get editor
uv run ocwt config set editor zed
uv run ocwt config reset
```

Completion:

```bash
uv run ocwt completion bash
uv run ocwt completion zsh
```
