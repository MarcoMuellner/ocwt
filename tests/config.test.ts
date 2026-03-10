import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import {
  getDefaultOcwtConfig,
  getDefaultOcwtConfigPath,
  loadOcwtConfig,
  resolveToolConfig,
} from "../src/lib/config.js"
import { runGit } from "../src/lib/git.js"
import { ocwtList } from "../src/tools/ocwt-list.js"
import { ocwtOpen } from "../src/tools/ocwt-open.js"
import type { ResultEnvelope } from "../src/lib/types.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

function parseEnvelope(input: string): ResultEnvelope<Record<string, unknown>> {
  return JSON.parse(input) as ResultEnvelope<Record<string, unknown>>
}

async function createRepo(): Promise<string> {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-config-"))
  tempDirectories.push(directory)

  await runGit(directory, ["init", "-b", "main"])
  await runGit(directory, ["config", "user.name", "ocwt test"])
  await runGit(directory, ["config", "user.email", "ocwt@example.com"])
  await fs.writeFile(path.join(directory, "README.md"), "seed\n", "utf8")
  await runGit(directory, ["add", "README.md"])
  await runGit(directory, ["commit", "-m", "init"])

  return directory
}

describe("config helpers", () => {
  it("returns defaults when the config file is missing", async () => {
    const missingConfigPath = path.join(os.tmpdir(), "ocwt-missing-config.json")

    await expect(
      loadOcwtConfig({ configPath: missingConfigPath }),
    ).resolves.toEqual(getDefaultOcwtConfig())
  })

  it("loads normalized config values from disk", async () => {
    const directory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-file-"),
    )
    tempDirectories.push(directory)
    const configPath = path.join(directory, "config.json")

    await fs.writeFile(
      configPath,
      JSON.stringify({
        agent: "build",
        auto_plan: true,
        auto_pull: true,
        worktree_parent: "/tmp/worktrees",
        symlink_opencode: false,
        symlink_idea: true,
        symlink_env: true,
      }),
      "utf8",
    )

    await expect(loadOcwtConfig({ configPath })).resolves.toEqual({
      agent: "build",
      autoPlan: true,
      autoPull: true,
      worktreeParent: "/tmp/worktrees",
      symlinkOpencode: false,
      symlinkIdea: true,
      symlinkEnv: true,
    })
  })

  it("rejects malformed config files", async () => {
    const directory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-file-"),
    )
    tempDirectories.push(directory)
    const configPath = path.join(directory, "config.json")

    await fs.writeFile(configPath, "{not-json", "utf8")

    await expect(loadOcwtConfig({ configPath })).rejects.toMatchObject({
      code: "INVALID_INPUT",
    })
  })

  it("lets explicit tool overrides win over file config", () => {
    expect(
      resolveToolConfig(
        {
          agent: "build",
          autoPlan: false,
          autoPull: false,
          worktreeParent: "/tmp/from-config",
          symlinkOpencode: true,
          symlinkIdea: false,
          symlinkEnv: false,
        },
        { worktreeParent: "/tmp/from-tool" },
      ),
    ).toMatchObject({
      worktreeParent: "/tmp/from-tool",
      agent: "build",
    })
  })

  it("builds the legacy default config path from the home directory", () => {
    expect(getDefaultOcwtConfigPath("/Users/example")).toBe(
      path.join("/Users/example", ".config", "ocwt", "config.json"),
    )
  })
})

describe("tool config integration", () => {
  it("uses worktree_parent from config when open does not receive an explicit parent", async () => {
    const repo = await createRepo()
    const configDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-file-"),
    )
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-parent-"),
    )
    tempDirectories.push(configDirectory, worktreeParent)
    const configPath = path.join(configDirectory, "config.json")

    await fs.writeFile(
      configPath,
      JSON.stringify({ worktree_parent: worktreeParent }),
      "utf8",
    )

    const result = parseEnvelope(
      await ocwtOpen(
        { intentOrBranch: "feat/from-config" },
        { cwd: repo, configPath },
      ),
    )

    expect(result.ok).toBe(true)
    expect(result.data?.worktreeDir).toBe(
      path.join(worktreeParent, "feat__from-config"),
    )
  })

  it("uses worktree_parent from config when listing managed worktrees", async () => {
    const repo = await createRepo()
    const configDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-file-"),
    )
    const worktreeParent = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-config-parent-"),
    )
    tempDirectories.push(configDirectory, worktreeParent)
    const configPath = path.join(configDirectory, "config.json")

    await fs.writeFile(
      configPath,
      JSON.stringify({ worktree_parent: worktreeParent }),
      "utf8",
    )

    await ocwtOpen(
      { intentOrBranch: "feat/list-from-config" },
      { cwd: repo, configPath },
    )

    const result = parseEnvelope(await ocwtList({}, { cwd: repo, configPath }))
    const entries = result.data?.entries as
      | Array<{ branch: string }>
      | undefined

    expect(result.ok).toBe(true)
    expect(entries?.map((entry) => entry.branch)).toContain(
      "feat/list-from-config",
    )
  })
})
