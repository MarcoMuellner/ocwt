import path from "node:path"
import os from "node:os"
import { promises as fs } from "node:fs"

import { afterEach, describe, expect, it } from "vitest"

import { ERROR_CODES } from "../src/lib/errors.js"
import {
  ensureSessionForDirectory,
  findSessionByDirectory,
  listSessions,
  type SessionClient,
  type SessionSummary,
} from "../src/lib/session.js"

const tempDirectories: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirectories
      .splice(0)
      .map((directory) => fs.rm(directory, { recursive: true, force: true })),
  )
})

function createClient(initialSessions: SessionSummary[] = []): SessionClient & {
  created: SessionSummary[]
  selected: string[]
} {
  const sessions = [...initialSessions]
  const created: SessionSummary[] = []
  const selected: string[] = []

  return {
    created,
    selected,
    async listSessions() {
      return sessions
    },
    async createSession(input) {
      const session = {
        id: `session-${sessions.length + 1}`,
        directory: input.directory,
        ...(input.title === undefined ? {} : { title: input.title }),
      }
      sessions.push(session)
      created.push(session)
      return session
    },
    async selectSession(input) {
      selected.push(input.sessionID)
    },
  }
}

describe("session helpers", () => {
  it("reuses an existing session for the target directory", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    tempDirectories.push(directory)

    const client = createClient([{ id: "session-1", directory }])
    const result = await ensureSessionForDirectory(
      client,
      path.join(directory, "."),
    )

    expect(result).toMatchObject({
      sessionID: "session-1",
      created: false,
      switchedSession: false,
      headless: true,
    })
    expect(client.created).toHaveLength(0)
  })

  it("creates a session when no existing directory match is found", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    tempDirectories.push(directory)

    const client = createClient()
    const result = await ensureSessionForDirectory(client, directory, {
      title: "feat/native-open",
    })

    expect(result).toMatchObject({
      sessionID: "session-1",
      created: true,
      switchedSession: false,
      headless: true,
    })
    expect(client.created[0]).toMatchObject({
      directory: result.directory,
      title: "feat/native-open",
    })
  })

  it("switches the session when interactive mode is enabled", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    tempDirectories.push(directory)

    const client = createClient([{ id: "session-1", directory }])
    const result = await ensureSessionForDirectory(client, directory, {
      interactive: true,
    })

    expect(result).toMatchObject({
      sessionID: "session-1",
      switchedSession: true,
      headless: false,
    })
    expect(client.selected).toEqual(["session-1"])
  })

  it("maps creation failures to SESSION_CREATE_FAILED", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    tempDirectories.push(directory)

    const client: SessionClient = {
      async listSessions() {
        return []
      },
      async createSession() {
        throw new Error("boom")
      },
    }

    await expect(
      ensureSessionForDirectory(client, directory),
    ).rejects.toMatchObject({
      code: ERROR_CODES.sessionCreateFailed,
    })
  })

  it("maps switch failures to SESSION_SWITCH_FAILED", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    tempDirectories.push(directory)

    const client: SessionClient = {
      async listSessions() {
        return [{ id: "session-1", directory }]
      },
      async createSession() {
        throw new Error("should not create")
      },
      async selectSession() {
        throw new Error("switch failed")
      },
    }

    await expect(
      ensureSessionForDirectory(client, directory, { interactive: true }),
    ).rejects.toMatchObject({
      code: ERROR_CODES.sessionSwitchFailed,
    })
  })

  it("filters listed sessions by canonical directory equality", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "ocwt-session-"))
    const otherDirectory = await fs.mkdtemp(
      path.join(os.tmpdir(), "ocwt-session-"),
    )
    tempDirectories.push(directory, otherDirectory)

    const client = createClient([
      { id: "session-1", directory },
      { id: "session-2", directory: otherDirectory },
    ])

    await expect(
      listSessions(client, path.join(directory, ".")),
    ).resolves.toMatchObject([{ id: "session-1" }])
    await expect(
      findSessionByDirectory(client, directory),
    ).resolves.toMatchObject({
      id: "session-1",
    })
  })
})
