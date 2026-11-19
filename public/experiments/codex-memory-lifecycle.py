"""Reproduce the Codex CLI 0.169.0 memory experiment. Usage: python codex-memory-lifecycle.py blank|stale|malformed"""
import argparse
import gzip
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FACT = "check-atlas-47"
PRIOR = "PRIOR_ONLY_63"
OLD_SUMMARY = "\n".join(("v1", "## User Profile", "## User preferences", "## General Tips",
                         "## What's in Memory", PRIOR, ""))


class Fixture(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        encoding = self.headers.get("Content-Encoding", "").lower()
        if encoding == "gzip":
            body = gzip.decompress(body)
        elif encoding == "zstd":
            import zstandard
            body = zstandard.ZstdDecompressor().stream_reader(body).read()
        request = json.loads(body)
        model = request["model"]
        evidence = json.dumps(request["input"])
        self.server.models.append(model)
        if model == "fixture-extract":
            retain = "SYNTH_KEEP" in evidence and "SYNTH_NO_SIGNAL" not in evidence
            answer = json.dumps({"rollout_summary": "Use " + FACT if retain else "",
                                 "rollout_slug": "atlas-check" if retain else ""})
            if self.server.case == "malformed" and not retain:
                answer = "invalid-json-fixture"
        else:
            # No tool call. The consolidation worker leaves every memory file as found.
            answer = "Finished fixture."
        rid = "res" + str(len(self.server.models))
        events = [
            {"type": "response.created", "response": {"id": rid}},
            {"type": "response.output_item.done", "item": {"type": "message", "id": rid + "-msg",
             "role": "assistant", "content": [{"type": "output_text", "text": answer}]}},
            {"type": "response.completed", "response": {"id": rid, "usage": {
             "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}},
        ]
        stream = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(stream)))
        self.end_headers()
        self.wfile.write(stream)

    def log_message(self, *args):
        pass


class App:
    def __init__(self, proc):
        self.proc, self.responses, self.pending, self.counter = proc, queue.Queue(), [], 0
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        for line in self.proc.stdout:
            self.responses.put(json.loads(line))

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def take(self, wanted):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            for i, msg in enumerate(self.pending):
                if wanted(msg):
                    return self.pending.pop(i)
            self.pending.append(self.responses.get(timeout=max(.01, deadline - time.monotonic())))
        raise TimeoutError("App Server response")

    def call(self, method, params):
        self.counter += 1
        self.send({"id": self.counter, "method": method, "params": params})
        result = self.take(lambda msg: msg.get("id") == self.counter)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]

    def thread(self, repo, memories):
        return self.call("thread/start", {"cwd": str(repo), "config": {"features.memories": memories},
                         "environments": [{"environmentId": "local", "cwd": str(repo)}]})["thread"]["id"]

    def turn(self, thread, message):
        self.call("turn/start", {"threadId": thread, "input": [{"type": "text", "text": message}]})
        event = self.take(lambda m: m.get("method") == "turn/completed" and m["params"]["threadId"] == thread)
        assert event["params"]["turn"]["status"] == "completed", event


def memory_state(dbfile):
    with sqlite3.connect(dbfile) as db:
        jobs = db.execute("SELECT kind,status,last_error FROM jobs ORDER BY kind,job_key").fetchall()
        rows = db.execute("SELECT rollout_slug,selected_for_phase2 FROM stage1_outputs").fetchall()
    return jobs, rows


def wait_for_pass(dbfile, expected, written):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        jobs, rows = memory_state(dbfile)
        global_jobs = [j for j in jobs if j[0] == "memory_consolidate_global"]
        if global_jobs and global_jobs[0][1] == expected and len(rows) == written:
            return global_jobs[0][1:], rows
        time.sleep(.1)
    raise TimeoutError((jobs, rows))


def run(case):
    root = Path(tempfile.mkdtemp(prefix="codex-memory-study-"))
    home, a, b = [root / name for name in ("home", "A", "B")]
    for path in (home, a, b):
        path.mkdir()
    for repo in (a, b):
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    memory = home / "memories_v2"
    memory.mkdir()
    if case != "blank":
        (memory / "memory_summary.md").write_text(OLD_SUMMARY, encoding="utf-8")
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    provider.models = []
    provider.case = case
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    config = ('model="fixture-foreground"\nmodel_provider="probe"\napproval_policy="never"\n'
              'sandbox_mode="read-only"\n[features]\nmemories=true\n[memories]\nversion="v2"\n'
              'extract_model="fixture-extract"\nconsolidation_model="fixture-consolidate"\n'
              '[model_providers.probe]\nname="Probe"\nwire_api="responses"\nrequest_max_retries=0\n'
              f'stream_max_retries=0\nbase_url="http://127.0.0.1:{provider.server_port}/v1"\n')
    for path in (a, b):
        config += '[projects.' + json.dumps(str(path)) + ']\ntrust_level="trusted"\n'
    (home / "config.toml").write_text(config, encoding="utf-8")
    env = dict(os.environ, CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(home),
               NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    print("Temporary evidence:", root, flush=True)
    with open(root / "app-server.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(["codex", "app-server", "--listen", "stdio://"], cwd=a, env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                text=True, encoding="utf-8")
        app = App(proc)
        try:
            app.call("initialize", {"clientInfo": {"name": "notes-probe", "version": "1"},
                                    "capabilities": {"experimentalApi": True}})
            app.send({"method": "initialized"})
            old, empty = app.thread(a, False), app.thread(a, False)
            app.turn(old, "SYNTH_KEEP: use " + FACT)
            app.turn(empty, "SYNTH_NO_SIGNAL")
            # The only fixture edit to the index is the clock of these two temporary threads.
            age = int((time.time() - 8 * 3600) * 1000)
            state = next(home.glob("state_*.sqlite"))
            with sqlite3.connect(state) as db:
                db.execute("UPDATE threads SET updated_at_ms=? WHERE id IN (?,?)", (age, old, empty))
            trigger = app.thread(b, True)
            app.turn(trigger, "Run the first pass.")
            dbfile = next(home.glob("memories_v2_*.sqlite"))
            expected = "error" if case == "blank" else "done"
            status, rows = wait_for_pass(dbfile, expected, 1)
            files = list((memory / "rollout_summaries").glob("*.md"))
            fresh = app.thread(b, True)
            summary = app.call("thread/memory/read", {"threadId": fresh})["summary"] or ""
            with sqlite3.connect(dbfile) as db:
                extract = db.execute("SELECT status,retry_remaining,retry_at FROM jobs "
                                     "WHERE kind='memory_stage1' ORDER BY status").fetchall()
            print("extract jobs:", [job[0] for job in extract])
            print("first pass:", status, "rows:", rows, "source files:", len(files))
            print("new thread:", "prior =", PRIOR in summary, "new fact =", FACT in summary)
            assert len(files) == 1 and FACT in files[0].read_text(encoding="utf-8")
            assert (PRIOR in summary) == (case != "blank") and FACT not in summary
            assert status[1] == ("failed_invalid_artifacts" if case == "blank" else None)
            if case == "malformed":
                assert [job[0] for job in extract] == ["done", "error"]
                assert extract[1][2] > time.time()
            else:
                assert [job[0] for job in extract] == ["done", "done"]
            if case == "stale":
                app.turn(old, "SYNTH_NO_SIGNAL: this source no longer contributes.")
                with sqlite3.connect(state) as db:
                    db.execute("UPDATE threads SET updated_at_ms=? WHERE id=?", (age + 600_000, old))
                app.turn(fresh, "Run the revised-source pass.")
                status, rows = wait_for_pass(dbfile, "pending", 0)
                files = list((memory / "rollout_summaries").glob("*.md"))
                print("during cooldown:", status, "rows:", rows, "source files:", len(files))
                assert len(files) == 1
                # Advance only the isolated job's cooldown clock to observe the next eligible pass.
                with sqlite3.connect(dbfile) as db:
                    db.execute("UPDATE jobs SET finished_at=? WHERE kind='memory_consolidate_global'",
                               (int(time.time()) - 7 * 3600,))
                after = app.thread(b, True)
                app.turn(after, "Scan after the synthetic cooldown.")
                status, rows = wait_for_pass(dbfile, "done", 0)
                files = list((memory / "rollout_summaries").glob("*.md"))
                print("after empty re-extraction:", status, "rows:", rows, "source files:", len(files))
                assert not files and (memory / "memory_summary.md").read_text(encoding="utf-8") == OLD_SUMMARY
        finally:
            proc.terminate()
            proc.wait(timeout=10)
            provider.shutdown()
            provider.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["blank", "stale", "malformed"])
    run(parser.parse_args().case)
