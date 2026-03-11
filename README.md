# opencode-ocwt

Standalone npm plugin for native `ocwt` workflows in OpenCode.

This repository builds `opencode-ocwt`, an installable OpenCode plugin package that is loaded through `opencode.json` without requiring a local `.opencode/` runtime directory.

## Goals

- implement `ocwt` natively as an installable OpenCode npm plugin
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
  config/     Config loading and precedence helpers
  lib/        Shared domain logic and types
  plugin*.ts  Plugin entrypoint and injected command definitions
  tools/      Native ocwt tool entrypoints
tests/        Unit and integration tests
```

The code lives under `src/`. The published package entrypoint is `src/plugin.ts`, which injects commands and registers tools through the OpenCode plugin API.

## Install

Add the plugin to your OpenCode config:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-ocwt"]
}
```

OpenCode installs npm plugins automatically with Bun at startup.

## Scripts

```bash
pnpm install
pnpm clean
pnpm check
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm pack:dry-run
pnpm format:check
```

## Release workflow

The repository now ships with GitHub Actions for CI, stable releases, and nightly prereleases.

- `CI` runs on pushes and pull requests, executes `pnpm check`, and verifies the publishable tarball with `npm pack --dry-run`
- `.github/workflows/release.yml` handles both stable and nightly publishing so npm trusted publishing only needs one workflow file
- stable publishing runs when a GitHub release is published, verifies that the release tag matches `package.json`, and publishes to npm with provenance
- nightly publishing runs from the same workflow on every push to `main` or manual dispatch, always checks out `main`, stamps a unique `-nightly.<timestamp>` version, publishes it to npm under the `nightly` dist-tag, and creates a GitHub prerelease

### npm trusted publishing

Stable and nightly publishing are configured for npm trusted publishing with GitHub Actions.

Before the workflows can publish, configure an npm trusted publisher for this repository and this workflow file:

- `.github/workflows/release.yml`

The workflows use `id-token: write` and publish with:

```bash
npm publish --provenance --access public
```

No long-lived `NPM_TOKEN` secret is required when trusted publishing is configured correctly.

The release workflow also avoids `actions/setup-node` token-auth registry configuration during publish, and upgrades npm in CI to meet npm's current trusted-publishing requirement (`npm` 11.5.1+).

## Current status

The project now includes deterministic branch, path, git, session, config, and symlink helpers plus real `ocwt_open`, `ocwt_close`, and `ocwt_list` flows for the core worktree lifecycle. Commands are now injected from the plugin at runtime, and the package is structured for standalone npm distribution through OpenCode's `plugin` config. The implementation plan is documented in:

- `OPENCODE_NATIVE_OCWT_DESIGN.md`
- `OPENCODE_NATIVE_OCWT_IMPLEMENTATION_PLAN.md`

## Engineering rules

- keep tool entrypoints thin and move domain logic into `src/lib/`
- return stable JSON envelopes from tool boundaries
- fail closed for destructive worktree operations
- prefer deterministic behavior over implicit heuristics
- add tests alongside any branch, git, path, or symlink logic
- harden edge cases before moving orchestration into tool entrypoints
- keep config precedence explicit: tool input overrides config, config overrides defaults
- back up conflicting files before replacing them with shared-state symlinks
- keep the shipping surface plugin-first: npm package plus `plugin` config only

## Runtime behavior

With the plugin loaded in OpenCode:

- `/wt-open` creates or reuses the worktree and switches the TUI to the target session
- `/wt-build` does the same and starts a planning prompt in the target session
- `/wt-open` also starts planning when `auto_plan` is enabled in `~/.config/ocwt/config.json`
- session creation and selection now use the live OpenCode SDK rather than placeholder plugin wrappers
