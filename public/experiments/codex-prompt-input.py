"""Compare the prompt debugger's input and memory markers in Codex CLI 0.169.0."""
import json, os, subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    repo, home = root / "project", root / "codex"
    repo.mkdir()
    memory = home / "memories_v2"
    memory.mkdir(parents=True)
    (memory / "memory_summary.md").write_text("v1\nSUMMARY_7392", encoding="utf-8")
    for enabled in (False, True):
        (home / "config.toml").write_text(
            f"[features]\nmemories={str(enabled).lower()}\n"
            '[memories]\nversion="v2"\nuse_memories=true\n', encoding="utf-8")
        raw = subprocess.check_output(["codex", "debug", "prompt-input", "INPUT_6185"],
                                      env=dict(os.environ, CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(home)),
                                      cwd=repo, text=True, encoding="utf-8", timeout=25)
        prompt = json.dumps(json.loads(raw))
        print(enabled, "INPUT_6185" in prompt, "SUMMARY_7392" in prompt)
