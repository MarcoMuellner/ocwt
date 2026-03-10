# ocwt-native

Native OpenCode implementation workspace for `ocwt`.

This repository is the source workspace for building the OpenCode-native version of `ocwt`, based on `OPENCODE_NATIVE_OCWT_DESIGN.md` and `OPENCODE_NATIVE_OCWT_IMPLEMENTATION_PLAN.md`.

## Goals

- implement `ocwt` natively with OpenCode tools and commands
- keep worktree lifecycle safe and deterministic
- preserve current branch, symlink, and session behavior
- keep the codebase small, typed, and testable

## Stack

- `pnpm` for package management
- `TypeScript` in strict mode
- `vitest` for tests
- `oxlint` for linting
- `prettier` for formatting
- `zod` for schemas and runtime validation

## Layout

```text
src/
  commands/   Prompt and command scaffolding
  config/     Config loading and precedence helpers
  lib/        Shared domain logic and types
  tools/      Native ocwt tool entrypoints
tests/        Unit and integration tests
```

The code lives under `src/`. The eventual `.opencode/` runtime surface can be generated or assembled from these source files once implementation starts.

## Scripts

```bash
pnpm install
pnpm typecheck
pnpm lint
pnpm test
pnpm format:check
```

## Current status

The project now includes the first shared domain helpers for deterministic branch, path, and git lifecycle handling. The implementation plan is documented in:

- `OPENCODE_NATIVE_OCWT_DESIGN.md`
- `OPENCODE_NATIVE_OCWT_IMPLEMENTATION_PLAN.md`

## Engineering rules

- keep tool entrypoints thin and move domain logic into `src/lib/`
- return stable JSON envelopes from tool boundaries
- fail closed for destructive worktree operations
- prefer deterministic behavior over implicit heuristics
- add tests alongside any branch, git, path, or symlink logic
