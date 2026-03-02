# Recipe: team workflow

Use `ocwt` as a consistent local branch/worktree workflow.

## Suggested baseline

```bash
ocwt config auto-plan true
ocwt config auto-pull true
ocwt config open-editor true
ocwt config editor zed
```

## Daily flow

```bash
# start work
ocwt open "implement retry queue"

# reopen same branch later
ocwt open feat/implement-retry-queue

# close when done
ocwt close
```

## Notes

- `auto_pull` uses `git pull --ff-only`; it fails fast if pull is not clean.
- `--no-plan` disables planning for one run even when `auto_plan=true`.
