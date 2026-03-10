import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import plugin from "../src/plugin.js"
import { runGit } from "../src/lib/git.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

async function createRepo(): Promise<string> {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-plugin-"))
  tempDirectories.push(directory)

  await runGit(directory, ["init", "-b", "main"])
  await runGit(directory, ["config", "user.name", "ocwt test"])
  await runGit(directory, ["config", "user.email", "ocwt@example.com"])
  await fs.writeFile(path.join(directory, "README.md"), "seed\n", "utf8")
  await runGit(directory, ["add", "README.md"])
  await runGit(directory, ["commit", "-m", "init"])

  return directory
}

describe("plugin entrypoint", () => {
  it("injects the ocwt commands into OpenCode config", async () => {
    const repo = await createRepo()
    const hooks = await plugin({
      client: {} as never,
      project: { id: "project", worktree: repo } as never,
      directory: repo,
      worktree: repo,
      serverUrl: new URL("http://localhost:4096"),
      $: {} as never,
    })

    const config = {} as Record<string, unknown>
    await hooks.config?.(config as never)

    expect(config).toMatchObject({
      command: {
        "wt-open": expect.objectContaining({ description: expect.any(String) }),
        "wt-build": expect.objectContaining({
          description: expect.any(String),
        }),
        "wt-close": expect.objectContaining({
          description: expect.any(String),
        }),
        "wt-list": expect.objectContaining({ description: expect.any(String) }),
      },
    })
  })

  it("registers ocwt tools", async () => {
    const repo = await createRepo()
    const hooks = await plugin({
      client: {} as never,
      project: { id: "project", worktree: repo } as never,
      directory: repo,
      worktree: repo,
      serverUrl: new URL("http://localhost:4096"),
      $: {} as never,
    })

    expect(Object.keys(hooks.tool ?? {}).sort()).toEqual([
      "ocwt_close",
      "ocwt_list",
      "ocwt_open",
    ])
  })
})
