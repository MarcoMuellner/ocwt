import type { Plugin } from "@opencode-ai/plugin"
import { tool, type ToolContext } from "@opencode-ai/plugin/tool"

import { INJECTED_COMMANDS } from "./plugin-commands.js"
import { ocwtClose } from "./tools/ocwt-close.js"
import { ocwtList } from "./tools/ocwt-list.js"
import { ocwtOpen } from "./tools/ocwt-open.js"

export const plugin: Plugin = async () => {
  return {
    config: async (input) => {
      input.command ??= {}

      for (const [name, command] of Object.entries(INJECTED_COMMANDS)) {
        input.command[name] = {
          description: command.description,
          template: command.template,
          agent: command.agent,
        }
      }
    },
    tool: {
      ocwt_open: tool({
        description: "Open or reuse an ocwt worktree",
        args: {
          intentOrBranch: tool.schema.string().optional(),
          files: tool.schema.array(tool.schema.string()).optional(),
          plan: tool.schema.boolean().optional(),
          agent: tool.schema.string().optional(),
          reuseOnly: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            intentOrBranch?: string
            files?: string[]
            plan?: boolean
            agent?: string
            reuseOnly?: boolean
          },
          context: ToolContext,
        ) {
          return await ocwtOpen(args, {
            cwd: context.directory,
          })
        },
      }),
      ocwt_close: tool({
        description: "Close an ocwt worktree safely",
        args: {
          branchOrPath: tool.schema.string().optional(),
          force: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            branchOrPath?: string
            force?: boolean
          },
          context: ToolContext,
        ) {
          return await ocwtClose(args, {
            cwd: context.directory,
          })
        },
      }),
      ocwt_list: tool({
        description: "List ocwt-managed worktrees",
        args: {
          includeSessions: tool.schema.boolean().optional(),
        },
        async execute(
          args: {
            includeSessions?: boolean
          },
          context: ToolContext,
        ) {
          return await ocwtList(args, {
            cwd: context.directory,
          })
        },
      }),
    },
  }
}

export default plugin
