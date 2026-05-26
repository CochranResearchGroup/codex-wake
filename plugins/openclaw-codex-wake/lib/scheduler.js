import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const TOOL_NAME = "codex_wake_schedule";
export const DEFAULT_WAKE_ROOT = ".codex/wake";
export const DEFAULT_OPENCLAW_COMMAND = "openclaw";
export const DEFAULT_TIMEOUT_SECONDS = 600;
export const DEFAULT_GATEWAY_TIMEOUT_MS = 180000;
export const DEFAULT_MONITOR_STALE_AFTER_SECONDS = 120;
export const SCHEMA_VERSION = 1;

const WAKE_DIRS = [
  "pending",
  "firing",
  "submitted",
  "failed",
  "cancelled",
  "expired",
  "acks",
  "logs",
  "locks",
  "archive",
];

const PLACEHOLDER_TOKENS = [
  "noop-smoke-test",
  "placeholder",
  "dummy-session",
  "fake-session",
  "test-session",
  "session_abc",
  "thread_abc",
];

const ENV_NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

export class CodexWakePluginInputError extends Error {
  constructor(message) {
    super(message);
    this.name = "CodexWakePluginInputError";
  }
}

function isRecord(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function readString(record, key, options = {}) {
  const value = isRecord(record) ? record[key] : undefined;
  if (typeof value !== "string") {
    if (options.required) {
      throw new CodexWakePluginInputError(`${options.label ?? key} is required`);
    }
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    if (options.required) {
      throw new CodexWakePluginInputError(`${options.label ?? key} is required`);
    }
    return undefined;
  }
  return trimmed;
}

function readBoolean(record, key, fallback) {
  const value = isRecord(record) ? record[key] : undefined;
  return typeof value === "boolean" ? value : fallback;
}

function readPositiveInteger(record, key, fallback, min = 1) {
  const value = isRecord(record) ? record[key] : undefined;
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  if (!Number.isInteger(value) || value < min) {
    throw new CodexWakePluginInputError(`${key} must be an integer >= ${min}`);
  }
  return value;
}

function rootKey(wakeRoot) {
  return crypto.createHash("sha1").update(path.resolve(wakeRoot)).digest("hex").slice(0, 12);
}

function userConfigDir(env = process.env) {
  return path.join(env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), ".config"), "codex-wake");
}

function userStateDir(env = process.env) {
  return path.join(env.XDG_STATE_HOME || path.join(env.HOME || os.homedir(), ".local", "state"), "codex-wake");
}

function readJsonFile(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return undefined;
  }
}

function findSupervisorEntry(wakeRoot, env = process.env) {
  const registryDir = path.join(userConfigDir(env), "roots.d");
  let files = [];
  try {
    files = fs.readdirSync(registryDir);
  } catch {
    return {
      registryDir,
      registered: false,
    };
  }
  const resolved = path.resolve(wakeRoot);
  for (const file of files) {
    if (!file.endsWith(".json")) {
      continue;
    }
    const filePath = path.join(registryDir, file);
    const entry = readJsonFile(filePath);
    if (entry && path.resolve(String(entry.wake_root || "")) === resolved) {
      return {
        registryDir,
        registered: true,
        enabled: Boolean(entry.enabled),
        rootId: entry.root_id,
        path: filePath,
      };
    }
  }
  return {
    registryDir,
    registered: false,
  };
}

function parseServiceWakeRoot(unitText) {
  const match = /--wake-root(?:=|\s+)(?:"([^"]+)"|([^\s]+))/.exec(unitText);
  return match?.[1] || match?.[2] ? path.resolve(match[1] || match[2]) : undefined;
}

function findRepoServiceUnit(wakeRoot, env = process.env) {
  const systemdDir = path.join(env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), ".config"), "systemd", "user");
  let files = [];
  try {
    files = fs.readdirSync(systemdDir);
  } catch {
    return {
      systemdDir,
      appearsMonitored: false,
    };
  }
  const resolved = path.resolve(wakeRoot);
  for (const file of files) {
    if (!file.startsWith("codex-wake-") || !file.endsWith(".service")) {
      continue;
    }
    const filePath = path.join(systemdDir, file);
    let unitText = "";
    try {
      unitText = fs.readFileSync(filePath, "utf8");
    } catch {
      continue;
    }
    const serviceWakeRoot = parseServiceWakeRoot(unitText);
    if (serviceWakeRoot === resolved) {
      return {
        systemdDir,
        appearsMonitored: true,
        name: file,
        path: filePath,
        wakeRoot: serviceWakeRoot,
      };
    }
  }
  return {
    systemdDir,
    appearsMonitored: false,
  };
}

function readMonitorHealth(wakeRoot, env = process.env) {
  const healthPath = path.join(userStateDir(env), "monitors", `${rootKey(wakeRoot)}.json`);
  const health = readJsonFile(healthPath);
  return {
    path: healthPath,
    exists: Boolean(health),
    health,
  };
}

function isoAgeSeconds(value, now = new Date()) {
  if (typeof value !== "string" || !value) {
    return undefined;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) {
    return undefined;
  }
  return Math.max(0, Math.floor((now.valueOf() - parsed.valueOf()) / 1000));
}

export function monitorStatusForWakeRoot(wakeRoot, { env = process.env, now = new Date(), staleAfterSeconds = DEFAULT_MONITOR_STALE_AFTER_SECONDS } = {}) {
  const supervisor = findSupervisorEntry(wakeRoot, env);
  const repoService = findRepoServiceUnit(wakeRoot, env);
  const healthProbe = readMonitorHealth(wakeRoot, env);
  const ageSeconds = isoAgeSeconds(healthProbe.health?.checked_at, now);
  const recent = ageSeconds !== undefined && ageSeconds <= staleAfterSeconds;
  const persistent = healthProbe.health?.mode === "loop";
  const monitorReady = Boolean(recent && persistent);
  return {
    monitorReady,
    monitorSource: monitorReady ? String(healthProbe.health?.source || "health") : "",
    wakeRoot: path.resolve(wakeRoot),
    staleAfterSeconds,
    supervisor,
    repoService,
    health: {
      path: healthProbe.path,
      exists: healthProbe.exists,
      recent,
      persistent,
      ageSeconds: ageSeconds ?? null,
      source: healthProbe.health?.source ?? "",
      mode: healthProbe.health?.mode ?? "",
      checkedAt: healthProbe.health?.checked_at ?? "",
    },
  };
}

function readConfigString(config, key) {
  return readString(config, key);
}

function commandFromConfigOrEnv(config, configKey, envKey, fallback, env) {
  return readConfigString(config, configKey) ?? env[envKey] ?? fallback;
}

function normalizeTrigger(params) {
  const trigger = (readString(params, "trigger") ?? "after").toLowerCase();
  if (trigger === "after") {
    return {
      type: "after",
      value: readString(params, "delay", { required: true }),
    };
  }
  if (trigger === "at") {
    return {
      type: "at",
      value: readString(params, "timestamp", { required: true }),
    };
  }
  throw new CodexWakePluginInputError('trigger must be "after" or "at"');
}

export function deriveAgentId(sessionKey, explicitAgentId) {
  const agentId = explicitAgentId?.trim();
  if (agentId) {
    return agentId;
  }
  const match = /^agent:([^:]+):/.exec(sessionKey);
  if (match?.[1]) {
    return match[1];
  }
  throw new CodexWakePluginInputError("agentId is required when sessionKey does not include an agent id");
}

export function validateSessionKey(sessionKey, agentId) {
  const normalized = sessionKey.trim();
  if (!normalized) {
    throw new CodexWakePluginInputError("sessionKey is required");
  }
  const lower = normalized.toLowerCase();
  if (PLACEHOLDER_TOKENS.some((token) => lower.includes(token))) {
    throw new CodexWakePluginInputError(`placeholder OpenClaw sessionKey is not allowed: ${sessionKey}`);
  }
  if (!normalized.startsWith(`agent:${agentId}:`)) {
    throw new CodexWakePluginInputError(
      `sessionKey must belong to agent "${agentId}" and start with "agent:${agentId}:"`,
    );
  }
  return normalized;
}

function inferProviderFromSessionKey(sessionKey) {
  const parts = sessionKey.split(":");
  return parts[2] || undefined;
}

function inferChannelIdFromSessionKey(sessionKey) {
  const match = /^agent:[^:]+:[^:]+:channel:([^:]+)$/i.exec(sessionKey);
  return match?.[1];
}

function inferChannelIdFromTarget(target) {
  if (!target) {
    return undefined;
  }
  const match = /^channel:(.+)$/i.exec(target);
  return match?.[1];
}

function normalizeChannelId(provider, value) {
  if (!value) {
    return undefined;
  }
  return provider === "slack" ? value.toUpperCase() : value;
}

function resolvePathAgainst(cwd, value) {
  return path.isAbsolute(value) ? path.resolve(value) : path.resolve(cwd, value);
}

function defaultCwd(params, config, toolContext) {
  const cwd =
    readString(params, "cwd") ??
    readConfigString(config, "cwd") ??
    readString(toolContext, "workspaceDir") ??
    process.cwd();
  return path.resolve(cwd);
}

function defaultWakeRoot(params, config, cwd) {
  const root = readString(params, "wakeRoot") ?? readConfigString(config, "wakeRoot") ?? DEFAULT_WAKE_ROOT;
  return resolvePathAgainst(cwd, root);
}

function validateEnvRef(name, value) {
  if (!value) {
    return undefined;
  }
  if (!ENV_NAME_RE.test(value)) {
    throw new CodexWakePluginInputError(`${name} must be an environment variable name`);
  }
  return value;
}

export function resolveExecutableCommand(command, env = process.env) {
  if (command.includes(path.sep)) {
    const resolved = path.resolve(command);
    try {
      fs.accessSync(resolved, fs.constants.X_OK);
      return resolved;
    } catch {
      throw new CodexWakePluginInputError(`configured OpenClaw command is not executable: ${command}`);
    }
  }
  const pathText = env.PATH ?? "";
  for (const dir of pathText.split(path.delimiter).filter(Boolean)) {
    const candidate = path.join(dir, command);
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      // Keep scanning PATH.
    }
  }
  throw new CodexWakePluginInputError(`OpenClaw command not found on PATH: ${command}`);
}

function parseDurationMs(value) {
  const text = value.trim().toLowerCase();
  if (!text) {
    throw new CodexWakePluginInputError("delay is required");
  }
  const pattern = /(\d+)([smhd])/g;
  let pos = 0;
  let total = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index !== pos) {
      throw new CodexWakePluginInputError(`invalid delay: ${value}`);
    }
    const amount = Number.parseInt(match[1], 10);
    const unit = match[2];
    const scale = unit === "s" ? 1000 : unit === "m" ? 60000 : unit === "h" ? 3600000 : 86400000;
    total += amount * scale;
    pos = match.index + match[0].length;
  }
  if (pos !== text.length || total <= 0) {
    throw new CodexWakePluginInputError(`invalid delay: ${value}`);
  }
  return total;
}

function parseTimestamp(value) {
  const text = value.trim();
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(text)) {
    throw new CodexWakePluginInputError("timestamp must include a timezone offset or Z");
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.valueOf())) {
    throw new CodexWakePluginInputError(`invalid timestamp: ${value}`);
  }
  return parsed;
}

export function formatUtc(date) {
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function makeWakeId(now, randomHex = crypto.randomBytes(2).toString("hex")) {
  const stamp = formatUtc(now).replace(/[-:]/g, "").replace("T", "_").replace("Z", "");
  return `wake_${stamp}_${randomHex}`;
}

function makeEvent(type, message, now, extra = {}) {
  return {
    at: formatUtc(now),
    type,
    message,
    ...extra,
  };
}

function dueAtForTrigger(trigger, now) {
  if (trigger.type === "after") {
    return new Date(now.valueOf() + parseDurationMs(trigger.value));
  }
  return parseTimestamp(trigger.value);
}

function buildOpenClawTarget(plan) {
  const target = {
    transport: "openclaw_gateway",
    gateway: {},
    openclaw: {
      agent_id: plan.agentId,
      session_key: plan.sessionKey,
    },
    dispatch: {
      deliver: plan.deliver,
      timeout_seconds: plan.timeoutSeconds,
      gateway_timeout_ms: plan.gatewayTimeoutMs,
    },
    openclaw_cmd: plan.openclawCommand,
  };
  if (plan.gatewayUrl) {
    target.gateway.url = plan.gatewayUrl;
  }
  if (plan.tokenEnv) {
    target.gateway.token_env = plan.tokenEnv;
  }
  if (plan.passwordEnv) {
    target.gateway.password_env = plan.passwordEnv;
  }
  const channel = {};
  if (plan.provider) {
    channel.provider = plan.provider;
  }
  if (plan.workspace) {
    channel.workspace = plan.workspace;
  }
  if (plan.channelId) {
    channel.channel_id = plan.channelId;
  }
  if (plan.threadTs) {
    channel.thread_ts = plan.threadTs;
  }
  if (Object.keys(channel).length > 0) {
    target.openclaw.channel = channel;
  }
  if (plan.replyChannel) {
    target.dispatch.reply_channel = plan.replyChannel;
  }
  if (plan.replyTo) {
    target.dispatch.reply_to = plan.replyTo;
  }
  if (plan.replyAccountId) {
    target.dispatch.reply_account_id = plan.replyAccountId;
  }
  if (plan.model) {
    target.dispatch.model = plan.model;
  }
  if (plan.thinking) {
    target.dispatch.thinking = plan.thinking;
  }
  return target;
}

export function buildSchedulePlan({
  params,
  config = {},
  toolContext = {},
  env = process.env,
} = {}) {
  if (!isRecord(params)) {
    throw new CodexWakePluginInputError("tool params must be an object");
  }
  const context = isRecord(toolContext) ? toolContext : {};
  const pluginConfig = isRecord(config) ? config : {};
  const prompt = readString(params, "prompt", { required: true });
  const trigger = normalizeTrigger(params);
  const cwd = defaultCwd(params, pluginConfig, context);
  const wakeRoot = defaultWakeRoot(params, pluginConfig, cwd);
  const rawSessionKey = readString(params, "sessionKey") ?? readString(context, "sessionKey", { required: true });
  const agentId = deriveAgentId(rawSessionKey, readString(params, "agentId") ?? readString(context, "agentId"));
  const sessionKey = validateSessionKey(rawSessionKey, agentId);
  const deliveryContext = isRecord(context.deliveryContext) ? context.deliveryContext : {};
  const provider =
    readString(params, "channelProvider") ??
    readConfigString(pluginConfig, "channelProvider") ??
    readString(deliveryContext, "channel") ??
    readString(context, "messageChannel") ??
    inferProviderFromSessionKey(sessionKey) ??
    "slack";
  const deliveryTo = readString(deliveryContext, "to");
  const replyTo = readString(params, "replyTo") ?? readConfigString(pluginConfig, "replyTo");
  const channelId = normalizeChannelId(
    provider,
    readString(params, "channelId") ??
      readConfigString(pluginConfig, "channelId") ??
      inferChannelIdFromTarget(replyTo) ??
      inferChannelIdFromTarget(deliveryTo) ??
      inferChannelIdFromSessionKey(sessionKey),
  );
  const threadTs =
    readString(params, "threadTs") ??
    readConfigString(pluginConfig, "threadTs") ??
    (typeof deliveryContext.threadId === "number"
      ? String(deliveryContext.threadId)
      : readString(deliveryContext, "threadId"));
  const workspace =
    readString(params, "workspace") ??
    readConfigString(pluginConfig, "workspace") ??
    readString(deliveryContext, "accountId") ??
    readString(context, "agentAccountId");
  const openclawCommand = resolveExecutableCommand(
    readString(params, "openclawCommand") ??
      commandFromConfigOrEnv(
        pluginConfig,
        "openclawCommand",
        "CODEX_WAKE_OPENCLAW_CMD",
        DEFAULT_OPENCLAW_COMMAND,
        env,
      ),
    env,
  );
  const timeoutSeconds = readPositiveInteger(
    params,
    "timeoutSeconds",
    readPositiveInteger(pluginConfig, "defaultTimeoutSeconds", DEFAULT_TIMEOUT_SECONDS),
  );
  const gatewayTimeoutMs = readPositiveInteger(
    params,
    "gatewayTimeoutMs",
    readPositiveInteger(pluginConfig, "defaultGatewayTimeoutMs", DEFAULT_GATEWAY_TIMEOUT_MS, 1000),
    1000,
  );
  const requireMonitor = readBoolean(
    params,
    "requireMonitor",
    readBoolean(pluginConfig, "requireMonitorByDefault", true),
  );
  const monitorStaleAfterSeconds = readPositiveInteger(
    params,
    "monitorStaleAfterSeconds",
    readPositiveInteger(pluginConfig, "monitorStaleAfterSeconds", DEFAULT_MONITOR_STALE_AFTER_SECONDS),
  );
  return {
    cwd,
    wakeRoot,
    agentId,
    sessionKey,
    provider,
    channelId,
    threadTs,
    workspace,
    replyChannel: readString(params, "replyChannel") ?? readConfigString(pluginConfig, "replyChannel"),
    replyTo,
    replyAccountId: readString(params, "replyAccountId") ?? readConfigString(pluginConfig, "replyAccountId"),
    gatewayUrl: readString(params, "gatewayUrl") ?? readConfigString(pluginConfig, "gatewayUrl"),
    tokenEnv: validateEnvRef("tokenEnv", readString(params, "tokenEnv") ?? readConfigString(pluginConfig, "tokenEnv")),
    passwordEnv: validateEnvRef(
      "passwordEnv",
      readString(params, "passwordEnv") ?? readConfigString(pluginConfig, "passwordEnv"),
    ),
    openclawCommand,
    timeoutSeconds,
    gatewayTimeoutMs,
    requireMonitor,
    monitorStaleAfterSeconds,
    deliver: readBoolean(params, "deliver", readBoolean(pluginConfig, "deliverByDefault", true)),
    model: readString(params, "model") ?? readConfigString(pluginConfig, "model"),
    thinking: readString(params, "thinking") ?? readConfigString(pluginConfig, "thinking"),
    trigger: trigger.type,
    triggerValue: trigger.value,
    prompt,
  };
}

export const buildScheduleCommand = buildSchedulePlan;

export function buildWakeRecord(plan, { now = new Date(), randomHex } = {}) {
  const current = new Date(Math.trunc(now.valueOf() / 1000) * 1000);
  const due = dueAtForTrigger({ type: plan.trigger, value: plan.triggerValue }, current);
  const timestamp = formatUtc(current);
  const dueAt = formatUtc(due);
  const wakeId = makeWakeId(current, randomHex);
  const predicate = {
    type: "not_before",
    due_at: dueAt,
  };
  return {
    schema_version: SCHEMA_VERSION,
    id: wakeId,
    created_at: timestamp,
    updated_at: timestamp,
    cwd: plan.cwd,
    target: buildOpenClawTarget(plan),
    predicate,
    prompt: plan.prompt,
    status: "pending",
    attempts: 0,
    max_attempts: 3,
    ack_timeout_seconds: 30,
    next_attempt_at: dueAt,
    events: [
      makeEvent("created", "Wake record created", current, {
        created_by: "openclaw-plugin:codex-wake",
      }),
    ],
  };
}

export function ensureWakeDirs(wakeRoot) {
  for (const dir of WAKE_DIRS) {
    fs.mkdirSync(path.join(wakeRoot, dir), { recursive: true });
  }
}

export function writeWakeRecord(wakeRoot, record) {
  ensureWakeDirs(wakeRoot);
  const wakeId = record.id;
  if (typeof wakeId !== "string" || !wakeId) {
    throw new CodexWakePluginInputError("wake record missing id");
  }
  if (record.status !== "pending") {
    throw new CodexWakePluginInputError(`plugin can only create pending records, got ${record.status}`);
  }
  const finalPath = path.join(wakeRoot, "pending", `${wakeId}.json`);
  const tempPath = `${finalPath}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(record, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, finalPath);
  return finalPath;
}

export function createWakeRecord(params) {
  const plan = buildSchedulePlan(params);
  const monitor = monitorStatusForWakeRoot(plan.wakeRoot, {
    env: params.env,
    now: params.now,
    staleAfterSeconds: plan.monitorStaleAfterSeconds,
  });
  if (plan.requireMonitor && !monitor.monitorReady) {
    throw new CodexWakePluginInputError(
      `wake root is not actively monitored: ${plan.wakeRoot}; ` +
        `health_recent=${monitor.health.recent} health_persistent=${monitor.health.persistent} ` +
        `repo_service_unit=${monitor.repoService.appearsMonitored}`,
    );
  }
  const record = buildWakeRecord(plan, params);
  const recordPath = writeWakeRecord(plan.wakeRoot, record);
  return {
    plan,
    monitor,
    record,
    recordPath,
  };
}

export function parseCodexWakeCreateOutput(stdout) {
  const text = String(stdout ?? "");
  const match = text.match(/^(wake_[A-Za-z0-9_.:-]+)\s+(.+)$/m);
  if (!match) {
    throw new CodexWakePluginInputError("codex-wake did not print a wake id");
  }
  return {
    wakeId: match[1],
    path: match[2].trim(),
  };
}

export function summarizeScheduleResult(plan, record, recordPath, monitorStatus) {
  const monitor = monitorStatus ?? monitorStatusForWakeRoot(plan.wakeRoot, {
    staleAfterSeconds: plan.monitorStaleAfterSeconds,
  });
  return {
    ok: true,
    wakeId: record.id,
    wakePath: recordPath,
    wakeRoot: plan.wakeRoot,
    cwd: plan.cwd,
    transport: "openclaw_gateway",
    agentId: plan.agentId,
    sessionKey: plan.sessionKey,
    deliver: plan.deliver,
    trigger: plan.trigger,
    triggerValue: plan.triggerValue,
    dueAt: record.predicate.due_at,
    monitor: {
      requireMonitor: plan.requireMonitor,
      monitorReady: monitor.monitorReady,
      monitorSource: monitor.monitorSource,
      wakeRoot: monitor.wakeRoot,
      health: monitor.health,
      supervisor: monitor.supervisor,
      repoService: monitor.repoService,
      warning: monitor.monitorReady
        ? ""
        : "Wake record was written, but no recent persistent monitor health was found for this wake root.",
    },
    validation: {
      show: `codex-wake --wake-root ${plan.wakeRoot} show ${record.id}`,
      status: `codex-wake --wake-root ${plan.wakeRoot} status --json`,
      daemonOnce: `codex-waked --wake-root ${plan.wakeRoot} --once --ack-timeout 20`,
    },
  };
}

export function commandStatusSummary(ctx, config = {}) {
  const context = isRecord(ctx) ? ctx : {};
  const sessionKey = readString(context, "sessionKey");
  const agentId = sessionKey ? deriveAgentId(sessionKey, readString(context, "agentId")) : readString(context, "agentId");
  const cwd = defaultCwd({}, isRecord(config) ? config : {}, context);
  const wakeRoot = defaultWakeRoot({}, isRecord(config) ? config : {}, cwd);
  return {
    plugin: "codex-wake",
    tool: TOOL_NAME,
    agentId,
    sessionKey,
    channel: readString(context, "channel") ?? readString(context, "messageChannel"),
    channelId: readString(context, "channelId"),
    accountId: readString(context, "accountId"),
    threadId: typeof context.messageThreadId === "number" ? String(context.messageThreadId) : readString(context, "messageThreadId"),
    wakeRoot,
    cwd,
  };
}
