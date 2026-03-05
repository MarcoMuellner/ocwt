# `ocwt open`

Open or create a worktree from a file path, or reopen an existing branch worktree.

## Usage

```bash
ocwt open [file-path|existing-branch] [--plan|--no-plan] [--agent <name>] [--editor <cmd|none>]
```

## Common examples

```bash
# File input (required)
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md

# Reopen an existing worktree by branch name
ocwt open feat/otto-self-awareness-transparency

# Force planning once
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md --plan

# Disable planning once
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md --no-plan
```

## Notes

- If input matches an existing linked branch worktree, `open` reuses it directly.
- Otherwise `open` expects an existing file path and fails fast for missing files.
- File input is attached automatically and influences branch naming.
- In planning mode, default planning agent is `plan` unless `--agent` is provided.
- If branch generation fails, `open` falls back to a deterministic semantic branch.
- For free-form intent text, use [`ocwt build`](build.md).
