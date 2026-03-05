# `ocwt build`

Open or create a worktree from free-form intent text.

## Usage

```bash
ocwt build [intent] [@file ...] [--plan|--no-plan] [--agent <name>] [--editor <cmd|none>]
```

If `intent` is omitted, `ocwt` prompts for it.

## Common examples

```bash
# Intent text
ocwt build "add rate-limit retries"

# Intent with attached file context
ocwt build "improve delivery summary" @pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md

# Force planning once
ocwt build "improve queue backoff" --plan

# Disable planning once
ocwt build "small fix" --no-plan
```

## Notes

- `build` accepts intent text and optional `@file` mentions.
- In planning mode, default planning agent is `plan` unless `--agent` is provided.
- If branch generation fails, `build` falls back to a deterministic semantic branch.
