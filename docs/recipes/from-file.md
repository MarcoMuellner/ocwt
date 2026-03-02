# Recipe: open from file

Use file-first flow when your work starts from a ticket or spec document.

## Command

```bash
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md
```

## What happens

1. file is auto-attached as context
2. branch name includes file context (`epic_011`, `ticket_003`, etc.)
3. worktree is created/reused
4. session starts (planning first if enabled)

## Optional flags

```bash
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md --plan
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md --no-plan
```
