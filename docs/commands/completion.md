# `ocwt completion`

Print shell completion script.

## Usage

```bash
ocwt completion bash
ocwt completion zsh
```

## Setup examples

```bash
# bash
ocwt completion bash > ~/.ocwt-completion.bash
source ~/.ocwt-completion.bash

# zsh
ocwt completion zsh > ~/.ocwt-completion.zsh
source ~/.ocwt-completion.zsh
```

## What it includes

- command completion (`open`, `close`, `completion`, `config`)
- `@file` completion for `open`
- worktree branch suggestions for `close`
