# Config

This directory is reserved for config parsing and precedence logic.

Current support includes `~/.config/ocwt/config.json` loading through `src/lib/config.ts`.

The native tools currently honor `worktree_parent` from config, with explicit tool options taking precedence over file values.

The normalized config layer also parses these keys for future parity work:

- `agent`
- `auto_plan`
- `auto_pull`
- `symlink_opencode`
- `symlink_idea`
- `symlink_env`
