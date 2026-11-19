"""Trace Claude Code tool requests in isolated local Git repositories.

Requires Python 3.9+, Git and the Claude Code CLI. Run: python claude-memory-trace.py
The endpoint returns scripted tool calls, never a prediction. It listens on loopback.
The temporary directory is retained so the raw requests and written files can be inspected.
"""
import json
import os
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def reply(model, tool, number):
    """A minimal streaming Messages response accepted by the real CLI."""
    if tool:
        name, arguments = tool
        block = {"type": "tool_use", "id": f"toolu_{number}", "name": name, "input": {}}
        delta = {"type": "input_json_delta", "partial_json": json.dumps(arguments)}
    else:
        block = {"type": "text", "text": ""}
        delta = {"type": "text_delta", "text": "OK"}
    message = {"id": f"msg_{number}", "role": "assistant", "type": "message", "model": model,
               "content": [], "stop_reason": None, "stop_sequence": None,
               "usage": {"input_tokens": 1, "output_tokens": 0}}
    return [("message_start", {"message": message}),
            ("content_block_start", {"index": 0, "content_block": block}),
            ("content_block_delta", {"index": 0, "delta": delta}),
            ("content_block_stop", {"index": 0}),
            ("message_delta", {"delta": {"stop_reason": "tool_use" if tool else "end_turn",
                                          "stop_sequence": None}, "usage": {"output_tokens": 1}}),
            ("message_stop", {})]


class Receiver(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/messages":
            self.send_error(404)
            return
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        number = len(self.server.requests)
        plan = self.server.plan
        tool = plan[number - 1] if number <= len(plan) else None
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for event, fields in reply(request["model"], tool, number):
            data = json.dumps({"type": event, **fields})
            self.wfile.write(f"event: {event}\ndata: {data}\n\n".encode())


def blocks(req):
    system = req.get("system", [])
    if isinstance(system, str):
        yield "system.text", system
    else:
        for item in system:
            yield "system.text", item.get("text", "")
    for msg in req["messages"]:
        items = msg["content"]
        if isinstance(items, str):
            yield msg["role"] + ".text", items
        else:
            for item in items:
                yield msg["role"] + "." + item["type"], json.dumps(item, ensure_ascii=False)


markers = ["ROOT_GUIDE", "SECOND_GUIDE", "INDEX_BEFORE", "INDEX_AFTER", "DETAIL_QUARTZ", "SCOPE_RULE", "NESTED_RULE",
           "BODY_RELEASE", "DESC_RELEASE", "BODY_MANUAL", "DESC_MANUAL",
           "DESC_SIDE", "EDGE_200", "EDGE_201", "EDGE_202"]


def report(label, req):
    fields = []
    for slot, body in blocks(req):
        found = [m for m in markers if m in body]
        if found:
            fields.append(f"{slot}={','.join(found)}")
    print(label, " | ".join(fields) or "(no markers)")


def environment(base, config, port):
    keep = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LANG",
            "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROCESSOR_ARCHITECTURE"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    home = base / "home"
    home.mkdir()
    env.update(HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home / "Local"),
               APPDATA=str(home / "Roaming"), CLAUDE_CONFIG_DIR=str(config),
               ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}", ANTHROPIC_API_KEY="local-fixture",
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_AUTOUPDATER="1",
               NO_PROXY="127.0.0.1")
    return env


def main():
    base = Path(tempfile.mkdtemp(prefix="cc-memory-trace-"))
    print("Isolated fixture:", base, flush=True)
    config, repo, linked, unrelated = [base / p for p in ("config", "repo", "linked", "other")]
    for project in (repo, unrelated):
        project.mkdir()
        git(project, "init", "-q")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=example@example.invalid",
        "commit", "--allow-empty", "-qm", "fixture root")
    git(repo, "worktree", "add", "-qb", "side", str(linked))
    write(config / "settings.json", '{"autoMemoryEnabled": true}')
    write(repo / "CLAUDE.md", "ROOT_GUIDE")
    write(repo / "AGENTS.md", "SECOND_GUIDE")
    write(repo / ".claude/skills/release-card/SKILL.md",
          "---\nname: release-card\ndescription: DESC_RELEASE\n---\nBODY_RELEASE\n")
    write(repo / ".claude/skills/release-manual/SKILL.md",
          "---\nname: release-manual\ndescription: DESC_MANUAL\ndisable-model-invocation: true\n---\nBODY_MANUAL\n")
    write(repo / ".claude/rules/module.md", '---\npaths: ["module/**/*.py"]\n---\nSCOPE_RULE')
    write(repo / "module/CLAUDE.md", "NESTED_RULE")
    write(repo / "module/a.py", "value = 1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    env = environment(base, config, server.server_port)
    cli = shutil.which("claude.exe") or shutil.which("claude")
    print(subprocess.check_output([cli, "--version"], env=env, text=True).strip())

    def run(label, cwd, prompt="ordinary prompt", plan=()):
        server.plan, server.requests = plan, []
        subprocess.run([cli, "-p", "--no-session-persistence", "--model", "sonnet",
                        "--strict-mcp-config", "--tools", "Read,Write,Edit,Skill",
                        "--allowedTools", "Read,Write,Edit,Skill", "--", prompt],
                       cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, check=True, timeout=60)
        if len(server.requests) != len(plan) + 1:
            raise RuntimeError(f"{label}: expected {len(plan)+1} requests, saw {len(server.requests)}")
        for i, req in enumerate(server.requests, 1):
            write(base / "requests" / f"{label}-{i}.json", json.dumps(req, indent=2))
            report(f"{label}.{i}", req)
        return server.requests

    try:
        run("bootstrap", repo)
        memory, = (config / "projects").glob("*/memory")
        index, note = memory / "MEMORY.md", memory / "release-owner.md"
        before = "- release-owner.md: INDEX_BEFORE\n"
        after = "- release-owner.md: INDEX_AFTER\n"
        detail = ("---\nname: release-owner\ndescription: Release handoff\ntype: project\n---\n"
                  "The on-call handoff code is DETAIL_QUARTZ.\n")
        write(index, before)
        run("writer", repo, plan=[
            ("Read", {"file_path": str(index)}),
            ("Write", {"file_path": str(note), "content": detail}),
            ("Edit", {"file_path": str(index), "old_string": before.strip(), "new_string": after.strip()})])
        assert after.strip() in index.read_text("utf-8") and "DETAIL_QUARTZ" in note.read_text("utf-8")
        print("on disk:", index.read_text("utf-8").strip(),
              "topic contains detail:", "DETAIL_QUARTZ" in note.read_text("utf-8"),
              "modified frontmatter:", "modified:" in note.read_text("utf-8"))
        run("restart", repo, plan=[("Read", {"file_path": str(note)})])
        run("linked", linked)
        (linked / ".claude/skills").mkdir(parents=True)
        run("linked-empty", linked)
        write(linked / ".claude/skills/side-check/SKILL.md",
              "---\nname: side-check\ndescription: DESC_SIDE\n---\nA worktree-only check.\n")
        run("linked-local", linked)
        run("unrelated", unrelated)
        oversized = "\n".join(["entry"] * 199 + ["EDGE_200", "EDGE_201", "EDGE_202"])
        overflow = run("oversize", repo, plan=[
            ("Read", {"file_path": str(index)}),
            ("Write", {"file_path": str(index), "content": oversized})])
        outcome = next(item for msg in overflow[-1]["messages"] for item in msg["content"]
                       if isinstance(item, dict) and item.get("tool_use_id") == "toolu_2")
        correction = next((body for slot, body in blocks(overflow[-1])
                           if slot == "system.text" and "200-line read limit" in body), None)
        print("oversize: is_error=", outcome.get("is_error", False),
              "line count on disk=", len(index.read_text("utf-8").splitlines()),
              "separate post-write warning=", bool(correction))
        run("truncation", repo)
        run("explicit", repo, "/release-card")
        run("manual", repo, "/release-manual")
        run("invoked-twice", repo, plan=[("Skill", {"skill": "release-card"}),
                                          ("Skill", {"skill": "release-card"})])
        run("manual-via-tool", repo, plan=[("Skill", {"skill": "release-manual"})])
        run("nested", repo, plan=[("Read", {"file_path": str(repo / "module/a.py")})])
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
