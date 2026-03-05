# ocwt

`ocwt` creates and reuses Git worktrees for implementation work, with optional OpenCode planning before you start coding.

## Install

Requirements:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

Install as a tool:

```bash
uv tool install ocwt
```

Run without installing:

```bash
uvx ocwt --help
```

## Quickstart (60 seconds)

```bash
# Open from an intent
ocwt build "add retry queue metrics"

# Open directly from a ticket/spec file
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md

# Close with interactive branch picker (arrow keys)
ocwt close
```

## Most-used commands

```bash
# Plan first, then continue in the same session
ocwt build "improve delivery retries" --plan

# Override auto-plan for one run
ocwt build "hotfix webhook timeout" --no-plan

# Close a specific branch worktree
ocwt close feat/my-branch

# Config
ocwt config show
ocwt config auto-plan true
ocwt config auto-pull true
```

## Shell completion

```bash
ocwt completion bash > /tmp/ocwt-completion.bash
ocwt completion zsh > /tmp/ocwt-completion.zsh
```

See full docs for setup examples and command details.

## Documentation

- Docs home: `docs/index.md`
- Installation: `docs/installation.md`
- Quickstart: `docs/quickstart.md`
- Commands: `docs/commands/open.md`, `docs/commands/build.md`, `docs/commands/close.md`, `docs/commands/config.md`, `docs/commands/completion.md`
- Concepts: `docs/concepts/planning-mode.md`, `docs/concepts/branch-naming.md`, `docs/concepts/worktrees.md`
- Troubleshooting: `docs/troubleshooting.md`
- FAQ: `docs/faq.md`

## Development

Install dev dependencies:

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

Build docs locally:

```bash
uv run mkdocs serve
uv run mkdocs build --strict
```
