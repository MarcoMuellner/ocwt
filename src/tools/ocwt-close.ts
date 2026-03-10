import path from "node:path"

import { z } from "zod"

import { loadOcwtConfig, resolveToolConfig } from "../lib/config.js"
import {
  deleteLocalBranch,
  findRepoRoot,
  findWorktreeByBranch,
  findWorktreeContainingPath,
  findWorktreeByPath,
  getBaseBranch,
  getCurrentBranch,
  getPrimaryWorktreeDirectory,
  removeWorktree,
} from "../lib/git.js"
import { ERROR_CODES, OcwtError } from "../lib/errors.js"
import { fail, ok, stringifyEnvelope } from "../lib/json.js"
import { canonicalizePath, isWithinParentDirectory } from "../lib/paths.js"
import type { CloseToolInput, CloseToolSuccessData } from "../lib/types.js"

const CloseToolInputSchema = z.object({
  branchOrPath: z.string().trim().min(1).optional(),
  force: z.boolean().optional(),
})

type ParsedCloseToolInput = z.output<typeof CloseToolInputSchema>

export interface CloseToolOptions {
  cwd: string
  worktreeParent?: string
  configPath?: string
}

/**
 * Closes an ocwt worktree by resolving a managed target, removing the worktree, and deleting its branch.
 *
 * @param input - The requested branch or path to close.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the close outcome.
 */
export async function ocwtClose(
  input: CloseToolInput,
  options: CloseToolOptions,
): Promise<string> {
  try {
    const parsedInput = CloseToolInputSchema.parse(input)
    const repoRoot = await findRepoRoot(options.cwd)
    const config = resolveToolConfig(
      await loadOcwtConfig(options),
      buildToolConfigOverrides(options.worktreeParent),
    )
    const primaryWorktreeDir = await getPrimaryWorktreeDirectory(repoRoot)
    const baseBranch = await getBaseBranch(primaryWorktreeDir)
    const target = await resolveCloseTarget(
      parsedInput,
      buildCloseOptions(options, config.worktreeParent),
      repoRoot,
      primaryWorktreeDir,
    )

    if (!target.branch) {
      return stringifyEnvelope(
        fail(
          ERROR_CODES.targetNotFound,
          "The target worktree does not have a removable local branch",
        ),
      )
    }

    if (target.isPrimaryWorktree) {
      return stringifyEnvelope(
        fail(
          ERROR_CODES.protectedBranch,
          "The primary repository worktree cannot be closed",
          {
            data: buildCloseData(
              repoRoot,
              target.branch,
              target.directory,
              false,
              false,
            ),
          },
        ),
      )
    }

    if (["main", "master", baseBranch].includes(target.branch)) {
      return stringifyEnvelope(
        fail(
          ERROR_CODES.protectedBranch,
          `Branch ${target.branch} is protected and cannot be closed`,
          {
            data: buildCloseData(
              repoRoot,
              target.branch,
              target.directory,
              false,
              false,
            ),
          },
        ),
      )
    }

    await removeWorktree(
      primaryWorktreeDir,
      target.directory,
      parsedInput.force ?? false,
    )
    await deleteLocalBranch(primaryWorktreeDir, target.branch, true)

    return stringifyEnvelope(
      ok<CloseToolSuccessData>("OK", "Closed worktree", {
        repoRoot,
        branch: target.branch,
        worktreeDir: target.directory,
        removedWorktree: true,
        deletedBranch: true,
      }),
    )
  } catch (error) {
    return stringifyEnvelope(handleCloseError(error))
  }
}

/**
 * Keeps the previous scaffold entrypoint name while delegating to the real implementation.
 *
 * @param input - The requested branch or path to close.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the close outcome.
 */
export async function ocwtCloseScaffold(
  input: CloseToolInput,
  options: CloseToolOptions,
): Promise<string> {
  return ocwtClose(input, options)
}

interface ResolvedCloseTarget {
  branch?: string
  directory: string
  isPrimaryWorktree: boolean
}

async function resolveCloseTarget(
  input: ParsedCloseToolInput,
  options: CloseToolOptions,
  repoRoot: string,
  primaryWorktreeDir: string,
): Promise<ResolvedCloseTarget> {
  if (input.branchOrPath) {
    const worktree = await findWorktreeByBranch(repoRoot, input.branchOrPath)
    if (worktree) {
      return enforceManagedParent(
        {
          directory: worktree.directory,
          isPrimaryWorktree:
            (await canonicalizePath(worktree.directory)) === primaryWorktreeDir,
          ...(worktree.branch === undefined ? {} : { branch: worktree.branch }),
        },
        options.worktreeParent,
      )
    }

    if (looksLikePath(input.branchOrPath)) {
      const resolvedPath = path.resolve(options.cwd, input.branchOrPath)
      return resolveTargetByPath(
        repoRoot,
        resolvedPath,
        options.worktreeParent,
        primaryWorktreeDir,
      )
    }

    throw new OcwtError(
      ERROR_CODES.targetNotFound,
      `No worktree found for branch ${input.branchOrPath}`,
    )
  }

  const currentBranch = await getCurrentBranch(options.cwd)
  const currentWorktree = await findWorktreeContainingPath(
    repoRoot,
    options.cwd,
  )
  if (!currentWorktree) {
    throw new OcwtError(
      ERROR_CODES.targetNotFound,
      "No managed worktree target could be resolved",
    )
  }

  const resolvedBranch = currentWorktree.branch ?? currentBranch

  return enforceManagedParent(
    {
      directory: currentWorktree.directory,
      isPrimaryWorktree:
        (await canonicalizePath(currentWorktree.directory)) ===
        primaryWorktreeDir,
      ...(resolvedBranch === undefined ? {} : { branch: resolvedBranch }),
    },
    options.worktreeParent,
  )
}

async function resolveTargetByPath(
  repoRoot: string,
  targetPath: string,
  worktreeParent?: string,
  primaryWorktreeDir?: string,
): Promise<ResolvedCloseTarget> {
  const worktree = await findWorktreeByPath(repoRoot, targetPath)
  if (!worktree) {
    throw new OcwtError(
      ERROR_CODES.targetNotFound,
      `No worktree found for path ${targetPath}`,
    )
  }

  return enforceManagedParent(
    {
      directory: worktree.directory,
      isPrimaryWorktree:
        (await canonicalizePath(worktree.directory)) ===
        (primaryWorktreeDir ?? repoRoot),
      ...(worktree.branch === undefined ? {} : { branch: worktree.branch }),
    },
    worktreeParent,
  )
}

async function enforceManagedParent(
  target: ResolvedCloseTarget,
  worktreeParent?: string,
): Promise<ResolvedCloseTarget> {
  if (target.isPrimaryWorktree) return target
  if (!worktreeParent) return target

  const withinParent = await isWithinParentDirectory(
    worktreeParent,
    target.directory,
  )
  if (!withinParent) {
    throw new OcwtError(
      ERROR_CODES.targetNotFound,
      "The requested target is outside the managed worktree parent",
    )
  }

  return target
}

function looksLikePath(value: string): boolean {
  return value.includes(path.sep) || value.startsWith(".")
}

function buildCloseData(
  repoRoot: string,
  branch: string,
  worktreeDir: string,
  removedWorktree: boolean,
  deletedBranch: boolean,
): CloseToolSuccessData {
  return {
    repoRoot,
    branch,
    worktreeDir,
    removedWorktree,
    deletedBranch,
  }
}

function buildCloseOptions(
  options: CloseToolOptions,
  worktreeParent?: string,
): CloseToolOptions {
  return {
    cwd: options.cwd,
    ...(options.configPath === undefined
      ? {}
      : { configPath: options.configPath }),
    ...(worktreeParent === undefined ? {} : { worktreeParent }),
  }
}

function buildToolConfigOverrides(worktreeParent?: string) {
  return worktreeParent === undefined ? {} : { worktreeParent }
}

function handleCloseError(error: unknown) {
  if (error instanceof z.ZodError) {
    return fail(
      ERROR_CODES.invalidInput,
      error.issues[0]?.message || "Invalid ocwt_close input",
    )
  }

  if (error instanceof OcwtError) {
    return fail(error.code, error.message)
  }

  const message =
    error instanceof Error ? error.message : "Unknown ocwt_close error"
  return fail(ERROR_CODES.removeFailed, message)
}
