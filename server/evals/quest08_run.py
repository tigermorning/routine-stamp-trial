"""Main Quest 08: 만든 대화를 /api/chat 에 흘려 보내고(트레이스는 Langfuse 로), 턴마다 이벤트·답을 로컬 파일에 남긴다.

  python evals/quest08_run.py --set a --release v1-baseline --out evals/quest08/run_a_v1.json
환경: .env 값(LLM_*, LANGFUSE_*)을 이 프로세스 안에서만 읽는다. 대화는 모두 지어낸 것이다(실제 개인정보 없음).
트레이스에는 ENV=quest08, K_REVISION=<release> 로 환경·버전을 달고, 원문 수집(LANGFUSE_CAPTURE_TEXT=on)을 켠다(지어낸 대화라 개인정보 약속과 충돌 없음).
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def load_env(path):
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in raw and not raw.lstrip().startswith("#"):
            k, v = raw.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def parse(text):
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--env", default=str(HERE.parents[1] / ".env"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    load_env(a.env)
    os.environ["ENV"] = "quest08"
    os.environ["K_REVISION"] = a.release
    os.environ["LANGFUSE_CAPTURE_TEXT"] = "on"
    convs = json.loads((HERE / "quest08" / f"convs_{a.set}.json").read_text(encoding="utf-8"))
    if a.only:
        convs = [c for c in convs if c["id"] in a.only.split(",")]
    from fastapi.testclient import TestClient

    import main
    import tracing

    main.RATE_PER_IP = main.RATE_ALL = 10**6
    client = TestClient(main.app)
    rows = []
    for conv in convs:
        history = []
        for n, user in enumerate(conv["turns"], 1):
            history.append({"role": "user", "content": user})
            body = {"messages": history, "context": conv.get("context")}
            resp = client.post("/api/chat", json=body)
            ev = parse(resp.text)
            reply = "".join(e.get("text", "") for e in ev if e["type"] == "delta")
            done = next((e for e in ev if e["type"] == "done"), {})
            kind = done.get("type") and "reply" or next((e["type"] for e in ev if e["type"] in ("crisis", "scope", "error")), "none")
            rows.append({"conv": conv["id"], "type": conv["type"], "turn": n, "user": user, "reply": reply, "kind": kind,
                         "mode": done.get("mode"), "ok": done.get("ok"), "notice": next((e.get("key") for e in ev if e["type"] == "notice"), None),
                         "cards": [c.get("id") for c in done.get("cards", [])], "release": a.release})
            if reply:
                history.append({"role": "assistant", "content": reply})
            print(conv["id"], n, kind, done.get("mode"), (reply[:50] or "").replace("\n", " "))
    c = tracing.get_client()
    if c:
        c.flush()
    Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", len(rows), "turns ->", a.out)


if __name__ == "__main__":
    main()
