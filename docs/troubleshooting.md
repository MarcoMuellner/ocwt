# Troubleshooting

## `Failed to generate branch name with opencode`

`ocwt` could not get a valid branch from `opencode run`.

What to do:

- check `opencode` availability: `opencode --version`
- retry with explicit agent: `ocwt build "..." --agent build`
- if it still fails, `ocwt` falls back to deterministic branch naming

## Planning mode shows no continuation session

`ocwt` tries to parse session id from planning events. If not found, it falls back to `--continue`.

What to do:

- update `ocwt` to latest
- rerun with `--plan`

## `auto_pull` fails

`auto_pull` uses `git pull --ff-only` and fails on non-fast-forward state.

What to do:

- resolve local divergence manually
- rerun `ocwt open <existing-file>` or `ocwt build "..."`

## `ocwt close` picker not interactive

Arrow-key picker requires TTY input/output.

What to do:

- run in a normal terminal session
- or pass explicit branch: `ocwt close feat/my-branch`
