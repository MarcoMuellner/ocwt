# OpenCode-native ocwt Implementation Plan

## Purpose

This document turns the design in `OPENCODE_NATIVE_OCWT_DESIGN.md` into a concrete implementation plan.

It is intended to be executable by an engineer without needing to rediscover the OpenCode platform surface area first.

## Distribution update

The current implementation direction has changed from a local `.opencode/`-directory delivery model to a standalone npm plugin model.

The shipping target is now:

- installable through `opencode.json` via the `plugin` field
- no required local `.opencode/tools/` or `.opencode/commands/` artifacts
- tools registered from plugin code
- commands injected from plugin config hooks

## What research confirmed

The current OpenCode docs and source support the core architecture needed for native `ocwt`:

- custom tools in `.opencode/tools/`
- custom commands in `.opencode/commands/`
- optional plugins in `.opencode/plugins/`
- SDK-driven session creation and prompting
- TUI session switching by `sessionID`

Important implementation detail from source:

- `createOpencodeClient({ directory })` binds SDK operations to a target directory/worktree through the `x-opencode-directory` header
- `tui.selectSession` exists as a real API route and is covered by source tests

This means native `ocwt` can create or reuse a git worktree, create or locate a session for that worktree directory, and switch the TUI into that session without shelling out to a separate `opencode` process.

## Recommended implementation stance

Build phase 1 on documented OpenCode extension points, but rely on source-verified session behavior where the docs are light.

Specifically:

- use `.opencode/tools/`, not legacy `.opencode/tool/`
- use slash commands only as thin entrypoints
- keep worktree, branch, symlink, and session logic inside shared TypeScript modules
- do not use plugins for core lifecycle behavior in phase 1
- do not rely on OpenCode's experimental built-in worktree API for parity because its naming and lifecycle behavior do not match the required `ocwt` contract

## Delivery goals

The implementation should satisfy all of these before being considered ready:

- `/wt-open <intent>` creates or reuses the correct worktree
- worktree selection is deterministic from branch naming
- branch naming rules match the current semantic-prefix contract
- session creation is bound to the target worktree directory
- TUI auto-switch happens when interactive context exists
- headless mode still returns enough metadata for follow-up
- `/wt-close` safely removes only valid worktrees and protected-branch rules are enforced
- symlink behavior matches current defaults and safety requirements

## Proposed target layout

```text
.opencode/
  package.json
  tools/
    ocwt_open.ts
    ocwt_close.ts
    ocwt_list.ts
    ocwt_config.ts
    lib/
      branch.ts
      config.ts
      errors.ts
      git.ts
      json.ts
      paths.ts
      session.ts
      symlink.ts
      types.ts
  commands/
    wt-open.md
    wt-build.md
    wt-close.md
    wt-list.md
  plugins/
    ocwt-ui.ts
```

Notes:

- `ocwt_config.ts` is phase 2, but reserving the file now keeps the architecture stable.
- `plugins/ocwt-ui.ts` is optional and should not block core delivery.

## Architecture rules

### Thin entrypoints

Each tool file should:

- define the input schema
- call shared domain functions
- map errors into stable result envelopes
- return a JSON string only

Each command file should:

- gather arguments
- invoke the corresponding tool first
- summarize the returned payload concisely
- avoid duplicating business logic in prompt text

### Shared modules own all behavior

Keep the domain logic in `.opencode/tools/lib/`:

- `branch.ts`: validation, sanitization, prefix enforcement, fallback generation
- `git.ts`: repo detection, base branch resolution, worktree listing, create/remove logic, protection checks
- `paths.ts`: deterministic worktree path mapping and repo-relative path helpers
- `session.ts`: session lookup, session creation, TUI selection, headless detection
- `symlink.ts`: shared state sync, backup-before-replace rules, tracked vs untracked `.env` handling
- `config.ts`: read and validate `~/.config/ocwt/config.json`
- `errors.ts`: stable error types and mapping helpers
- `types.ts`: shared DTOs and envelope types
- `json.ts`: safe JSON success/error builders

### Stable result contract

All tools should return JSON strings using one envelope shape:

```json
{
  "ok": true,
  "code": "OK",
  "message": "Worktree ready",
  "data": {},
  "next_action": "Optional follow-up hint"
}
```

Rules:

- `ok` is always present
- `code` is always stable and machine-readable
- `message` is short and user-readable
- `data` is omitted only when unnecessary
- `next_action` is optional and only used when it adds value

## Good software practices to enforce

### Strong typing

- use strict TypeScript everywhere
- validate every tool input with Zod
- validate config loaded from disk before use
- avoid loosely typed transport objects outside a small boundary layer

### Idempotent lifecycle behavior

- `ocwt_open` should be safe to run repeatedly
- existing matching worktrees should be reused by default
- symlink reconciliation should be safe on repeated runs
- session lookup should prefer reuse over duplicate creation where possible

### Fail-closed safety

- protected branches must never be deleted
- the main worktree directory must never be removed
- arbitrary directories must never be treated as close targets
- tracked `.env` files must not be symlinked as if they were safe untracked files

### Separation of concerns

- git execution only through `git.ts`
- filesystem/symlink operations only through `paths.ts` and `symlink.ts`
- session SDK interactions only through `session.ts`
- commands should not contain shell-heavy fallback logic

### Deterministic behavior

- branch fallback names should be deterministic for the same invalid input path
- worktree directory mapping must always use the same branch-to-path transform
- tests should inject clocks or name generators where needed to avoid flaky assertions

### Test-first hardening

- convert current Python behavior into fixture-backed cases before coding parity-sensitive sections
- add unit coverage for every sanitizer, resolver, and safety rule
- use integration tests for end-to-end lifecycle flows in temp git repos

### Structured observability

- keep optional debug logs around branch resolution, worktree reuse, session selection, and symlink actions
- avoid verbose normal-path logs in tool return values
- include enough metadata in error envelopes for diagnosis without exposing unrelated filesystem detail

## Detailed implementation phases

## Phase 0: Behavior lock

Goal: freeze the current `ocwt` contract before writing native behavior.

Tasks:

- extract all behavior promises from `OPENCODE_NATIVE_OCWT_DESIGN.md`
- reconstruct Python parity expectations from the referenced source files if available elsewhere
- define golden test cases for:
  - semantic branch prefixes
  - sanitized branch names
  - deterministic fallback naming
  - worktree reuse vs creation
  - protected-branch refusal
  - `.opencode`, `.idea`, and `.env` symlink policy
  - headless vs interactive session behavior
- define exact success and error envelopes for all tools

Deliverables:

- test matrix document or inline fixtures
- stable error code catalog
- accepted default config behavior list

Exit criteria:

- there is no ambiguous behavior left for phase 1 implementation

## Phase 1: Minimal native implementation

Goal: ship the core lifecycle natively inside OpenCode.

Tasks:

- add `.opencode/package.json` with required runtime dependencies only
- implement shared library modules
- implement `ocwt_open.ts`
- implement `ocwt_close.ts`
- implement `ocwt_list.ts`
- add `/wt-open`, `/wt-build`, `/wt-close`, `/wt-list`
- verify session creation and TUI session switching

### Phase 1 scope details

#### `ocwt_open`

Responsibilities:

- validate input
- resolve repo root and base branch
- resolve branch from direct input or generated intent
- reuse an existing worktree when possible
- otherwise create a new worktree using deterministic path rules
- apply minimal phase-1 symlink policy for `.opencode`
- create or find a session bound to `worktreeDir`
- switch to that session when TUI context is available
- optionally run a planning prompt when `plan=true`
- return a structured success payload

Implementation notes:

- branch generation should be local logic, not an LLM dependency in phase 1
- if the provided/generated branch is invalid after sanitization, use deterministic fallback naming
- session creation should use a directory-bound SDK client for `worktreeDir`

#### `ocwt_close`

Responsibilities:

- resolve target from branch or path
- verify target belongs to a known worktree under the expected parent
- enforce protected branch rules
- remove worktree safely
- delete local branch only after worktree removal succeeds
- return structured result fields for removed worktree and deleted branch

Implementation notes:

- never infer arbitrary paths as removable
- protect `main`, `master`, detected base branch, and primary worktree location

#### `ocwt_list`

Responsibilities:

- resolve repo root and base branch
- enumerate ocwt-managed worktrees
- mark protected entries
- optionally attach session IDs when discoverable

Implementation notes:

- prefer deterministic listing from the actual worktree parent plus git worktree state
- do not list unrelated directories that only happen to exist nearby

Exit criteria:

- the main worktree lifecycle works natively
- no external `ocwt` process handoff is needed

## Phase 2: Parity hardening

Goal: close the gap with current Python behavior.

Tasks:

- fully implement symlink parity
- implement config parity from `~/.config/ocwt/config.json`
- support `auto_plan`
- support `agent` selection from config and input
- support `worktree_parent` override
- support `.idea` and untracked `.env` symlinking
- add `ocwt_config.ts` if config mutation/showing is still desirable

### Config behavior to support

Honor at least:

- `agent`
- `auto_plan`
- `auto_pull`
- `worktree_parent`
- `symlink_opencode`
- `symlink_idea`
- `symlink_env`

Recommended precedence:

1. explicit tool input
2. project-native overlay if added later
3. `~/.config/ocwt/config.json`
4. built-in defaults

### Symlink parity details

Implement:

- `.opencode` sync/symlink
- optional `.idea` symlink
- optional untracked `.env` and `.env.*` symlinks
- backup creation before replacing conflicting files or directories
- tracked-vs-untracked checks before symlinking `.env` files

Exit criteria:

- behavior matches current defaults and safety contract closely enough for side-by-side acceptance

## Phase 3: UX polish

Goal: improve operator experience without changing the core contract.

Tasks:

- add optional `.opencode/plugins/ocwt-ui.ts`
- show success/error toasts after open/close flows
- improve concise summaries returned by commands
- optionally add richer event-driven status around session/worktree readiness

Rules:

- phase 3 must not own any critical lifecycle logic
- plugin absence must not break core functionality

## Phase 4: Deprecate old path

Goal: remove dependency on the old Python shell-out path.

Tasks:

- mark the old path deprecated
- keep a short fallback window only if acceptance is incomplete
- remove fallback once parity is accepted

Exit criteria:

- native OpenCode implementation is the only supported path

## File-by-file implementation responsibilities

### `.opencode/tools/lib/branch.ts`

Implement:

- allowed prefix list
- branch-safe sanitization
- direct branch validation
- intent-to-branch conversion
- fallback branch generation
- helpers for human input vs explicit branch detection

Test cases:

- spaces, punctuation, uppercase, slashes, repeated separators
- invalid prefix normalization/refusal
- empty result fallback

### `.opencode/tools/lib/git.ts`

Implement:

- repo root detection
- base branch detection
- current branch lookup
- worktree listing and lookup by branch/path
- worktree creation using raw git worktree commands
- worktree removal
- local branch deletion
- tracked file detection for env symlink decisions

Test cases:

- detached HEAD fallback behavior
- base branch detection when `main` is absent and `master` exists
- existing worktree reuse
- refusal on protected branch removal

### `.opencode/tools/lib/paths.ts`

Implement:

- deterministic worktree directory mapping from branch with `/ -> __`
- canonical path comparison helpers
- protection against path traversal and off-parent targets

Test cases:

- nested branch names
- branch names with mixed separators
- equivalent absolute/relative path matching

### `.opencode/tools/lib/symlink.ts`

Implement:

- file existence checks
- backup naming strategy
- safe replacement rules
- symlink creation and verification
- optional shared state application based on config

Test cases:

- conflicting real file backup
- conflicting real directory backup
- existing correct symlink no-op
- tracked `.env` refusal

### `.opencode/tools/lib/session.ts`

Implement:

- create directory-bound OpenCode client
- list sessions for a specific directory when possible
- create session for target worktree
- apply title strategy
- select session in TUI when available
- detect and report headless behavior cleanly
- optionally run planning prompt in that session

Test cases:

- session created for target `worktreeDir`
- TUI switch success path
- headless no-switch path
- session creation failure maps to `SESSION_CREATE_FAILED`

### `.opencode/tools/lib/config.ts`

Implement:

- config file load from `~/.config/ocwt/config.json`
- schema validation
- defaults
- precedence merge helper with explicit tool inputs

Test cases:

- missing file fallback
- malformed config rejection
- explicit input overriding config

### `.opencode/tools/lib/errors.ts`

Implement:

- domain error classes or tagged factories
- envelope mapping helpers
- stable code constants

Rule:

- low-level exceptions should not leak directly from tools

### `.opencode/tools/ocwt_open.ts`

Implement:

- input schema
- call graph orchestration
- success/error envelope output

### `.opencode/tools/ocwt_close.ts`

Implement:

- input schema
- target resolution orchestration
- safe remove/delete sequence
- success/error envelope output

### `.opencode/tools/ocwt_list.ts`

Implement:

- input schema
- list assembly
- optional session enrichment

### `.opencode/commands/wt-open.md`

Behavior:

- call `ocwt_open`
- summarize branch, worktree, reuse/create state, and session outcome

### `.opencode/commands/wt-build.md`

Behavior:

- call `ocwt_open` with planning enabled
- summarize result and plan session state

### `.opencode/commands/wt-close.md`

Behavior:

- call `ocwt_close`
- summarize removed worktree and deleted branch state

### `.opencode/commands/wt-list.md`

Behavior:

- call `ocwt_list`
- present entries in compact readable form

## Runtime flow details

## Open flow

1. validate input
2. resolve repo root
3. resolve base branch
4. resolve target branch from explicit branch or intent
5. compute deterministic worktree path
6. check for existing matching worktree
7. reuse when present, otherwise create from base branch
8. apply symlink policy
9. create or locate session bound to `worktreeDir`
10. switch TUI session when available
11. if `plan=true`, send planning prompt in that session
12. return success envelope

Important behavior:

- reuse beats creation
- invalid generated branch names must never proceed unchanged
- TUI switch failure should not destroy a successfully created worktree; return partial success with a session-related error code only when appropriate

## Close flow

1. validate input
2. resolve target by branch or path
3. verify the target is an ocwt-managed worktree
4. enforce protected branch rules
5. remove the worktree
6. delete the local branch if present
7. return success envelope

Important behavior:

- no close operation should touch the primary worktree
- branch deletion must only happen after successful target validation

## List flow

1. resolve repo root and base branch
2. enumerate ocwt-managed worktrees
3. mark protected entries
4. enrich with session IDs when requested
5. return success envelope

## Planning behavior

Recommended default:

- `/wt-open` honors config `auto_plan`
- `/wt-build` always plans

Planning implementation approach:

- create the target session first
- send a prompt through the session SDK with planning instructions
- keep planning prompt text in one reusable helper so command behavior stays consistent

## Headless behavior

When running without an active TUI context:

- still create or reuse a session
- do not attempt TUI switching
- return `sessionID` and `worktreeDir`
- set `switchedSession` to `false`
- use `next_action` to tell the caller what to do next if useful

## Testing strategy

## Unit tests

Cover:

- branch prefix validation
- branch sanitization
- deterministic fallback generation
- protected branch detection
- branch-to-path mapping
- path safety checks
- symlink conflict backup behavior
- config merge precedence

## Integration tests

Use temporary git repos to cover:

- open creating a new worktree
- open reusing an existing worktree
- close removing worktree and branch
- protected branch refusal
- `.env` tracked vs untracked symlink behavior
- non-worktree path refusal

## Session/TUI tests

Cover:

- session created against target worktree directory
- interactive TUI switch path
- headless no-switch path
- graceful behavior when TUI selection fails

## Regression tests

Cover:

- parity scenarios captured from current Python behavior
- stable JSON envelopes for both success and failure

## Suggested acceptance checklist

- `ocwt_open` returns stable JSON on success and failure
- `ocwt_close` never removes protected targets
- branch fallback behavior is deterministic
- worktree directories map deterministically from branch names
- repeated open calls reuse instead of duplicating worktrees
- session creation is tied to the target worktree directory
- TUI switching works when available and degrades cleanly when not
- symlink policy preserves user data through backups
- commands stay thin and readable

## Final implementation decisions recommended now

To avoid blocking phase 1, lock these decisions in immediately:

1. Deprecate editor-launch semantics in native mode.
2. Use config precedence: explicit input > future project overlay > `~/.config/ocwt/config.json` > defaults.
3. Make `/wt-open` honor `auto_plan` and make `/wt-build` force planning.
4. Keep plugin UX out of phase 1.
5. Implement worktree lifecycle with raw git logic, not OpenCode's experimental worktree API, to preserve parity.

## Recommended first coding sequence

1. create `.opencode/package.json`
2. implement `types.ts`, `errors.ts`, `json.ts`
3. implement `branch.ts`, `paths.ts`
4. implement `git.ts`
5. implement `session.ts`
6. implement `ocwt_open.ts`
7. implement `ocwt_close.ts`
8. implement `ocwt_list.ts`
9. add command files
10. add tests
11. add config and symlink parity
12. add plugin polish if still needed

This sequence gets the highest-risk architecture decisions validated early and keeps the command layer thin from the start.

## Release automation

The standalone npm plugin distribution should include repository-native release automation.

- CI should run validation plus `npm pack --dry-run` on pushes and pull requests.
- Stable npm publishing should be triggered from GitHub Releases and use npm trusted publishing with provenance.
- Nightly publishing should produce a unique prerelease version, publish under the `nightly` dist-tag, and create a matching GitHub prerelease.
