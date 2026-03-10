import path from "node:path"
import { promises as fs } from "node:fs"

/**
 * Converts a branch name into the deterministic directory suffix used for ocwt worktrees.
 *
 * @param branch - The fully qualified git branch name.
 * @returns The branch name rewritten into a filesystem-safe worktree directory name.
 */
export function branchToWorktreeDirectoryName(branch: string): string {
  return branch.trim().replaceAll("/", "__")
}

/**
 * Resolves the expected worktree directory for a branch under the configured worktree parent.
 *
 * @param parentDir - The configured root directory that contains ocwt worktrees.
 * @param branch - The fully qualified git branch name.
 * @returns The absolute directory path for the branch worktree.
 */
export function resolveWorktreeDirectory(
  parentDir: string,
  branch: string,
): string {
  return path.resolve(parentDir, branchToWorktreeDirectoryName(branch))
}

/**
 * Normalizes a path for reliable comparisons across relative input, symbolic links, and platforms.
 *
 * @param targetPath - The path to normalize.
 * @returns A canonical absolute path suitable for equality and parent-child checks.
 */
export async function canonicalizePath(targetPath: string): Promise<string> {
  const absolutePath = path.resolve(targetPath)
  const realPath = await fs.realpath(absolutePath).catch(() => absolutePath)
  const normalizedPath = path.normalize(realPath)

  return process.platform === "win32"
    ? normalizedPath.toLowerCase()
    : normalizedPath
}

/**
 * Returns true when the target resolves to the same directory as the parent or a child within it.
 *
 * @param parentDir - The allowed root directory.
 * @param targetPath - The candidate path to verify.
 * @returns True when the candidate stays within the allowed root.
 */
export async function isWithinParentDirectory(
  parentDir: string,
  targetPath: string,
): Promise<boolean> {
  const canonicalParent = await canonicalizePath(parentDir)
  const canonicalTarget = await canonicalizePath(targetPath)

  return (
    canonicalTarget === canonicalParent ||
    canonicalTarget.startsWith(`${canonicalParent}${path.sep}`)
  )
}

/**
 * Returns true when the target path matches the deterministic ocwt directory for the branch.
 *
 * @param parentDir - The configured root directory that contains ocwt worktrees.
 * @param branch - The fully qualified git branch name.
 * @param targetPath - The candidate worktree path to compare.
 * @returns True when the path matches the branch's managed worktree location.
 */
export async function matchesManagedWorktreePath(
  parentDir: string,
  branch: string,
  targetPath: string,
): Promise<boolean> {
  const expectedPath = resolveWorktreeDirectory(parentDir, branch)
  const canonicalExpectedPath = await canonicalizePath(expectedPath)
  const canonicalTargetPath = await canonicalizePath(targetPath)

  return canonicalExpectedPath === canonicalTargetPath
}
