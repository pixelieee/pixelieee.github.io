"""Experiment: does a restored skill get re-archived on the next curator pass? (pinned bf0203a)"""
import json, os, sys, tempfile, pathlib
from datetime import datetime, timedelta, timezone
repo = sys.argv[1]
home = pathlib.Path(tempfile.mkdtemp(prefix="hermes-home-"))
os.environ["HERMES_HOME"] = str(home)
sys.path.insert(0, repo)
skill = home / "skills" / "demo"
skill.mkdir(parents=True)
(skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo skill\n---\n# demo\n", encoding="utf-8")

from tools import skill_usage as u
from agent import curator as c
u.mark_agent_created("demo")
usage = home / "skills" / ".usage.json"
data = json.loads(usage.read_text(encoding="utf-8"))
old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
rec = data["demo"] if "demo" in data else data.setdefault("skills", {})["demo"]
rec.update(use_count=3, last_used_at=old, last_viewed_at=old, created_at=old)
usage.write_text(json.dumps(data), encoding="utf-8")

def state():
    d = json.loads(usage.read_text(encoding="utf-8")); r = d.get("demo") or d.get("skills", {}).get("demo")
    return r.get("state"), (home / "skills" / "demo").exists(), any((home/"skills"/".archive").rglob("SKILL.md")) if (home/"skills"/".archive").exists() else False
print("record keys:", sorted(rec))
print("pass 1:", c.apply_automatic_transitions(), "-> state/dir/archived:", state())
print("restore:", u.restore_skill("demo"), "->", state())
print("pass 2:", c.apply_automatic_transitions(), "-> state/dir/archived:", state())
