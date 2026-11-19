"""Capture OpenCode v1.18.33's compaction and skill-permission requests on loopback.

Run: python opencode-checkpoint.py [path-to-opencode]
Requires Python 3.10+, Git and the v1.18.33 binary. All inputs and state live
in a new temporary directory. requests.json holds the synthetic provider trace.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import tempfile
from threading import Thread
import time
from urllib.request import build_opener, ProxyHandler, Request


HEAD, TAIL = "HEAD_CHECKPOINT_PROBE", "TAIL_CHECKPOINT_PROBE"
SUMMARY = "STUB_CHECKPOINT"
MODEL = {"providerID": "localprobe", "modelID": "probe"}
http = build_opener(ProxyHandler({}))


def write_skill(repo, name, body):
    dest = repo / ".opencode" / "skills" / name / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"---\nname: {name}\ndescription: {name} procedure\n---\n{body}\n", encoding="utf8")


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        messages = request["messages"]
        last = messages[-1]
        exposed = [tool["function"]["name"] for tool in request.get("tools", [])]
        revision_calls = ("CHANGE_BEFORE", "CHANGE_AFTER", "CHANGE_COLD")
        calls = ("TURN_OLD", "CHECK_DENIAL", "ASK_ONCE", "ASK_AGAIN", *revision_calls)
        is_call = last["role"] == "user" and last["content"] in calls and "skill" in exposed
        is_summary = "[Tool result]:" in str(messages) and "[User]: TURN_OLD" in str(messages)
        if is_call:
            skill_name = "revision" if last["content"] in revision_calls else "release"
            function = {"name": "skill", "arguments": json.dumps({"name": skill_name})}
            delta = {"role": "assistant", "tool_calls": [
                {"index": 0, "id": "call_" + last["content"], "type": "function", "function": function}
            ]}
        else:
            delta = {"role": "assistant", "content": SUMMARY if is_summary else "OK"}
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for payload, finish in [(delta, None), ({}, "tool_calls" if is_call else "stop")]:
            event = {"id": "local", "object": "chat.completion.chunk", "model": "probe",
                     "created": int(time.time()), "choices": [{"index": 0, "delta": payload, "finish_reason": finish}]}
            self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")


def api(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    with http.open(Request(base + path, data, {"Content-Type": "application/json"}), timeout=120) as response:
        return json.load(response)


@contextmanager
def opencode(binary, repo, env, root):
    with socket.socket() as port_picker:
        port_picker.bind(("127.0.0.1", 0))
        port = port_picker.getsockname()[1]
    log_path = root / f"server-{time.time_ns()}.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen([binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                   cwd=repo, env=env, stdout=log, stderr=log,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            end = time.monotonic() + 120
            while time.monotonic() < end and process.poll() is None:
                ready = re.search(r"opencode server listening on (http://127\.0\.0\.1:\d+)",
                                  log_path.read_text(encoding="utf8", errors="replace"))
                if ready:
                    base = ready.group(1)
                    api(base, "/global/health")
                    break
                time.sleep(0.15)
            else:
                raise RuntimeError(f"Server did not announce a listener (exit={process.poll()}). See {log_path}")
            yield base
        finally:
            process.terminate()
            process.wait(timeout=15)


def turn(base, session, text, agent="build"):
    result = api(base, f"/session/{session}/message", {"model": MODEL, "agent": agent,
                 "parts": [{"type": "text", "text": text}]})
    if result["info"].get("error"):
        raise RuntimeError(result["info"]["error"])
    return result["info"]["parentID"]


def content(request, role):
    return "\n".join(json.dumps(m["content"]) for m in request["messages"] if m["role"] == role)


def approve_once(base, session, text):
    with ThreadPoolExecutor(max_workers=1) as pool:
        response = pool.submit(turn, base, session, text, "approver")
        end = time.monotonic() + 75
        while time.monotonic() < end and not response.done():
            pending = next((p for p in api(base, "/permission") if p["sessionID"] == session
                            and p["permission"] == "skill" and p["patterns"] == ["release"]), None)
            if pending:
                api(base, f"/permission/{pending['id']}/reply", {"reply": "once"})
                response.result()
                return pending["id"]
            time.sleep(0.2)
        if response.done():
            response.result()
        raise RuntimeError(f"No pending skill approval for {text}")


def verify(phases, root, session, keep_id, approvals):
    old = next(r for r in phases["old"] if TAIL in content(r, "tool"))
    summary = next(r for r in phases["compact"] if "[Tool result]:" in content(r, "user"))
    resumed = next(r for r in phases["resumed"] if "TURN_RESTART" in content(r, "user") and r.get("tools"))
    denied = next(r for r in phases["denied"] if content(r, "tool"))
    asking = next(r for r in phases["ask"] if HEAD in content(r, "tool"))
    versions = []
    for name in ("before", "after", "cold"):
        req = next(r for r in phases[name] if r["messages"][-1]["role"] == "tool")
        rule = next(v for v in ("V1", "V2") if f"RULE_{v}_PROBE" in content(req, "system"))
        tool = req["messages"][-1]["content"]
        recipe = next(v for v in ("V1", "V2") if f"RECIPE_{v}_PROBE" in str(tool))
        versions.append((rule, recipe))
    raw = next((root / "data").rglob("opencode.db"))
    with sqlite3.connect(raw.resolve().as_uri() + "?mode=ro", uri=True) as db:
        parts = [json.loads(data) for (data,) in db.execute("SELECT data FROM part WHERE session_id = ?", (session,))]
    result = next(p["state"] for p in parts if p["type"] == "tool" and p["tool"] == "skill")
    cut = next(p for p in parts if p["type"] == "compaction")
    text = next(m["content"] for m in summary["messages"] if m["role"] == "user")
    serialized = text.split("[Tool result]: ", 1)[1].split("\n[truncated]", 1)[0]
    facts = {
        "ordinary tool result contains both markers": HEAD in content(old, "tool") and TAIL in content(old, "tool"),
        "compactor saw the first 2000 result characters": serialized == result["output"][:2000] and len(serialized) == 2000,
        "compactor saw HEAD and truncation, omitted TAIL": HEAD in text and "[truncated]" in text and TAIL not in text,
        "raw SQLite tool result still contains both": HEAD in result["output"] and TAIL in result["output"],
        "tail_start_id equals TURN_KEEP message ID": cut.get("tail_start_id") == keep_id,
        "resumed request has summary, TURN_KEEP and TURN_RESTART": SUMMARY in content(resumed, "assistant")
            and all(x in content(resumed, "user") for x in ("TURN_KEEP", "TURN_RESTART")),
        "resumed request omits old turn and tool result": "TURN_OLD" not in content(resumed, "user") and not content(resumed, "tool"),
        "restricted catalog includes other, omits release": "<name>other</name>" in content(denied, "system")
            and "<name>release</name>" not in content(denied, "system"),
        "restricted agent still has skill tool": any(t["function"]["name"] == "skill" for t in denied["tools"]),
        "named call returns deny and no skill body": "prevents you from using this specific tool call" in content(denied, "tool")
            and HEAD not in content(denied, "tool") and TAIL not in content(denied, "tool"),
        "ask advertises release and delivers its body after approval": "<name>release</name>" in content(asking, "system")
            and TAIL in content(asking, "tool"),
        "two once approvals required distinct requests": len(set(approvals)) == 2,
        "rule and skill versions before edit / warm / cold": versions == [("V1", "V1"), ("V2", "V1"), ("V2", "V2")],
    }
    print(f"Raw skill output: {len(result['output'])} characters (includes the temporary path).")
    print("SQLite:", raw)
    print("Compacted session:", session)
    print("Rule / latest tool result, before edit, warm call, cold call:", versions)
    for label, passed in facts.items():
        print(f"{'PASS' if passed else 'FAIL'}  {label}")
    if not all(facts.values()):
        raise AssertionError(f"Inspect {root / 'requests.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="opencode")
    args = parser.parse_args()
    binary = shutil.which(args.binary)
    if not binary:
        parser.error("Provide a path to the v1.18.33 executable.")
    binary = str(Path(binary).resolve())
    root = Path(tempfile.mkdtemp(prefix="opencode-checkpoint-"))
    print("Evidence directory:", root, flush=True)
    repo = root / "project"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("OPENCODE_")}
    homes = {"OPENCODE_TEST_HOME": "home", "XDG_DATA_HOME": "data", "XDG_CONFIG_HOME": "config",
             "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache"}
    for key, folder in homes.items():
        (root / folder).mkdir()
        env[key] = str(root / folder)
    env.update(OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_DISABLE_AUTOUPDATE="1",
               OPENCODE_DISABLE_DEFAULT_PLUGINS="1", HTTP_PROXY="http://127.0.0.1:1",
               HTTPS_PROXY="http://127.0.0.1:1", NO_PROXY="localhost,127.0.0.1")
    version = subprocess.check_output([binary, "--version"], cwd=repo, env=env, text=True).strip()
    if version != "1.18.33":
        parser.error(f"Expected v1.18.33. This binary reports {version}.")
    write_skill(repo, "release", HEAD + "\n" + "x" * 2500 + "\n" + TAIL)
    write_skill(repo, "other", "Another procedure")
    write_skill(repo, "revision", "RECIPE_V1_PROBE")
    (repo / "AGENTS.md").write_text("RULE_V1_PROBE", encoding="utf8")
    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
        provider.requests = []
        Thread(target=provider.serve_forever, daemon=True).start()
        local = {"npm": "@ai-sdk/openai-compatible", "name": "Local",
                 "options": {"baseURL": f"http://127.0.0.1:{provider.server_port}/v1", "apiKey": "fixture"},
                 "models": {"probe": {"name": "Probe", "limit": {"context": 32000, "output": 2000}}}}
        config = {"enabled_providers": ["localprobe"], "model": "localprobe/probe", "small_model": "localprobe/probe",
                  "provider": {"localprobe": local}, "snapshot": False,
                  "compaction": {"auto": False, "prune": True, "tail_turns": 1},
                  "agent": {name: {"mode": "primary", "description": "Permission probe",
                             "permission": {"skill": {"*": "allow", "release": action}}}
                            for name, action in [("reviewer", "deny"), ("approver", "ask")]}}
        (repo / "opencode.json").write_text(json.dumps(config), encoding="utf8")
        phases = {}
        try:
            with opencode(binary, repo, env, root) as base:
                session = api(base, "/session", {})["id"]
                start = len(provider.requests)
                turn(base, session, "TURN_OLD")
                phases["old"] = provider.requests[start:]
                keep_id = turn(base, session, "TURN_KEEP")
                start = len(provider.requests)
                api(base, f"/session/{session}/summarize", dict(MODEL, auto=False))
                phases["compact"] = provider.requests[start:]
            with opencode(binary, repo, env, root) as base:
                start = len(provider.requests)
                turn(base, session, "TURN_RESTART")
                phases["resumed"] = provider.requests[start:]
                separate = api(base, "/session", {})["id"]
                start = len(provider.requests)
                turn(base, separate, "CHECK_DENIAL", "reviewer")
                phases["denied"] = provider.requests[start:]
                separate = api(base, "/session", {})["id"]
                start = len(provider.requests)
                approvals = [approve_once(base, separate, marker) for marker in ("ASK_ONCE", "ASK_AGAIN")]
                phases["ask"] = provider.requests[start:]
                revision = api(base, "/session", {})["id"]
                start = len(provider.requests)
                turn(base, revision, "CHANGE_BEFORE")
                phases["before"] = provider.requests[start:]
                (repo / "AGENTS.md").write_text("RULE_V2_PROBE", encoding="utf8")
                write_skill(repo, "revision", "RECIPE_V2_PROBE")
                start = len(provider.requests)
                turn(base, revision, "CHANGE_AFTER")
                phases["after"] = provider.requests[start:]
            with opencode(binary, repo, env, root) as base:
                start = len(provider.requests)
                turn(base, revision, "CHANGE_COLD")
                phases["cold"] = provider.requests[start:]
        finally:
            provider.shutdown()
            (root / "requests.json").write_text(json.dumps(provider.requests, indent=2), encoding="utf8")
    verify(phases, root, session, keep_id, approvals)


if __name__ == "__main__":
    main()
