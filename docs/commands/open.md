# `ocwt open`

Open or create a worktree from intent, branch, or file context.

## Usage

```bash
ocwt open [intent-or-branch] [@file ...] [--plan|--no-plan] [--agent <name>] [--editor <cmd|none>]
```

## Common examples

```bash
# Intent
ocwt open "add rate-limit retries"

# Existing branch
ocwt open feat/rate-limit-retries

# File input (auto-attached)
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md

# Force planning once
ocwt open "improve queue backoff" --plan

# Disable planning once
ocwt open "small fix" --no-plan
```

## Notes

- If input matches an existing linked branch worktree, `open` reuses it.
- File inputs are attached automatically and influence branch naming.
- In planning mode, default planning agent is `plan` unless `--agent` is provided.
- If branch generation fails, `open` falls back to a deterministic semantic branch.
