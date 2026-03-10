import path from "node:path"
import { promises as fs } from "node:fs"

import { z } from "zod"

import {
  createWorktree,
  findRepoRoot,
  findWorktreeByBranch,
  getBaseBranch,
} from "../lib/git.js"
import { fail, ok, stringifyEnvelope } from "../lib/json.js"
import {
  hasAllowedPrefix,
  normalizeBranchName,
  toDeterministicFallback,
} from "../lib/branch.js"
import {
  resolveManagedWorktreeParent,
  resolveWorktreeDirectory,
} from "../lib/paths.js"
import { ERROR_CODES, OcwtError } from "../lib/errors.js"
import {
  ensureSessionForDirectory,
  type SessionClient,
} from "../lib/session.js"
import type { OpenToolInput, OpenToolSuccessData } from "../lib/types.js"

const OpenToolInputSchema = z.object({
  intentOrBranch: z.string().trim().min(1).optional(),
  files: z.array(z.string().trim().min(1)).optional(),
  plan: z.boolean().optional(),
  agent: z.string().trim().min(1).optional(),
  reuseOnly: z.boolean().optional(),
})

type ParsedOpenToolInput = z.output<typeof OpenToolInputSchema>

export interface OpenToolOptions {
  cwd: string
  worktreeParent?: string
  sessionClient?: SessionClient
  interactive?: boolean
}

/**
 * Opens an ocwt worktree by resolving a branch, reusing an existing worktree, or creating a new one.
 *
 * @param input - The user-provided open request.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the open outcome.
 */
export async function ocwtOpen(
  input: OpenToolInput,
  options: OpenToolOptions,
): Promise<string> {
  try {
    const parsedInput = OpenToolInputSchema.parse(input)

    if (
      !parsedInput.intentOrBranch &&
      (!parsedInput.files || parsedInput.files.length === 0)
    ) {
      return stringifyEnvelope(
        fail(
          ERROR_CODES.invalidInput,
          "Provide an intent, branch, or file list to open a worktree",
        ),
      )
    }

    await validateAttachedFiles(options.cwd, parsedInput.files)

    const repoRoot = await findRepoRoot(options.cwd)
    const baseBranch = await getBaseBranch(repoRoot)
    const branch = resolveTargetBranch(parsedInput)

    const existingWorktree = await findWorktreeByBranch(repoRoot, branch)
    if (existingWorktree) {
      const baseData: OpenToolSuccessData = {
        repoRoot,
        baseBranch,
        branch,
        worktreeDir: existingWorktree.directory,
        created: false,
        reused: true,
        symlinkMessages: [],
      }

      const sessionResult = options.sessionClient
        ? await tryEnsureSession(baseData, options)
        : undefined

      if (typeof sessionResult === "string") return sessionResult

      return stringifyEnvelope(
        ok<OpenToolSuccessData>(
          "OK",
          "Reused existing worktree",
          mergeSessionMetadata(baseData, sessionResult),
        ),
      )
    }

    if (parsedInput.reuseOnly) {
      return stringifyEnvelope(
        fail(
          ERROR_CODES.invalidInput,
          "No existing worktree matched the requested branch",
          {
            nextAction: "Retry without reuseOnly to create a new worktree",
          },
        ),
      )
    }

    const worktreeParent = resolveManagedWorktreeParent(
      repoRoot,
      options.worktreeParent,
    )
    await fs.mkdir(worktreeParent, { recursive: true })

    const worktreeDir = resolveWorktreeDirectory(worktreeParent, branch)
    await createWorktree(repoRoot, {
      branch,
      directory: worktreeDir,
      startPoint: baseBranch,
    })

    const baseData: OpenToolSuccessData = {
      repoRoot,
      baseBranch,
      branch,
      worktreeDir,
      created: true,
      reused: false,
      symlinkMessages: [],
    }

    const sessionResult = options.sessionClient
      ? await tryEnsureSession(baseData, options)
      : undefined

    if (typeof sessionResult === "string") return sessionResult

    return stringifyEnvelope(
      ok<OpenToolSuccessData>(
        "OK",
        "Created new worktree",
        mergeSessionMetadata(baseData, sessionResult),
      ),
    )
  } catch (error) {
    return stringifyEnvelope(handleOpenError(error))
  }
}

/**
 * Keeps the previous scaffold entrypoint name while delegating to the real implementation.
 *
 * @param input - The user-provided open request.
 * @param options - Runtime options that provide repository context.
 * @returns A JSON result envelope describing the open outcome.
 */
export async function ocwtOpenScaffold(
  input: OpenToolInput,
  options: OpenToolOptions,
): Promise<string> {
  return ocwtOpen(input, options)
}

async function validateAttachedFiles(
  cwd: string,
  files?: string[],
): Promise<void> {
  if (!files) return

  for (const file of files) {
    const resolvedPath = path.resolve(cwd, file)
    const exists = await fs
      .access(resolvedPath)
      .then(() => true)
      .catch(() => false)

    if (!exists) {
      throw new OcwtError(
        ERROR_CODES.fileNotFound,
        `Attached file not found: ${file}`,
      )
    }
  }
}

function resolveTargetBranch(input: ParsedOpenToolInput): string {
  const branchCandidate =
    input.intentOrBranch?.trim() || input.files?.join("-") || ""
  const normalized = normalizeBranchName(branchCandidate)

  if (normalized && hasAllowedPrefix(normalized)) return normalized

  const branchBody = normalized.replace(/^[^/]+\//, "")
  if (branchBody) return `feat/${branchBody}`

  return toDeterministicFallback(branchCandidate)
}

async function tryEnsureSession(
  baseData: OpenToolSuccessData,
  options: OpenToolOptions,
) {
  try {
    return await ensureSessionForDirectory(
      options.sessionClient!,
      baseData.worktreeDir,
      {
        ...(options.interactive === undefined
          ? {}
          : { interactive: options.interactive }),
        title: baseData.branch,
      },
    )
  } catch (error) {
    if (
      error instanceof OcwtError &&
      (error.code === ERROR_CODES.sessionCreateFailed ||
        error.code === ERROR_CODES.sessionSwitchFailed)
    ) {
      return stringifyEnvelope(
        fail<OpenToolSuccessData>(error.code, error.message, {
          data: baseData,
          nextAction:
            "The worktree is ready, but the session step failed. Re-run open or attach to the returned worktree directory.",
        }),
      )
    }

    throw error
  }
}

function mergeSessionMetadata(
  baseData: OpenToolSuccessData,
  sessionResult?: {
    sessionID: string
    switchedSession: boolean
  },
): OpenToolSuccessData {
  return {
    ...baseData,
    ...(sessionResult?.sessionID === undefined
      ? {}
      : { sessionID: sessionResult.sessionID }),
    ...(sessionResult?.switchedSession === undefined
      ? {}
      : { switchedSession: sessionResult.switchedSession }),
  }
}

function handleOpenError(error: unknown) {
  if (error instanceof z.ZodError) {
    return fail(
      ERROR_CODES.invalidInput,
      error.issues[0]?.message || "Invalid ocwt_open input",
    )
  }

  if (error instanceof OcwtError) {
    return fail(error.code, error.message)
  }

  const message =
    error instanceof Error ? error.message : "Unknown ocwt_open error"
  return fail(ERROR_CODES.worktreeCreateFailed, message)
}
