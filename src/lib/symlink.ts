import path from "node:path"
import { promises as fs } from "node:fs"

import { isTrackedPath } from "./git.js"
import { canonicalizePath } from "./paths.js"

export interface SharedStateOptions {
  symlinkOpencode: boolean
  symlinkIdea: boolean
  symlinkEnv: boolean
}

/**
 * Applies the configured shared-state symlink policy from the repository root into a worktree.
 *
 * @param repoRoot - The primary repository root that owns the shared files.
 * @param worktreeDir - The target worktree directory that should reuse shared state.
 * @param options - The config-controlled symlink toggles.
 * @returns User-readable messages describing applied or skipped actions.
 */
export async function applySharedStateSymlinks(
  repoRoot: string,
  worktreeDir: string,
  options: SharedStateOptions,
): Promise<string[]> {
  if (
    (await canonicalizePath(repoRoot)) === (await canonicalizePath(worktreeDir))
  ) {
    return []
  }

  const messages: string[] = []

  if (options.symlinkOpencode) {
    const result = await ensureSharedPathSymlink(
      repoRoot,
      worktreeDir,
      ".opencode",
    )
    if (result) messages.push(result)
  }

  if (options.symlinkIdea) {
    const result = await ensureSharedPathSymlink(repoRoot, worktreeDir, ".idea")
    if (result) messages.push(result)
  }

  if (options.symlinkEnv) {
    const envResults = await ensureEnvSymlinks(repoRoot, worktreeDir)
    messages.push(...envResults)
  }

  return messages
}

/**
 * Creates or verifies a symlink from a worktree path to the shared source path in the repo root.
 *
 * @param repoRoot - The primary repository root that owns the shared file or directory.
 * @param worktreeDir - The target worktree directory that should reuse shared state.
 * @param relativeName - The shared path name relative to both roots.
 * @returns A message describing the action taken, or `undefined` when nothing applies.
 */
export async function ensureSharedPathSymlink(
  repoRoot: string,
  worktreeDir: string,
  relativeName: string,
): Promise<string | undefined> {
  const sourcePath = path.join(repoRoot, relativeName)
  const targetPath = path.join(worktreeDir, relativeName)

  if (
    (await canonicalizePath(sourcePath)) ===
    (await canonicalizePath(targetPath))
  ) {
    return `Skipped ${relativeName}: source and target are the same path`
  }

  const sourceStatus = await readPathStatus(sourcePath)

  if (!sourceStatus.exists) {
    return `Skipped ${relativeName}: source does not exist`
  }

  if (await isSymlinkToTarget(targetPath, sourcePath)) {
    return `Kept ${relativeName}: existing symlink is correct`
  }

  const targetStatus = await readPathStatus(targetPath)
  if (targetStatus.exists) {
    const backupPath = await backupExistingPath(targetPath)
    await fs.rename(targetPath, backupPath)
    return await createSymlinkAndReport(
      sourcePath,
      targetPath,
      relativeName,
      backupPath,
    )
  }

  await createSymlink(
    sourcePath,
    targetPath,
    await detectSourceKind(sourcePath),
  )
  return `Linked ${relativeName}`
}

/**
 * Creates symlinks for untracked `.env` files at the repository root.
 *
 * @param repoRoot - The primary repository root that owns the env files.
 * @param worktreeDir - The target worktree directory that should reuse shared state.
 * @returns Messages describing linked or skipped env files.
 */
export async function ensureEnvSymlinks(
  repoRoot: string,
  worktreeDir: string,
): Promise<string[]> {
  const names = await listEnvCandidates(repoRoot)
  const messages: string[] = []

  for (const name of names) {
    const sourcePath = path.join(repoRoot, name)
    if (await isTrackedPath(repoRoot, sourcePath)) {
      messages.push(`Skipped ${name}: tracked files are not symlinked`)
      continue
    }

    const result = await ensureSharedPathSymlink(repoRoot, worktreeDir, name)
    if (result) messages.push(result)
  }

  return messages
}

/**
 * Creates the next deterministic backup path for a conflicting target.
 *
 * @param targetPath - The path that will be replaced by a symlink.
 * @returns The backup path that does not currently exist.
 */
export async function backupExistingPath(targetPath: string): Promise<string> {
  let index = 1

  while (true) {
    const candidate = `${targetPath}.backup-${index}`
    const status = await readPathStatus(candidate)
    if (!status.exists) return candidate
    index += 1
  }
}

async function createSymlinkAndReport(
  sourcePath: string,
  targetPath: string,
  relativeName: string,
  backupPath: string,
): Promise<string> {
  await createSymlink(
    sourcePath,
    targetPath,
    await detectSourceKind(sourcePath),
  )
  return `Linked ${relativeName} after backup to ${path.basename(backupPath)}`
}

async function createSymlink(
  sourcePath: string,
  targetPath: string,
  kind: "file" | "directory",
): Promise<void> {
  const symlinkType =
    kind === "directory"
      ? process.platform === "win32"
        ? "junction"
        : "dir"
      : "file"
  await fs.symlink(sourcePath, targetPath, symlinkType)
}

async function isSymlinkToTarget(
  targetPath: string,
  sourcePath: string,
): Promise<boolean> {
  const targetStatus = await readPathStatus(targetPath)
  if (!targetStatus.exists || targetStatus.kind !== "symlink") return false

  const linkTarget = await fs.readlink(targetPath)
  const resolvedLinkTarget = path.resolve(path.dirname(targetPath), linkTarget)

  return resolvedLinkTarget === sourcePath
}

async function detectSourceKind(
  sourcePath: string,
): Promise<"file" | "directory"> {
  const stats = await fs.stat(sourcePath)
  return stats.isDirectory() ? "directory" : "file"
}

async function listEnvCandidates(repoRoot: string): Promise<string[]> {
  const entries = await fs.readdir(repoRoot, { withFileTypes: true })
  return entries
    .filter((entry) => entry.name === ".env" || entry.name.startsWith(".env."))
    .filter((entry) => entry.isFile() || entry.isSymbolicLink())
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right))
}

async function readPathStatus(targetPath: string): Promise<{
  exists: boolean
  kind: "file" | "directory" | "symlink"
}> {
  try {
    const stats = await fs.lstat(targetPath)

    if (stats.isSymbolicLink()) {
      return { exists: true, kind: "symlink" }
    }

    return {
      exists: true,
      kind: stats.isDirectory() ? "directory" : "file",
    }
  } catch (error) {
    const readError = error as NodeJS.ErrnoException
    if (readError.code === "ENOENT") {
      return { exists: false, kind: "file" }
    }

    throw error
  }
}
