"""Probe the reference server pinned in the DSH example. Pass the server's dist/index.js."""
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

@contextmanager
def server(entry, cwd, graph):
    proc = subprocess.Popen(
        ["node", str(entry)], cwd=cwd, env={**os.environ, "MEMORY_FILE_PATH": str(graph)},
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
    )
    def send(msg):
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", **msg}) + "\n")
        proc.stdin.flush()
    sequence = 0
    def request(method, params):
        nonlocal sequence
        sequence += 1
        send({"method": method, "params": params, "id": sequence})
        for raw in proc.stdout:
            data = json.loads(raw)
            if data.get("id") == sequence:
                if "error" in data:
                    raise RuntimeError(data["error"])
                return data["result"]
        raise EOFError("Server closed before responding")

    def call(name, **arguments):
        result = request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(result["content"])
        return result["structuredContent"]
    try:
        request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "pixel-notes-research", "version": "1"}})
        send({"method": "notifications/initialized"})
        yield call
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        proc.stdout.close()

def names(graph):
    return [e["name"] for e in graph["entities"]]

def main():
    entry = Path(sys.argv[1]).resolve(strict=True)
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        a, b = root / "project-a", root / "project-b"
        a.mkdir()
        b.mkdir()
        graph = root / "shared.jsonl"
        with server(entry, a, graph) as call:
            result = call("create_entities", entities=[
                {"name": "release", "entityType": "workflow", "observations": ["refresh atlas"]},
                {"name": "manifest", "entityType": "artifact", "observations": ["owner: ci"]}])
            assert names(result) == ["release", "manifest"]
            relation = {"from": "release", "to": "manifest", "relationType": "requires"}
            call("create_relations", relations=[relation])
            duplicate = call("create_entities", entities=[
                {"name": "release", "entityType": "workflow", "observations": ["SECOND_NOTE"]}])
            assert duplicate["entities"] == []
            assert names(call("search_nodes", query="SECOND_NOTE")) == []
        with server(entry, b, graph) as call:
            match = call("search_nodes", query="ATLAS")
            assert names(match) == ["release"] and match["relations"] == [relation]
            assert names(call("search_nodes", query="map")) == []
            target = call("open_nodes", names=["manifest"])
            assert target["entities"][0]["observations"] == ["owner: ci"]
            print("other cwd, same file:", names(match), match["relations"])
            print("open neighbor:", target["entities"])
        with server(entry, b, root / "other.jsonl") as call:
            assert names(call("read_graph")) == []
            print("same cwd, different file: empty graph")
if __name__ == "__main__":
    main()
