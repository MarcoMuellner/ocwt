import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import {
  branchToWorktreeDirectoryName,
  canonicalizePath,
  isWithinParentDirectory,
  matchesManagedWorktreePath,
  resolveWorktreeDirectory,
} from "../src/lib/paths.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

describe("path helpers", () => {
  it("maps branch names to deterministic directory names", () => {
    expect(branchToWorktreeDirectoryName("feat/native/ocwt")).toBe(
      "feat__native__ocwt",
    )
  })

  it("resolves worktree directories under the configured parent", () => {
    expect(resolveWorktreeDirectory("/tmp/ocwt", "feat/native-open")).toBe(
      path.resolve("/tmp/ocwt", "feat__native-open"),
    )
  })

  it("canonicalizes relative paths into absolute comparison-safe values", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-paths-"))
    tempDirectories.push(directory)

    expect(await canonicalizePath(path.join(directory, "."))).toBe(
      await canonicalizePath(directory),
    )
  })

  it("allows targets inside the configured parent directory", async () => {
    const parentDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(parentDirectory)

    const targetDirectory = path.join(parentDirectory, "feat__native-open")
    await fs.mkdir(targetDirectory)

    await expect(
      isWithinParentDirectory(parentDirectory, targetDirectory),
    ).resolves.toBe(true)
  })

  it("rejects targets outside the configured parent directory", async () => {
    const parentDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    const outsideDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-outside-"),
    )
    tempDirectories.push(parentDirectory, outsideDirectory)

    await expect(
      isWithinParentDirectory(parentDirectory, outsideDirectory),
    ).resolves.toBe(false)
  })

  it("rejects sibling paths that only share the same prefix", async () => {
    const rootDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(rootDirectory)

    const parentDirectory = path.join(rootDirectory, "workspace")
    const siblingDirectory = path.join(rootDirectory, "workspace-copy")
    await fs.mkdir(parentDirectory)
    await fs.mkdir(siblingDirectory)

    await expect(
      isWithinParentDirectory(parentDirectory, siblingDirectory),
    ).resolves.toBe(false)
  })

  it("matches managed paths even when the candidate uses dot segments", async () => {
    const parentDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(parentDirectory)

    const managedDirectory = resolveWorktreeDirectory(
      parentDirectory,
      "feat/native-open",
    )
    await fs.mkdir(managedDirectory)

    const dottedPath = path.join(managedDirectory, ".")

    await expect(
      matchesManagedWorktreePath(
        parentDirectory,
        "feat/native-open",
        dottedPath,
      ),
    ).resolves.toBe(true)
  })

  it("matches only the managed path for a branch", async () => {
    const parentDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-parent-"),
    )
    tempDirectories.push(parentDirectory)

    const managedDirectory = resolveWorktreeDirectory(
      parentDirectory,
      "feat/native-open",
    )
    const otherDirectory = path.join(parentDirectory, "feat__other")
    await fs.mkdir(managedDirectory)
    await fs.mkdir(otherDirectory)

    await expect(
      matchesManagedWorktreePath(
        parentDirectory,
        "feat/native-open",
        managedDirectory,
      ),
    ).resolves.toBe(true)

    await expect(
      matchesManagedWorktreePath(
        parentDirectory,
        "feat/native-open",
        otherDirectory,
      ),
    ).resolves.toBe(false)
  })
})
