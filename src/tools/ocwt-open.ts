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
import { resolveWorktreeDirectory } from "../lib/paths.js"
import { ERROR_CODES, OcwtError } from "../lib/errors.js"
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
      return stringifyEnvelope(
        ok<OpenToolSuccessData>("OK", "Reused existing worktree", {
          repoRoot,
          baseBranch,
          branch,
          worktreeDir: existingWorktree.directory,
          created: false,
          reused: true,
          symlinkMessages: [],
        }),
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

    const worktreeParent = resolveWorktreeParent(
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

    return stringifyEnvelope(
      ok<OpenToolSuccessData>("OK", "Created new worktree", {
        repoRoot,
        baseBranch,
        branch,
        worktreeDir,
        created: true,
        reused: false,
        symlinkMessages: [],
      }),
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

function resolveWorktreeParent(
  repoRoot: string,
  configuredParent?: string,
): string {
  if (configuredParent) return path.resolve(configuredParent)

  return path.join(
    path.dirname(repoRoot),
    `${path.basename(repoRoot)}_worktrees`,
  )
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
