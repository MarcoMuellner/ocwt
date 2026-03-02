# Quickstart

## 1) Open from intent

```bash
ocwt open "add retry queue metrics"
```

This creates or reuses a worktree and starts an OpenCode session there.

## 2) Open from a ticket/spec file

```bash
ocwt open pm/epic_011/ticket_003_delivery_status_mirroring_and_pruning.md
```

The file is auto-attached as context. Branch naming also includes file context.

## 3) Plan first

```bash
ocwt open "improve delivery retries" --plan
```

Planning uses the `plan` agent by default, then continues interactively.

## 4) Override auto-plan once

```bash
ocwt open "hotfix webhook timeout" --no-plan
```

## 5) Close worktree

```bash
ocwt close
```

Use arrow keys to choose a branch, Enter to confirm, Esc to cancel.
