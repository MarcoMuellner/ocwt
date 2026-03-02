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
```

Completion:

```bash
uv run ocwt --show-completion bash
uv run ocwt --show-completion zsh
```
