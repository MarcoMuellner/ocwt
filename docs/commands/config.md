# `ocwt config`

Manage persistent settings at `~/.config/ocwt/config.json`.

## Usage

```bash
ocwt config show
ocwt config get <key>
ocwt config set <key> <value>
ocwt config reset [key]
```

## Convenience setters

```bash
ocwt config editor zed
ocwt config agent build
ocwt config auto-plan true
ocwt config auto-pull true
ocwt config open-editor false
ocwt config worktree-parent .worktrees
ocwt config prompt-file default
ocwt config branch-prompt-file default
```

## High-impact keys

- `auto_plan`: run plan mode by default on `open`
- `auto_pull`: run `git pull --ff-only` before creating new worktrees
- `open_editor`: auto-open editor during `open`
- `editor`: editor executable (`none` disables)
