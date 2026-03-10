import os from "node:os"
import path from "node:path"
import { promises as fs } from "node:fs"

import { z } from "zod"

import { ERROR_CODES, OcwtError } from "./errors.js"

const FileConfigSchema = z
  .object({
    agent: z.string().trim().min(1).optional(),
    auto_plan: z.boolean().optional(),
    auto_pull: z.boolean().optional(),
    worktree_parent: z.string().trim().min(1).optional(),
    symlink_opencode: z.boolean().optional(),
    symlink_idea: z.boolean().optional(),
    symlink_env: z.boolean().optional(),
  })
  .passthrough()

export interface OcwtConfig {
  agent?: string
  autoPlan: boolean
  autoPull: boolean
  worktreeParent?: string
  symlinkOpencode: boolean
  symlinkIdea: boolean
  symlinkEnv: boolean
}

export interface ConfigLoadOptions {
  configPath?: string
}

export interface ToolConfigOverrides {
  worktreeParent?: string
}

/**
 * Returns the default config path used by the legacy ocwt implementation.
 *
 * @param homeDirectory - Optional home directory override for tests.
 * @returns The absolute path to `~/.config/ocwt/config.json`.
 */
export function getDefaultOcwtConfigPath(homeDirectory = os.homedir()): string {
  return path.join(homeDirectory, ".config", "ocwt", "config.json")
}

/**
 * Loads ocwt config from disk, applying defaults when the file is missing.
 *
 * @param options - Optional config path overrides.
 * @returns The normalized config object used by the native implementation.
 * @throws OcwtError When the config file exists but cannot be parsed or validated.
 */
export async function loadOcwtConfig(
  options: ConfigLoadOptions = {},
): Promise<OcwtConfig> {
  const configPath = options.configPath ?? getDefaultOcwtConfigPath()

  let fileContent: string
  try {
    fileContent = await fs.readFile(configPath, "utf8")
  } catch (error) {
    const readError = error as NodeJS.ErrnoException
    if (readError.code === "ENOENT") return getDefaultOcwtConfig()

    throw new OcwtError(
      ERROR_CODES.invalidInput,
      `Could not read ocwt config at ${configPath}`,
    )
  }

  try {
    const parsedFile = FileConfigSchema.parse(JSON.parse(fileContent))
    return {
      autoPlan: parsedFile.auto_plan ?? false,
      autoPull: parsedFile.auto_pull ?? false,
      symlinkOpencode: parsedFile.symlink_opencode ?? true,
      symlinkIdea: parsedFile.symlink_idea ?? false,
      symlinkEnv: parsedFile.symlink_env ?? false,
      ...(parsedFile.agent === undefined ? {} : { agent: parsedFile.agent }),
      ...(parsedFile.worktree_parent === undefined
        ? {}
        : { worktreeParent: parsedFile.worktree_parent }),
    }
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof z.ZodError) {
      throw new OcwtError(
        ERROR_CODES.invalidInput,
        `Invalid ocwt config at ${configPath}`,
      )
    }

    throw error
  }
}

/**
 * Returns the built-in defaults used when no ocwt config file is present.
 *
 * @returns The default normalized ocwt config.
 */
export function getDefaultOcwtConfig(): OcwtConfig {
  return {
    autoPlan: false,
    autoPull: false,
    symlinkOpencode: true,
    symlinkIdea: false,
    symlinkEnv: false,
  }
}

/**
 * Applies explicit tool overrides on top of loaded config values.
 *
 * @param config - The loaded config values.
 * @param overrides - Explicit tool-level overrides.
 * @returns The resolved config values for a single tool invocation.
 */
export function resolveToolConfig(
  config: OcwtConfig,
  overrides: ToolConfigOverrides,
): OcwtConfig {
  return {
    ...config,
    ...(overrides.worktreeParent === undefined
      ? {}
      : { worktreeParent: overrides.worktreeParent }),
  }
}
