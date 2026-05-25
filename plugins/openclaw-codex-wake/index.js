import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import {
  TOOL_NAME,
  commandStatusSummary,
  createWakeRecord,
  summarizeScheduleResult,
} from "./lib/scheduler.js";

function jsonToolResult(payload) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2),
      },
    ],
    details: payload,
  };
}

function createScheduleTool(api, toolContext) {
  return {
    name: TOOL_NAME,
    label: "Schedule Wake",
    description:
      "Schedule a durable codex-wake OpenClaw Gateway wake for the current live OpenClaw session. Use for delayed follow-up work; prompts must be short, idempotent, and evidence-oriented.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        trigger: {
          type: "string",
          enum: ["after", "at"],
          description: "Use after for a relative delay or at for an ISO timestamp.",
        },
        delay: {
          type: "string",
          description: "Relative delay for trigger=after, such as 30s, 15m, or 1h30m.",
        },
        timestamp: {
          type: "string",
          description: "ISO-8601 timestamp with timezone for trigger=at.",
        },
        prompt: {
          type: "string",
          minLength: 1,
          description:
            "Wake prompt. Keep it short and idempotent; tell the future agent what evidence to inspect first.",
        },
        wakeRoot: {
          type: "string",
          description:
            "Optional wake root. Relative values resolve against the active workspace. Defaults to .codex/wake.",
        },
        cwd: {
          type: "string",
          description: "Optional working directory for the wake record. Defaults to the active workspace.",
        },
        deliver: {
          type: "boolean",
          description: "Whether the resumed OpenClaw turn should deliver its final reply. Defaults to true.",
        },
        timeoutSeconds: {
          type: "integer",
          minimum: 1,
          description: "OpenClaw agent turn timeout. Defaults to 600.",
        },
        gatewayTimeoutMs: {
          type: "integer",
          minimum: 1000,
          description: "Gateway CLI timeout in milliseconds. Defaults to 180000.",
        },
        model: {
          type: "string",
          description: "Optional OpenClaw model override.",
        },
        thinking: {
          type: "string",
          description: "Optional OpenClaw thinking level override.",
        },
      },
      required: ["prompt"],
    },
    async execute(_toolCallId, params) {
      const { plan, record, recordPath } = createWakeRecord({
        params,
        config: api.pluginConfig,
        toolContext,
      });
      return jsonToolResult(summarizeScheduleResult(plan, record, recordPath));
    },
  };
}

function formatStatus(summary) {
  return [
    "Codex Wake plugin is loaded.",
    `tool: ${summary.tool}`,
    `agentId: ${summary.agentId ?? "(unavailable)"}`,
    `sessionKey: ${summary.sessionKey ?? "(unavailable)"}`,
    `channel: ${summary.channel ?? "(unavailable)"}`,
    `channelId: ${summary.channelId ?? "(unavailable)"}`,
    `accountId: ${summary.accountId ?? "(unavailable)"}`,
    `threadId: ${summary.threadId ?? "(unavailable)"}`,
    `wakeRoot: ${summary.wakeRoot}`,
    `cwd: ${summary.cwd}`,
  ].join("\n");
}

export default definePluginEntry({
  id: "codex-wake",
  name: "Codex Wake",
  description: "Schedule durable codex-wake records from live OpenClaw sessions.",
  register(api) {
    api.registerTool((toolContext) => createScheduleTool(api, toolContext), {
      name: TOOL_NAME,
    });
    api.registerCommand({
      name: "codex-wake",
      description: "Show Codex Wake plugin context for this OpenClaw session.",
      acceptsArgs: true,
      agentPromptGuidance: [
        {
          surfaces: ["pi_main", "codex_app_server", "subagent"],
          text:
            "When delayed follow-up is needed in a live OpenClaw session, use the codex_wake_schedule tool. The tool captures the current OpenClaw session key; do not invent or copy placeholder session keys.",
        },
      ],
      handler: (ctx) => ({
        text: formatStatus(commandStatusSummary(ctx, api.pluginConfig)),
      }),
    });
  },
});
