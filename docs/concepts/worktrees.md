# Worktrees

`ocwt` keeps branch worktrees in a predictable parent folder and reuses them when possible.

## Path layout

- default parent: `.worktrees` next to the repo root
- branch path format: `/` replaced with `__`

Example:

```text
feat/my-branch -> .worktrees/feat__my-branch
```

## Reuse behavior

- if branch worktree already exists, `open` reuses it
- if not, `open` creates branch + worktree from base branch

## Shared files (configurable)

Depending on config, linked worktrees can symlink:

- `.opencode`
- `.idea`
- untracked `.env` / `.env.*`
