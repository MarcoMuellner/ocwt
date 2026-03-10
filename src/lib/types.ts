export const BRANCH_PREFIXES = [
  "feat",
  "bugfix",
  "fix",
  "chore",
  "docs",
  "refactor",
  "test",
  "perf",
] as const

export type BranchPrefix = (typeof BRANCH_PREFIXES)[number]

export interface ResultEnvelope<TData = Record<string, unknown>> {
  ok: boolean
  code: string
  message: string
  data?: TData
  next_action?: string
}

export interface OpenToolInput {
  intentOrBranch?: string
  files?: string[]
  plan?: boolean
  agent?: string
  reuseOnly?: boolean
}

export interface OpenToolSuccessData {
  repoRoot: string
  baseBranch: string
  branch: string
  worktreeDir: string
  created: boolean
  reused: boolean
  symlinkMessages: string[]
  sessionID?: string
  switchedSession?: boolean
}

export interface CloseToolInput {
  branchOrPath?: string
  force?: boolean
}

export interface ListToolInput {
  includeSessions?: boolean
}
