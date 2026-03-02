from __future__ import annotations

import typer

from ocwt.git_ops import (
    get_current_git_root,
    list_worktree_branches,
    pick_main_branch,
    primary_repo_root,
)


def _completion_script() -> str:
    return """_ocwt_complete() {
  local cur prev cmd branches
  local path_cur f prefix
  local cur_start idx before_char
  local ocwt_cmd cli word
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]:-}"
  ocwt_cmd="${COMP_WORDS[0]:-ocwt}"
  cli="$ocwt_cmd"
  if ! command -v "$cli" >/dev/null 2>&1; then
    if command -v ocwt >/dev/null 2>&1; then
      cli="ocwt"
    elif command -v octw >/dev/null 2>&1; then
      cli="octw"
    fi
  fi

  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "open close help -h --help completion config" -- "$cur") )
    return 0
  fi

  cmd=""
  for word in "${COMP_WORDS[@]}"; do
    case "$word" in
      open|close|help|-h|--help|completion|config)
        cmd="$word"
        break
        ;;
    esac
  done

  case "$cmd" in
    open)
      path_cur="$cur"
      prefix=""
      if [[ "$cur" == @* ]]; then
        path_cur="${cur#@}"
        prefix="@"
      else
        cur_start=$((COMP_POINT - ${#cur}))
        if (( cur_start > 0 )); then
          idx=$((cur_start - 1))
          before_char="${COMP_LINE:$idx:1}"
          if [[ "$before_char" == "@" || "$prev" == "@" ]]; then
            path_cur="$cur"
            prefix="@"
          fi
        fi
      fi

      compopt -o filenames 2>/dev/null || true
      COMPREPLY=()
      while IFS= read -r f; do
        COMPREPLY+=("${prefix}${f}")
      done < <(compgen -f -- "$path_cur")
      ;;
    close)
      branches="$($cli __complete_worktrees 2>/dev/null)"
      COMPREPLY=( $(compgen -W "$branches" -- "$cur") )
      ;;
  esac
}

if [[ -n "${ZSH_VERSION:-}" ]]; then
  autoload -U +X bashcompinit >/dev/null 2>&1 && bashcompinit
fi

complete -o bashdefault -o default -F _ocwt_complete ocwt
complete -o bashdefault -o default -F _ocwt_complete octw
"""


def completion_worktree_branches() -> list[str]:
    git_root = get_current_git_root()
    if git_root is None:
        return []

    repo_root = primary_repo_root(git_root)
    base = pick_main_branch(repo_root)

    branches: list[str] = []
    for branch, _path in list_worktree_branches(repo_root):
        if branch in {"main", "master", base}:
            continue
        branches.append(branch)
    return branches


def run_complete_worktrees() -> int:
    for branch in completion_worktree_branches():
        typer.echo(branch)
    return 0


def run_completion(shell: str) -> int:
    normalized = shell.strip().lower()
    if normalized not in {"bash", "zsh"}:
        raise typer.BadParameter("shell must be one of: bash, zsh")

    typer.echo(_completion_script(), nl=False)
    return 0
