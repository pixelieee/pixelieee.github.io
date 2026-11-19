"""Refresh a project skill and read a seeded V2 memory through Codex CLI 0.169.0 App Server."""
import json, os, subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    home, repo, sibling = [root / s for s in ("home", "repo", "sibling")]
    for folder in (home, repo, sibling):
        folder.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    config = "[projects." + json.dumps(str(repo)) + ']\ntrust_level = "trusted"\n'
    (home / "config.toml").write_text(config, encoding="utf-8")
    env = dict(os.environ, CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(home))
    for flags in ([], ["--enable", "memories"]):
        cmd = ["codex", *flags, "features", "list"]
        lines = subprocess.check_output(cmd, cwd=repo, env=env, text=True)
        print(next(s.split() for s in lines.splitlines() if s.startswith("memories ")))

    p = subprocess.Popen(["codex", "--enable", "memories", "app-server", "--listen", "stdio://"],
                         cwd=repo, env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True, encoding="utf-8")
    def send(message):
        p.stdin.write(json.dumps(message) + "\n")
        p.stdin.flush()

    def call(i, method, params):
        send(dict(id=i, method=method, params=params))
        for line in p.stdout:
            msg = json.loads(line)
            if msg.get("id") == i:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg["result"]
        raise EOFError(method)

    def snapshot(i, cwd):
        result = call(i, "skills/list", {"cwds": [str(cwd)], "forceReload": True})
        return [(s["description"], s["scope"], "BODY_SENTINEL" in json.dumps(s))
                for row in result["data"] for s in row["skills"] if s["name"] == "notes-probe"]

    try:
        call(1, "initialize", {"clientInfo": {"name": "notes-probe", "version": "1"},
                               "capabilities": {"experimentalApi": True}})
        send({"method": "initialized"})
        folder = repo / ".agents" / "skills" / "notes-probe"
        folder.mkdir(parents=True)
        print(snapshot(2, repo))
        for i, marker in enumerate(("alpha", "beta"), 3):
            skill = f"---\nname: notes-probe\ndescription: Marker {marker}\n---\nBODY_SENTINEL\n"
            (folder / "SKILL.md").write_text(skill, encoding="utf-8")
            print(snapshot(i, repo))
        print(snapshot(5, sibling))

        memory = home / "memories_v2"
        memory.mkdir(exist_ok=True)
        (memory / "memory_summary.md").write_text("v1\nSUMMARY_7392\n", encoding="utf-8")
        for i, use in ((6, False), (8, True)):
            cfg = {"memories.version": "v2", "memories.use_memories": use,
                   "memories.generate_memories": False}
            thread = call(i, "thread/start", {"cwd": str(repo), "ephemeral": True, "config": cfg})
            response = call(i + 1, "thread/memory/read", {"threadId": thread["thread"]["id"]})
            summary = (response["summary"] or "").splitlines()
            print("server", use, "SUMMARY_7392" in summary)
    finally:
        p.terminate()
        p.wait(timeout=10)
