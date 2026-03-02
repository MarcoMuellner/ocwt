# `ocwt close`

Close a linked worktree and delete its local branch.

## Usage

```bash
ocwt close [branch|worktree-path]
```

## Examples

```bash
# Interactive picker (arrow keys)
ocwt close

# By branch
ocwt close feat/rate-limit-retries

# By worktree path
ocwt close /path/to/.worktrees/feat__rate-limit-retries
```

## Interactive mode

- Up/Down: move selection
- Enter: confirm
- Esc: cancel

## Safety rules

- Protected branches (`main`, `master`, current base) are never deleted.
- If target path is not a registered worktree, close exits with an error.
