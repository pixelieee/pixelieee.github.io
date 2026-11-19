// Save in the upstream Pi checkout and use its TypeScript source resolver.
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from "./packages/ai/src/providers/faux.ts";
import { getCurrentSystemMessage } from "./packages/ai/src/utils/transcript.ts";
import { prepareCompaction } from "./packages/coding-agent/src/core/compaction/compaction.ts";
import { computeFileLists } from "./packages/coding-agent/src/core/compaction/utils.ts";
import { createAgentSession } from "./packages/coding-agent/src/core/sdk.ts";
import { AuthStorage } from "./packages/coding-agent/src/core/auth-storage.ts";
import { ModelRuntime } from "./packages/coding-agent/src/core/model-runtime.ts";
import { SessionManager } from "./packages/coding-agent/src/core/session-manager.ts";
import { DefaultResourceLoader } from "./packages/coding-agent/src/core/resource-loader.ts";

process.env.PI_OFFLINE = "1";
const temp = await mkdtemp(join(tmpdir(), "pi-skill-observation-"));
const project = join(temp, "project");
const agentDir = join(temp, "agent");
process.env.PI_CODING_AGENT_DIR = agentDir;
process.env.HOME = temp;
process.env.USERPROFILE = temp;
async function putSkill(name, description, body) {
  const dir = join(agentDir, "skills", name);
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "SKILL.md"), `---\nname: ${name}\ndescription: ${description}\n---\n${body}\n`);
}
const transcript = [];
const provider = fauxProvider();
const model = provider.getModel();
const credentials = AuthStorage.inMemory();
await credentials.modify(model.provider, async () => ({ type: "api_key", key: "local-fixture" }));
const runtime = await ModelRuntime.create({ credentials, modelsPath: join(agentDir, "models.json") });
async function open() {
  runtime.registerNativeProvider(provider.provider);
  const resourceLoader = new DefaultResourceLoader({ cwd: project, agentDir, noExtensions: true });
  await resourceLoader.reload();
  const { session } = await createAgentSession({ cwd: project, agentDir, modelRuntime: runtime, model, resourceLoader,
    sessionManager: SessionManager.inMemory(project) });
  return session;
}
async function turn(label, session, prompt) {
  runtime.registerNativeProvider(provider.provider);
  provider.setResponses([(context) => {
    const groups = context.messages.map(m => [m.role, JSON.stringify(m)]);
    const markers = (text) => [...new Set(text.match(/(?:DESC|BODY|RULE)_[AB]|NEW_SKILL|\/skill:late/g) ?? [])];
    const row = { label, system: markers(JSON.stringify(getCurrentSystemMessage(context.messages))),
      updates: groups.filter(([r]) => r === "system").map(([,t]) => markers(t)).filter(list => list.length),
      users: groups.filter(([r]) => r === "user").map(([,t]) => markers(t)) };
    transcript.push(row);
    console.log(JSON.stringify(row));
    return fauxAssistantMessage("ok");
  }]);
  await session.prompt(prompt);
  assert.equal(transcript.at(-1)?.label, label, "provider did not receive the expected turn");
}
let session;
try {
  await mkdir(project, { recursive: true });
  await writeFile(join(project, "AGENTS.md"), "RULE_A");
  await putSkill("release", "DESC_A", "BODY_A");
  session = await open();
  await turn("initial", session, "/skill:release");
  await putSkill("release", "DESC_B", "BODY_B");
  await putSkill("late", "NEW_SKILL", "New instructions.");
  await writeFile(join(project, "AGENTS.md"), "RULE_B");
  await turn("edit on disk", session, "/skill:release");
  await turn("unknown name", session, "/skill:late");
  await session.reload();
  await turn("reload", session, "/skill:release");
  session.dispose();
  session = await open();
  await turn("fresh session", session, "hello");
  const [first, edited, unknown, reloaded, fresh] = transcript;
  assert.deepEqual(new Set(first.system), new Set(["DESC_A", "RULE_A"]));
  assert.deepEqual(edited.users, [["BODY_A"], ["BODY_B"]]);
  assert.deepEqual(new Set(edited.system), new Set(first.system));
  assert.deepEqual(unknown.users.at(-1), ["/skill:late"]);
  assert.deepEqual(new Set(reloaded.system), new Set(["RULE_B", "DESC_B", "NEW_SKILL"]));
  assert.deepEqual(fresh.system, reloaded.system);
  assert.deepEqual(fresh.users, [[]]);
  assert.deepEqual(reloaded.updates[0], first.system);
  assert.deepEqual(reloaded.updates[1], fresh.system);

  // Execute the built-in edit against a real file. Supply replies without a remote model.
  await writeFile(join(project, "release.md"), "unchanged");
  provider.setResponses([
    fauxAssistantMessage(fauxToolCall("edit", {
      path: "release.md", edits: [{ oldText: "never present", newText: "patched" }],
    }), { stopReason: "toolUse" }),
    fauxAssistantMessage("edit failed"),
  ]);
  await session.prompt("Exercise the edit tool.");
  const log = session.sessionManager;
  const error = log.getEntries().find(e => e.type === "message" && e.message.role === "toolResult" && e.message.toolName === "edit");
  assert.equal(error?.message.isError, true);
  assert.equal(await readFile(join(project, "release.md"), "utf8"), "unchanged");
  await turn("keep recent", session, "the next user turn");
  const prepared = prepareCompaction(log.getBranch(), { enabled: true, reserveTokens: 16, keepRecentTokens: 1 });
  const files = computeFileLists(prepared.fileOps);
  assert.deepEqual(files.modifiedFiles, ["release.md"]);
  console.log(JSON.stringify({ toolError: error.message.isError, onDisk: "unchanged", ...files }));

} finally {
  session?.dispose();
  await rm(temp, { recursive: true, force: true });
}
