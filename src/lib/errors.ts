export const ERROR_CODES = {
  notGitRepo: "NOT_GIT_REPO",
  invalidInput: "INVALID_INPUT",
  fileNotFound: "FILE_NOT_FOUND",
  worktreeCreateFailed: "WORKTREE_CREATE_FAILED",
  sessionCreateFailed: "SESSION_CREATE_FAILED",
  sessionSwitchFailed: "SESSION_SWITCH_FAILED",
  targetNotFound: "TARGET_NOT_FOUND",
  protectedBranch: "PROTECTED_BRANCH",
  removeFailed: "REMOVE_FAILED",
  deleteBranchFailed: "DELETE_BRANCH_FAILED",
} as const

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES]

export class OcwtError extends Error {
  public readonly code: ErrorCode

  public constructor(code: ErrorCode, message: string) {
    super(message)
    this.name = "OcwtError"
    this.code = code
  }
}
