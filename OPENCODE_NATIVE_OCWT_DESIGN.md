# OpenCode-native ocwt Design Specification

## Purpose

This document defines a complete design to migrate `ocwt` from a standalone Python CLI into a native OpenCode implementation.

It is written as a standalone handoff document that an engineer can implement directly.

## Background

Current `ocwt` behavior is implemented in Python and shells out to OpenCode processes:

- branch generation via `opencode run`
- planning via `opencode run --format json`
- interactive handoff via `opencode .` or `opencode --session`

Key current implementation files:

- `src/ocwt/commands/open_cmd.py`
- `src/ocwt/commands/close_cmd.py`
- `src/ocwt/symlinks.py`
- `src/ocwt/git_ops.py`
- `src/ocwt/branching.py`
- `src/ocwt/config_store.py`

## Migration goal

Implement `ocwt` behavior directly inside OpenCode using:

- custom tools (`.opencode/tools/`)
- custom slash commands (`.opencode/commands/`)
- optional plugin hooks (`.opencode/plugins/`)

This removes external process handoff and keeps users in a single OpenCode UX.

## What must be preserved

### Worktree lifecycle

- Open from file/intent or reopen existing branch worktree
- Reuse existing branch worktree when present
- Create new worktree from base branch when missing
- Deterministic worktree path mapping from branch (slash to `__`)
- Safe close: remove worktree and delete local branch

### Safety rules

- Never delete `main`, `master`, or current base branch
- Never remove main worktree directory
- Never delete arbitrary non-worktree directories
- Backup conflicting files before replacing with symlinks

### Branch naming behavior

- Enforce semantic prefixes:
  - `feat/`, `bugfix/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`, `perf/`
- Sanitize model/user output into branch-safe text
- If generated output is invalid, use deterministic fallback branch

### Shared state behavior

- Sync/symlink `.opencode`
- Optionally symlink `.idea`
- Optionally symlink untracked `.env` / `.env.*`

### Planning/session behavior

- Support planning-first flow
- Create a session bound to target worktree directory
- Auto-switch TUI to that session when available
- Graceful fallback in headless mode

## OpenCode capabilities to use

Use currently available OpenCode features:

- Plugins from `.opencode/plugins/` or npm
- Custom tools from `.opencode/tools/`
- Custom slash commands from `.opencode/commands/`
- SDK session APIs (`session.create`, `session.prompt`, ...)
- SDK TUI APIs (`tui.selectSession`, `tui.showToast`, ...)

Important: sessions can be tied to a different directory/worktree. TUI switching is done by `sessionID`, not by current shell cwd.

## Target architecture

```text
.opencode/
  tools/
    ocwt_open.ts
    ocwt_close.ts
    ocwt_list.ts
    ocwt_config.ts            # optional in phase 2
    lib/
      branch.ts
      git.ts
      symlink.ts
      session.ts
      config.ts
      errors.ts
  commands/
    wt-open.md
    wt-build.md
    wt-close.md
    wt-list.md
  plugins/
    ocwt-ui.ts                # optional
  package.json
```

## Tool API contracts (stable)

All tool outputs should be JSON strings with this envelope:

- `ok: boolean`
- `code: string`
- `message: string`
- `data?: object`
- `next_action?: string`

### `ocwt_open`

Input:

- `intentOrBranch?: string`
- `files?: string[]`
- `plan?: boolean`
- `agent?: string`
- `reuseOnly?: boolean`

Success `data`:

- `repoRoot: string`
- `baseBranch: string`
- `branch: string`
- `worktreeDir: string`
- `created: boolean`
- `reused: boolean`
- `sessionID?: string`
- `switchedSession?: boolean`
- `symlinkMessages: string[]`

Error codes:

- `NOT_GIT_REPO`
- `INVALID_INPUT`
- `FILE_NOT_FOUND`
- `WORKTREE_CREATE_FAILED`
- `SESSION_CREATE_FAILED`
- `SESSION_SWITCH_FAILED`

### `ocwt_close`

Input:

- `branchOrPath?: string`
- `force?: boolean`

Success `data`:

- `repoRoot: string`
- `branch: string`
- `worktreeDir: string`
- `removedWorktree: boolean`
- `deletedBranch: boolean`

Error codes:

- `NOT_GIT_REPO`
- `TARGET_NOT_FOUND`
- `PROTECTED_BRANCH`
- `REMOVE_FAILED`
- `DELETE_BRANCH_FAILED`

### `ocwt_list`

Input:

- `includeSessions?: boolean`

Success `data`:

- `repoRoot: string`
- `baseBranch: string`
- `entries: Array<{ branch: string, directory: string, protected: boolean, sessionID?: string }>`

### `ocwt_config` (optional phase 2)

Input:

- `action: "get" | "set" | "reset" | "show"`
- `key?: string`
- `value?: string | boolean`

## Slash command design

Create command entrypoints:

- `/wt-open`
- `/wt-build`
- `/wt-close`
- `/wt-list`

Command templates should:

- call `ocwt_*` tools first (avoid shell-first logic)
- pass `$ARGUMENTS`/`$1` style command args into tool input
- return concise branch/worktree/session summary

## Runtime flows

### Open/build flow

1. Resolve repo root + base branch
2. Resolve target branch:
   - direct valid branch input, or
   - generate from intent/files, with deterministic fallback
3. Reuse existing worktree, else create new worktree
4. Apply symlink policy
5. Create/find OpenCode session for `worktreeDir`
6. If TUI available, call `tui.selectSession(sessionID)`
7. If `plan=true`, run planning prompt in that session
8. Return structured success payload

### Close flow

1. Resolve target from `branchOrPath` (or interactive/derived fallback)
2. Enforce protected branch rules
3. Remove registered worktree (optionally retry force)
4. Delete local branch if present
5. Return structured result

### Headless behavior

When no active TUI context exists:

- still create/find session
- do not attempt TUI switch
- return `sessionID` and `worktreeDir` for user follow-up

## Configuration strategy

Phase 1: preserve current config source for parity:

- `~/.config/ocwt/config.json`

Honor at least:

- `agent`
- `auto_plan`
- `auto_pull`
- `worktree_parent`
- `symlink_opencode`
- `symlink_idea`
- `symlink_env`

Phase 2 (optional): support an OpenCode config overlay and define precedence.

## Migration phases

### Phase 0: behavior lock

- Freeze expected behavior from Python implementation
- Add golden fixtures for edge cases

### Phase 1: minimal native implementation

- Implement `ocwt_open`, `ocwt_close`, `ocwt_list`
- Add `/wt-open`, `/wt-build`, `/wt-close`, `/wt-list`
- Ensure session create + auto-switch works

### Phase 2: parity hardening

- Port full symlink parity
- Add planning-first native path
- Integrate config parity from `~/.config/ocwt/config.json`

### Phase 3: UX polish (optional)

- Add plugin for toasts and richer event-driven UX

### Phase 4: deprecate old shell-out path

- Mark old Python OpenCode-launch flow deprecated
- Keep temporary fallback window
- Remove fallback after acceptance

## Test plan

### Unit tests

- branch sanitize/validate/fallback
- protected branch detection
- symlink conflict backup behavior
- path/branch resolution

### Integration tests (temp git repo)

- create and reopen worktrees
- close flow including force path
- protected branch refusal
- `.env` tracked vs untracked behavior

### Session/TUI tests

- session is created with target worktree directory
- TUI switch occurs when context is interactive
- headless path returns metadata without switch

### Regression checks

- compare output/behavior against current Python reference cases

## Acceptance criteria

Release-ready when all are true:

- `/wt-open <intent>` creates or reuses worktree and lands in correct session when TUI is present
- `/wt-close` safely removes worktree + branch and enforces protected branch policy
- branch naming rules and fallback behavior match current contract
- symlink behavior matches current defaults
- core flow no longer requires launching external `ocwt` process

## Implementation decisions to finalize before coding

1. Keep or deprecate editor-launch semantics in native mode
2. Config precedence if OpenCode overlay is added
3. Default planning behavior for `/wt-open` (`auto_plan` vs explicit)
4. Whether plugin UX layer is phase 1 or phase 3 only
