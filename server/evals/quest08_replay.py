"""데이터셋 항목을 /api/chat 에 다시 흘려 보낸다(변형 하나 = 릴리스 이름 하나). 트레이스는 Langfuse(environment=quest08, release=<이름>).
  CLAUDE_THINKING=off python evals/quest08_replay.py --release exp-thinking-off --out evals/quest08/replay_thinking_off.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
ap = argparse.ArgumentParser()
ap.add_argument("--release", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--data", default="dataset.json")
a = ap.parse_args()
for line in (HERE.parents[1] / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip(chr(34)+chr(39)))
os.environ.update(ENV="quest08", K_REVISION=a.release, LANGFUSE_CAPTURE_TEXT="on")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import tracing  # noqa: E402

main.RATE_PER_IP = main.RATE_ALL = 10**6
client = TestClient(main.app)
items = json.loads((HERE / "quest08" / a.data).read_text(encoding="utf-8"))
out = []
for it in items:
    resp = client.post("/api/chat", json={"messages": it["messages"], "context": it.get("context")})
    ev = [json.loads(x) for x in resp.text.splitlines() if x.strip()]
    reply = "".join(e.get("text", "") for e in ev if e["type"] == "delta")
    done = next((e for e in ev if e["type"] == "done"), {})
    out.append({"id": it["id"], "group": it.get("group"), "reply": reply, "mode": done.get("mode"), "ok": done.get("ok"),
                "kind": "reply" if done else next((e["type"] for e in ev if e["type"] in ("crisis", "scope", "error")), "none")})
    print(it["id"], it.get("group"), len(reply), done.get("mode"))
c = tracing.get_client()
if c:
    c.flush()
Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved", len(out), a.out)
