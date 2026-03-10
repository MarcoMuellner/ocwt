export interface InjectedCommand {
  description: string
  template: string
  agent: string
}

export const INJECTED_COMMANDS: Record<string, InjectedCommand> = {
  "wt-open": {
    description: "Open or reuse an ocwt worktree",
    agent: "build",
    template: [
      "Open or reuse an ocwt worktree for `$ARGUMENTS`.",
      "",
      "Call the `ocwt_open` tool first with:",
      "- `intentOrBranch`: `$ARGUMENTS`",
      "",
      "After the tool returns:",
      "- summarize the branch, worktree directory, whether it was created or reused, and any session outcome",
      "- if `ok` is false, explain the failure code and the next action if one was returned",
      "- do not fall back to shell-first worktree logic",
    ].join("\n"),
  },
  "wt-build": {
    description: "Open an ocwt worktree and start in planning mode",
    agent: "build",
    template: [
      "Open or reuse an ocwt worktree for `$ARGUMENTS` in planning-first mode.",
      "",
      "Call the `ocwt_open` tool first with:",
      "- `intentOrBranch`: `$ARGUMENTS`",
      "- `plan`: `true`",
      "",
      "After the tool returns:",
      "- summarize the branch, worktree directory, whether it was created or reused, and any session outcome",
      "- if `ok` is false, explain the failure code and the next action if one was returned",
      "- do not fall back to shell-first worktree logic",
    ].join("\n"),
  },
  "wt-close": {
    description: "Close an ocwt worktree safely",
    agent: "build",
    template: [
      "Close the ocwt worktree identified by `$ARGUMENTS`.",
      "",
      "Call the `ocwt_close` tool first with:",
      "- `branchOrPath`: `$ARGUMENTS`",
      "",
      "After the tool returns:",
      "- summarize the branch, worktree directory, and whether the worktree and branch were removed",
      "- if `ok` is false, explain the failure code and the next action if one was returned",
      "- do not fall back to shell-first worktree logic",
    ].join("\n"),
  },
  "wt-list": {
    description: "List ocwt-managed worktrees",
    agent: "build",
    template: [
      "List the currently managed ocwt worktrees.",
      "",
      "Call the `ocwt_list` tool first.",
      "",
      "After the tool returns:",
      "- summarize the base branch and each listed worktree entry",
      "- include session IDs only when the tool returns them",
      "- if `ok` is false, explain the failure code and the next action if one was returned",
      "- do not fall back to shell-first worktree logic",
    ].join("\n"),
  },
}
