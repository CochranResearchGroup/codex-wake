import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  buildSchedulePlan,
  buildWakeRecord,
  commandStatusSummary,
  createWakeRecord,
  monitorStatusForWakeRoot,
  parseCodexWakeCreateOutput,
} from "../lib/scheduler.js";

test("plugin manifest exposes monitor readiness config", () => {
  const manifest = JSON.parse(fs.readFileSync(new URL("../openclaw.plugin.json", import.meta.url), "utf8"));
  const packageJson = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"));

  assert.equal(manifest.version, packageJson.version);
  assert.equal(packageJson.version, "0.5.2");
  assert.equal(manifest.configSchema.properties.requireMonitorByDefault.type, "boolean");
  assert.equal(manifest.configSchema.properties.monitorStaleAfterSeconds.type, "integer");
  assert.equal(manifest.configSchema.properties.monitorStaleAfterSeconds.minimum, 1);
});

test("builds an OpenClaw Gateway wake plan from trusted tool context", () => {
  const plan = buildSchedulePlan({
    params: {
      trigger: "after",
      delay: "45m",
      prompt: "Check the build log and continue idempotently.",
    },
    config: {
      openclawCommand: "/bin/sh",
      wakeRoot: ".codex/wake",
      workspace: "default",
      requireMonitorByDefault: false,
    },
    toolContext: {
      workspaceDir: "/repo",
      agentId: "main",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
      messageChannel: "slack",
      deliveryContext: {
        channel: "slack",
        to: "channel:C0AHQQCG7J4",
        accountId: "default",
        threadId: "1779729958.218239",
      },
    },
    env: {},
  });

  assert.equal(plan.cwd, "/repo");
  assert.equal(plan.wakeRoot, path.resolve("/repo/.codex/wake"));
  assert.equal(plan.openclawCommand, "/bin/sh");
  assert.equal(plan.deliver, true);
  assert.equal(plan.agentId, "main");
  assert.equal(plan.sessionKey, "agent:main:slack:channel:c0ahqqcg7j4");
  assert.equal(plan.channelId, "C0AHQQCG7J4");
  assert.equal(plan.threadTs, "1779729958.218239");
  assert.equal(plan.replyChannel, undefined);
  assert.equal(plan.replyTo, undefined);
  assert.equal(plan.replyAccountId, undefined);
});

test("builds an absolute at-trigger wake root without workspace rewriting", () => {
  const plan = buildSchedulePlan({
    params: {
      trigger: "at",
      timestamp: "2026-05-25T18:30:00-05:00",
      prompt: "Check release state.",
      wakeRoot: "/var/lib/codex-wake/openclaw",
      deliver: false,
    },
    config: {
      openclawCommand: "/bin/sh",
      requireMonitorByDefault: false,
    },
    toolContext: {
      workspaceDir: "/repo",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
    },
  });

  assert.equal(plan.trigger, "at");
  assert.equal(plan.triggerValue, "2026-05-25T18:30:00-05:00");
  assert.equal(plan.wakeRoot, "/var/lib/codex-wake/openclaw");
  assert.equal(plan.deliver, false);
});

test("rejects missing live OpenClaw session context", () => {
  assert.throws(
    () =>
      buildSchedulePlan({
        params: { delay: "1m", prompt: "Resume." },
        toolContext: { workspaceDir: "/repo" },
      }),
    /sessionKey is required/,
  );
});

test("rejects placeholder session keys", () => {
  assert.throws(
    () =>
      buildSchedulePlan({
        params: { delay: "1m", prompt: "Resume.", sessionKey: "agent:main:noop-smoke-test" },
        env: { PATH: "/bin:/usr/bin" },
      }),
    /placeholder OpenClaw sessionKey is not allowed/,
  );
});

test("builds schema-versioned wake records", () => {
  const plan = buildSchedulePlan({
    params: {
      trigger: "after",
      delay: "30s",
      prompt: "Resume idempotently.",
    },
    config: {
      openclawCommand: "/bin/sh",
      requireMonitorByDefault: false,
    },
    toolContext: {
      workspaceDir: "/repo",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
    },
  });
  const record = buildWakeRecord(plan, {
    now: new Date("2026-05-25T20:39:34Z"),
    randomHex: "abcd",
  });

  assert.equal(record.schema_version, 1);
  assert.equal(record.id, "wake_20260525_203934_abcd");
  assert.equal(record.status, "pending");
  assert.equal(record.predicate.due_at, "2026-05-25T20:40:04Z");
  assert.equal(record.target.transport, "openclaw_gateway");
  assert.equal(record.target.openclaw.session_key, "agent:main:slack:channel:c0ahqqcg7j4");
  assert.equal(record.target.dispatch.deliver, true);
  assert.equal(record.target.dispatch.reply_channel, undefined);
  assert.equal(record.target.dispatch.reply_to, undefined);
  assert.equal(record.target.dispatch.reply_account_id, undefined);
  assert.equal(record.events[0].created_by, "openclaw-plugin:codex-wake");
});

test("includes dispatch reply overrides only when explicitly configured", () => {
  const plan = buildSchedulePlan({
    params: {
      trigger: "after",
      delay: "30s",
      prompt: "Resume idempotently.",
    },
    config: {
      openclawCommand: "/bin/sh",
      replyChannel: "api",
      replyTo: "channel:C0AHQQCG7J4",
      replyAccountId: "default",
      requireMonitorByDefault: false,
    },
    toolContext: {
      workspaceDir: "/repo",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
      deliveryContext: {
        channel: "slack",
        to: "channel:C0AHQQCG7J4",
        accountId: "default",
      },
    },
  });
  const record = buildWakeRecord(plan, {
    now: new Date("2026-05-25T20:39:34Z"),
    randomHex: "cafe",
  });

  assert.equal(plan.channelId, "C0AHQQCG7J4");
  assert.equal(record.target.dispatch.reply_channel, "api");
  assert.equal(record.target.dispatch.reply_to, "channel:C0AHQQCG7J4");
  assert.equal(record.target.dispatch.reply_account_id, "default");
});

test("writes wake records atomically under pending", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-codex-wake-"));
  const { record, recordPath } = createWakeRecord({
    params: {
      delay: "30s",
      prompt: "Resume idempotently.",
      wakeRoot: root,
    },
    config: {
      openclawCommand: "/bin/sh",
      requireMonitorByDefault: false,
    },
    toolContext: {
      workspaceDir: "/repo",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
    },
    now: new Date("2026-05-25T20:39:34Z"),
    randomHex: "beef",
  });

  assert.equal(record.id, "wake_20260525_203934_beef");
  assert.equal(recordPath, path.join(root, "pending", "wake_20260525_203934_beef.json"));
  assert.equal(fs.existsSync(recordPath), true);
});

test("requires recent persistent monitor health by default", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-codex-wake-unmonitored-"));

  assert.throws(
    () =>
      createWakeRecord({
        params: {
          delay: "30s",
          prompt: "Resume idempotently.",
          wakeRoot: root,
        },
        config: {
          openclawCommand: "/bin/sh",
        },
        toolContext: {
          workspaceDir: "/repo",
          sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
        },
      }),
    /wake root is not actively monitored/,
  );
});

test("accepts monitored roots with recent loop health", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-codex-wake-monitored-"));
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-codex-wake-state-"));
  const env = { HOME: os.homedir(), XDG_STATE_HOME: state };
  const key = crypto.createHash("sha1").update(path.resolve(root)).digest("hex").slice(0, 12);
  const healthDir = path.join(state, "codex-wake", "monitors");
  fs.mkdirSync(healthDir, { recursive: true });
  fs.writeFileSync(
    path.join(healthDir, `${key}.json`),
    `${JSON.stringify(
      {
        wake_root: path.resolve(root),
        source: "supervisor",
        mode: "loop",
        checked_at: "2026-05-25T20:39:30Z",
      },
      null,
      2,
    )}\n`,
  );

  const status = monitorStatusForWakeRoot(root, {
    env,
    now: new Date("2026-05-25T20:39:34Z"),
  });
  assert.equal(status.monitorReady, true);
  assert.equal(status.monitorSource, "supervisor");

  const { monitor, recordPath } = createWakeRecord({
    params: {
      delay: "30s",
      prompt: "Resume idempotently.",
      wakeRoot: root,
    },
    config: {
      openclawCommand: "/bin/sh",
    },
    toolContext: {
      workspaceDir: "/repo",
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
    },
    env,
    now: new Date("2026-05-25T20:39:34Z"),
    randomHex: "feed",
  });

  assert.equal(monitor.monitorReady, true);
  assert.equal(fs.existsSync(recordPath), true);
});

test("parses codex-wake create output", () => {
  assert.deepEqual(
    parseCodexWakeCreateOutput("wake_20260525_203934_201f /repo/.codex/wake/pending/wake.json\n"),
    {
      wakeId: "wake_20260525_203934_201f",
      path: "/repo/.codex/wake/pending/wake.json",
    },
  );
});

test("summarizes command status context", () => {
  const summary = commandStatusSummary(
    {
      sessionKey: "agent:main:slack:channel:c0ahqqcg7j4",
      channel: "slack",
      channelId: "C0AHQQCG7J4",
      accountId: "default",
      messageThreadId: "1779729958.218239",
      workspaceDir: "/repo",
    },
    {},
  );
  assert.equal(summary.agentId, "main");
  assert.equal(summary.wakeRoot, path.resolve("/repo/.codex/wake"));
  assert.equal(summary.threadId, "1779729958.218239");
});
