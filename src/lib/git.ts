import { promisify } from "node:util"
import { execFile } from "node:child_process"
import path from "node:path"

import { ERROR_CODES, OcwtError } from "./errors.js"
import { canonicalizePath } from "./paths.js"

const execFileAsync = promisify(execFile)

export interface GitCommandResult {
  exitCode: number
  stdout: string
  stderr: string
}

export interface GitWorktreeEntry {
  directory: string
  branch?: string
  head?: string
  bare: boolean
  detached: boolean
  locked: boolean
  prunable: boolean
}

/**
 * Runs a git command inside the provided directory and returns trimmed output.
 *
 * @param cwd - The working directory for the git invocation.
 * @param args - The git arguments to execute.
 * @returns The command exit code and captured output.
 */
export async function runGit(
  cwd: string,
  args: string[],
): Promise<GitCommandResult> {
  try {
    const result = await execFileAsync("git", args, {
      cwd,
      encoding: "utf8",
    })

    return {
      exitCode: 0,
      stdout: result.stdout.trim(),
      stderr: result.stderr.trim(),
    }
  } catch (error) {
    const failure = error as {
      code?: number
      stdout?: string
      stderr?: string
      message?: string
    }

    return {
      exitCode: failure.code ?? 1,
      stdout: failure.stdout?.trim() ?? "",
      stderr: failure.stderr?.trim() ?? failure.message ?? "",
    }
  }
}

/**
 * Resolves the git repository root for the provided directory.
 *
 * @param cwd - Any directory inside the target repository.
 * @returns The canonical repository root path.
 * @throws OcwtError When the directory is not inside a git repository.
 */
export async function findRepoRoot(cwd: string): Promise<string> {
  const result = await runGit(cwd, ["rev-parse", "--show-toplevel"])

  if (result.exitCode !== 0 || !result.stdout) {
    throw new OcwtError(
      ERROR_CODES.notGitRepo,
      "Current directory is not a git repository",
    )
  }

  return canonicalizePath(result.stdout)
}

/**
 * Returns the current branch name when HEAD points at a local branch.
 *
 * @param cwd - Any directory inside the target repository.
 * @returns The current branch name, or `undefined` when HEAD is detached.
 */
export async function getCurrentBranch(
  cwd: string,
): Promise<string | undefined> {
  const result = await runGit(cwd, ["branch", "--show-current"])
  if (result.exitCode !== 0 || !result.stdout) return undefined
  return result.stdout
}

/**
 * Resolves the repository base branch using remote HEAD first, then common local defaults.
 *
 * @param cwd - Any directory inside the target repository.
 * @returns The detected base branch name.
 * @throws OcwtError When no repository base branch can be resolved.
 */
export async function getBaseBranch(cwd: string): Promise<string> {
  const repoRoot = await findRepoRoot(cwd)
  const remoteHead = await runGit(repoRoot, [
    "symbolic-ref",
    "refs/remotes/origin/HEAD",
  ])

  if (
    remoteHead.exitCode === 0 &&
    remoteHead.stdout.startsWith("refs/remotes/origin/")
  ) {
    return remoteHead.stdout.replace("refs/remotes/origin/", "")
  }

  for (const branch of ["main", "master"]) {
    const branchCheck = await runGit(repoRoot, [
      "show-ref",
      "--verify",
      "--quiet",
      `refs/heads/${branch}`,
    ])
    if (branchCheck.exitCode === 0) return branch
  }

  const currentBranch = await getCurrentBranch(repoRoot)
  if (currentBranch) return currentBranch

  throw new OcwtError(
    ERROR_CODES.notGitRepo,
    "Could not determine the repository base branch",
  )
}

/**
 * Lists git worktrees registered for the repository.
 *
 * @param cwd - Any directory inside the target repository.
 * @returns The parsed porcelain worktree entries.
 */
export async function listWorktrees(cwd: string): Promise<GitWorktreeEntry[]> {
  const repoRoot = await findRepoRoot(cwd)
  const result = await runGit(repoRoot, ["worktree", "list", "--porcelain"])

  if (result.exitCode !== 0) {
    throw new OcwtError(
      ERROR_CODES.removeFailed,
      result.stderr || "Failed to list git worktrees",
    )
  }

  return parseWorktreeList(result.stdout)
}

/**
 * Finds a registered worktree by branch name.
 *
 * @param cwd - Any directory inside the target repository.
 * @param branch - The local branch name to match.
 * @returns The matching worktree entry, if one exists.
 */
export async function findWorktreeByBranch(
  cwd: string,
  branch: string,
): Promise<GitWorktreeEntry | undefined> {
  const worktrees = await listWorktrees(cwd)
  return worktrees.find((entry) => entry.branch === branch)
}

/**
 * Finds a registered worktree by path using canonical path comparison.
 *
 * @param cwd - Any directory inside the target repository.
 * @param targetPath - The worktree path to look up.
 * @returns The matching worktree entry, if one exists.
 */
export async function findWorktreeByPath(
  cwd: string,
  targetPath: string,
): Promise<GitWorktreeEntry | undefined> {
  const canonicalTargetPath = await canonicalizePath(targetPath)
  const worktrees = await listWorktrees(cwd)

  for (const entry of worktrees) {
    if ((await canonicalizePath(entry.directory)) === canonicalTargetPath)
      return entry
  }

  return undefined
}

/**
 * Creates a new worktree and local branch from the specified start point.
 *
 * @param cwd - Any directory inside the target repository.
 * @param input - The branch, directory, and starting revision to use.
 * @throws OcwtError When git fails to create the worktree.
 */
export async function createWorktree(
  cwd: string,
  input: {
    branch: string
    directory: string
    startPoint: string
  },
): Promise<void> {
  const repoRoot = await findRepoRoot(cwd)
  const result = await runGit(repoRoot, [
    "worktree",
    "add",
    "-b",
    input.branch,
    input.directory,
    input.startPoint,
  ])

  if (result.exitCode !== 0) {
    throw new OcwtError(
      ERROR_CODES.worktreeCreateFailed,
      result.stderr || "Failed to create git worktree",
    )
  }
}

/**
 * Removes a registered worktree from the repository.
 *
 * @param cwd - Any directory inside the target repository.
 * @param directory - The worktree directory to remove.
 * @param force - Whether to request forced removal from git.
 * @throws OcwtError When git fails to remove the worktree.
 */
export async function removeWorktree(
  cwd: string,
  directory: string,
  force = false,
): Promise<void> {
  const repoRoot = await findRepoRoot(cwd)
  const args = ["worktree", "remove"]
  if (force) args.push("--force")
  args.push(directory)

  const result = await runGit(repoRoot, args)
  if (result.exitCode !== 0) {
    throw new OcwtError(
      ERROR_CODES.removeFailed,
      result.stderr || "Failed to remove git worktree",
    )
  }
}

/**
 * Deletes a local branch by name.
 *
 * @param cwd - Any directory inside the target repository.
 * @param branch - The local branch to delete.
 * @param force - Whether to force branch deletion.
 * @throws OcwtError When git fails to delete the branch.
 */
export async function deleteLocalBranch(
  cwd: string,
  branch: string,
  force = true,
): Promise<void> {
  const repoRoot = await findRepoRoot(cwd)
  const result = await runGit(repoRoot, ["branch", force ? "-D" : "-d", branch])

  if (result.exitCode !== 0) {
    throw new OcwtError(
      ERROR_CODES.deleteBranchFailed,
      result.stderr || `Failed to delete local branch ${branch}`,
    )
  }
}

/**
 * Returns true when the branch is protected from destructive ocwt operations.
 *
 * @param branch - The branch to classify.
 * @param baseBranch - The repository base branch.
 * @returns True when the branch must not be removed.
 */
export function isProtectedBranch(branch: string, baseBranch: string): boolean {
  return ["main", "master", baseBranch].includes(branch)
}

/**
 * Returns true when the provided path is tracked by git.
 *
 * @param cwd - Any directory inside the target repository.
 * @param targetPath - The file path to test.
 * @returns True when the path is tracked in the repository index.
 */
export async function isTrackedPath(
  cwd: string,
  targetPath: string,
): Promise<boolean> {
  const repoRoot = await findRepoRoot(cwd)
  const canonicalTargetPath = await canonicalizePath(targetPath)
  const relativePath = path.relative(repoRoot, canonicalTargetPath)
  const result = await runGit(repoRoot, [
    "ls-files",
    "--error-unmatch",
    relativePath,
  ])
  return result.exitCode === 0
}

function parseWorktreeList(output: string): GitWorktreeEntry[] {
  const entries: GitWorktreeEntry[] = []
  let current: GitWorktreeEntry | undefined

  for (const line of output.split("\n")) {
    const trimmedLine = line.trim()
    if (!trimmedLine) {
      if (current) entries.push(current)
      current = undefined
      continue
    }

    if (trimmedLine.startsWith("worktree ")) {
      if (current) entries.push(current)
      current = {
        directory: trimmedLine.slice("worktree ".length),
        bare: false,
        detached: false,
        locked: false,
        prunable: false,
      }
      continue
    }

    if (!current) continue

    if (trimmedLine.startsWith("branch refs/heads/")) {
      current.branch = trimmedLine.slice("branch refs/heads/".length)
      continue
    }

    if (trimmedLine.startsWith("HEAD ")) {
      current.head = trimmedLine.slice("HEAD ".length)
      continue
    }

    if (trimmedLine === "bare") current.bare = true
    if (trimmedLine === "detached") current.detached = true
    if (trimmedLine.startsWith("locked")) current.locked = true
    if (trimmedLine.startsWith("prunable")) current.prunable = true
  }

  if (current) entries.push(current)
  return entries
}
