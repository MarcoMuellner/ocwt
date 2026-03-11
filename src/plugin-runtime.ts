import { createOpencodeClient } from "@opencode-ai/sdk/v2/client"
import type { PluginInput } from "@opencode-ai/plugin"

import type { SessionClient, SessionSummary } from "./lib/session.js"

/**
 * Creates a session client backed by the live OpenCode server so plugin tools can
 * create sessions, discover sessions by worktree directory, and submit prompts.
 * TUI switching is handled after tool execution so the UI lands in the new session
 * only after the tool call completes.
 *
 * @param input - The current plugin runtime context provided by OpenCode.
 * @returns A session client adapter for ocwt tool orchestration.
 */
export function createPluginSessionClient(input: PluginInput): SessionClient {
  return {
    async listSessions({ directory }) {
      const response = await createDirectoryClient(
        input,
        directory,
      ).session.list({
        limit: 100,
      })

      if (response.error) throw new Error(extractErrorMessage(response.error))
      if (response.data === undefined) {
        throw new Error("Session list returned no data")
      }

      return response.data.map(toSessionSummary)
    },
    async createSession({ directory, title }) {
      const response =
        title === undefined
          ? await createDirectoryClient(input, directory).session.create()
          : await createDirectoryClient(input, directory).session.create({
              title,
            })

      if (response.error) throw new Error(extractErrorMessage(response.error))
      if (response.data === undefined) {
        throw new Error("Session creation returned no data")
      }

      return toSessionSummary(response.data)
    },
    async promptSession({ sessionID, directory, text, agent }) {
      const response = await createDirectoryClient(
        input,
        directory,
      ).session.prompt({
        sessionID,
        ...(agent === undefined ? {} : { agent }),
        parts: [
          {
            type: "text",
            text,
          },
        ],
      })

      if (response.error) throw new Error(extractErrorMessage(response.error))
      if (response.data === undefined) {
        throw new Error("Session prompt returned no data")
      }
    },
  }
}

/**
 * Selects a TUI session after the current tool execution finishes.
 *
 * @param input - The current plugin runtime context provided by OpenCode.
 * @param sessionID - The session that should become active in the TUI.
 */
export async function selectPluginSession(
  input: PluginInput,
  sessionID: string,
): Promise<void> {
  const response = await createRootClient(input).tui.selectSession({
    sessionID,
  })

  if (response.error) throw new Error(extractErrorMessage(response.error))
}

function createRootClient(input: PluginInput) {
  return createOpencodeClient({
    baseUrl: input.serverUrl.toString(),
    directory: input.directory,
  })
}

function createDirectoryClient(input: PluginInput, directory: string) {
  return createOpencodeClient({
    baseUrl: input.serverUrl.toString(),
    directory,
  })
}

function toSessionSummary(session: {
  id: string
  directory: string
  title?: string
}): SessionSummary {
  return {
    id: session.id,
    directory: session.directory,
    ...(session.title === undefined ? {} : { title: session.title }),
  }
}

function extractErrorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = Reflect.get(error, "message")
    if (typeof message === "string") return message
  }

  return "Unknown OpenCode SDK error"
}
