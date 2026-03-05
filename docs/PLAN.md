# Revised Plan

- Rebuild `ocwt` as a Python package with a console executable, preserving current worktree behavior (`open`, `close`, completion, symlinks, branch generation, reuse existing worktrees).
- Replace file-based manual config editing with CLI-managed config commands only, backed by JSON at `~/.config/ocwt/config.json`.
- Add interactive one-shot planning mode that visibly streams progress, then drops into `opencode` in the same session using the `build` agent.
- Keep editor launch integrated and configurable via CLI (`ocwt config editor <executable>`), opening in the created/reused worktree directory.

## CLI Surface

- `ocwt open [file-path|existing-branch] [--plan] [--agent <name>] [--editor <exe>|none]`
- `ocwt build [intent] [@file ...] [--plan] [--agent <name>] [--editor <exe>|none]`
- `ocwt close [branch|worktree_path]`
- `ocwt completion [bash|zsh]`
- `ocwt config show`
- `ocwt config get <key>`
- `ocwt config set <key> <value>`
- Convenience setters:
  - `ocwt config editor <executable|none>`
  - `ocwt config agent <name>`
  - `ocwt config prompt-file <path|default>`
  - `ocwt config branch-prompt-file <path|default>`
  - `ocwt config worktree-parent <name>`
  - `ocwt config auto-plan <true|false>`
  - `ocwt config open-editor <true|false>`
- `ocwt config reset [key]`

## JSON Config Schema

- Path: `~/.config/ocwt/config.json`
- Keys:
  - `editor` (string, default `"cursor"` or `"none"` if unavailable)
  - `open_editor` (bool)
  - `agent` (string, default `"build"`)
  - `auto_plan` (bool, default `false`)
  - `prompt_file` (string or `null` for built-in default)
  - `branch_prompt_file` (string or `null`)
  - `worktree_parent` (string, default `".worktrees"`)
  - `symlink_opencode` / `symlink_idea` / `symlink_env` (bool)

## One-Shot Planning + Same Session Flow

- `ocwt build --plan ...` (or `ocwt open <existing-file> --plan`):
  - Creates/reuses worktree.
  - Prints clear planning banner (`Planning started...`) and streams live opencode output (spinner + line stream; no silent wait).
  - Runs one-shot with `opencode run --agent build ...` (plus attached `@file`s).
  - Captures resulting session id from machine output (`--format json`) when available.
  - Opens interactive TUI in the same session via `opencode --session <id> <worktree_dir> --agent build`.
  - Fallback if id not parseable: `opencode --continue <worktree_dir> --agent build` with explicit warning.

## Implementation Phases

- Phase 1: Package scaffold (`pyproject.toml`, `src/ocwt/...`, entrypoint).
- Phase 2: Port git/worktree + branch logic from Bash.
- Phase 3: Port symlink logic and close safeguards.
- Phase 4: Add config subsystem (`config` command family + JSON persistence).
- Phase 5: Add planning runner with interactive streamed UX + session handoff.
- Phase 6: Add editor launcher + config integration.
- Phase 7: Tests (unit + temp-repo integration) and compatibility polish (`octw` alias optional).

## Acceptance Checks

- `ocwt config editor zed` persists and is used on next `open`/`build`.
- `ocwt build "..." --plan` shows active planning output and then lands in same opencode session.
- Existing branch/worktree reopen behavior still works.
- `close` still protects `main/master/base` and handles interactive selection safely.
