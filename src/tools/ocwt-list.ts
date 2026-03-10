import { z } from "zod"

import { loadOcwtConfig, resolveToolConfig } from "../lib/config.js"
import { ERROR_CODES, OcwtError } from "../lib/errors.js"
import { findRepoRoot, getBaseBranch, listWorktrees } from "../lib/git.js"
import { fail, ok, stringifyEnvelope } from "../lib/json.js"
import {
  isWithinParentDirectory,
  resolveManagedWorktreeParent,
} from "../lib/paths.js"
import { findSessionByDirectory, type SessionClient } from "../lib/session.js"
import type {
  ListToolEntry,
  ListToolInput,
  ListToolSuccessData,
} from "../lib/types.js"

const ListToolInputSchema = z.object({
  includeSessions: z.boolean().optional(),
})

export interface ListToolOptions {
  cwd: string
  worktreeParent?: string
  configPath?: string
  sessionClient?: SessionClient
}

/**
 * Lists ocwt worktrees and optionally enriches them with session metadata.
 *
 * @param input - Controls whether session metadata should be included.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the known worktree entries.
 */
export async function ocwtList(
  input: ListToolInput,
  options: ListToolOptions,
): Promise<string> {
  try {
    const parsedInput = ListToolInputSchema.parse(input)
    const repoRoot = await findRepoRoot(options.cwd)
    const config = resolveToolConfig(
      await loadOcwtConfig(options),
      buildToolConfigOverrides(options.worktreeParent),
    )
    const baseBranch = await getBaseBranch(repoRoot)
    const managedParent = resolveManagedWorktreeParent(
      repoRoot,
      config.worktreeParent,
    )
    const worktrees = await listWorktrees(repoRoot)

    const entries: ListToolEntry[] = []

    for (const worktree of worktrees) {
      const isPrimary = worktree.directory === repoRoot
      const withinManagedParent = await isWithinParentDirectory(
        managedParent,
        worktree.directory,
      )

      if (!isPrimary && !withinManagedParent) continue

      const branch = worktree.branch ?? "(detached)"
      const sessionID =
        parsedInput.includeSessions && options.sessionClient
          ? (
              await findSessionByDirectory(
                options.sessionClient,
                worktree.directory,
              )
            )?.id
          : undefined

      entries.push({
        branch,
        directory: worktree.directory,
        protected: isPrimary || ["main", "master", baseBranch].includes(branch),
        ...(sessionID === undefined ? {} : { sessionID }),
      })
    }

    entries.sort((left, right) => left.directory.localeCompare(right.directory))

    return stringifyEnvelope(
      ok<ListToolSuccessData>("OK", "Listed worktrees", {
        repoRoot,
        baseBranch,
        entries,
      }),
    )
  } catch (error) {
    return stringifyEnvelope(handleListError(error))
  }
}

/**
 * Keeps the previous scaffold entrypoint name while delegating to the real implementation.
 *
 * @param input - Controls whether session metadata should be included.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the known worktree entries.
 */
export async function ocwtListScaffold(
  input: ListToolInput,
  options: ListToolOptions,
): Promise<string> {
  return ocwtList(input, options)
}

function handleListError(error: unknown) {
  if (error instanceof z.ZodError) {
    return fail(
      ERROR_CODES.invalidInput,
      error.issues[0]?.message || "Invalid ocwt_list input",
    )
  }

  if (error instanceof OcwtError) {
    return fail(error.code, error.message)
  }

  const message =
    error instanceof Error ? error.message : "Unknown ocwt_list error"
  return fail(ERROR_CODES.targetNotFound, message)
}

function buildToolConfigOverrides(worktreeParent?: string) {
  return worktreeParent === undefined ? {} : { worktreeParent }
}
