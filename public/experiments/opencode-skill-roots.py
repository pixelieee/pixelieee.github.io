"""Run the OpenCode v1.18.33 duplicate-name experiment without a model.

Usage: python opencode-skill-roots.py [path-to-opencode]
The eight discovery results are saved under a new temporary directory.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def write_skill(repo, folder, name, description, body):
    path = repo / folder / "SKILL.md"
    path.parent.mkdir(parents=True)
    frontmatter = f"description: {description}\n" if description else ""
    path.write_text(f"---\nname: {name}\n{frontmatter}---\n{body}\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="opencode")
    args = parser.parse_args()
    binary = shutil.which(args.binary)
    if not binary:
        parser.error("Provide a path to the v1.18.33 executable.")
    binary = str(Path(binary).resolve())
    root = Path(tempfile.mkdtemp(prefix="opencode-skill-roots-"))
    project = root / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("OPENCODE_")}
    homes = {"OPENCODE_TEST_HOME": "home", "XDG_CONFIG_HOME": "config", "XDG_DATA_HOME": "data",
             "XDG_CACHE_HOME": "cache", "XDG_STATE_HOME": "state"}
    for key, folder in homes.items():
        (root / folder).mkdir()
        env[key] = str(root / folder)
    env.update(OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_DISABLE_AUTOUPDATE="1",
               OPENCODE_DISABLE_DEFAULT_PLUGINS="1", HTTP_PROXY="http://127.0.0.1:1",
               HTTPS_PROXY="http://127.0.0.1:1", NO_PROXY="localhost,127.0.0.1")
    version = subprocess.check_output([binary, "--version"], cwd=project, env=env, text=True).strip()
    if version != "1.18.33":
        parser.error(f"Expected v1.18.33. This binary reports {version}.")

    write_skill(project, ".opencode/skills/a", "probe", "repo description", "BODY_REPO_MARKER")
    write_skill(project, "extra/b", "probe", "extra description", "BODY_EXTRA_MARKER")
    write_skill(project, "extra/quiet", "quiet", "", "BODY_QUIET_MARKER")
    (project / "opencode.json").write_text(json.dumps({"skills": {"paths": ["extra"]}}), encoding="utf8")

    counts = Counter()
    inventories = []
    print("Evidence directory:", root, flush=True)
    for _ in range(8):
        raw = subprocess.check_output([binary, "debug", "skill"], cwd=project, env=env, encoding="utf8")
        records = json.loads(raw)
        inventories.append(records)
        skills = {record["name"]: record for record in records}
        marker = skills["probe"]["content"].strip()
        if marker not in ("BODY_REPO_MARKER", "BODY_EXTRA_MARKER") or skills["quiet"].get("description"):
            raise AssertionError(f"Unexpected fixture records in {root}")
        counts[marker] += 1
        print(marker, "quiet description:", skills["quiet"].get("description"))
    (root / "inventories.json").write_text(json.dumps(inventories, indent=2), encoding="utf8")
    print("Observed winners:", dict(counts))


if __name__ == "__main__":
    main()
