"""대화 품질 실측 프로브(진짜 LLM). 서버 코드를 같은 프로세스 안에서 부른다.

  python evals/probe.py --env <.env 경로> --tone      말투 준수율: casual 설정+존댓말 기록, polite 설정+반말 기록 각 3턴(호출 6번: 모드 고르기는 듣기로 고정해 모델 호출을 아낀다)
  python evals/probe.py --env <.env 경로> --convo     사용자가 실제로 겪은 4턴 대화를 이어서 재생(턴마다 호출 2번 = 8번)
키는 이 프로세스 안에서만 쓰고 출력하지 않는다. 답 본문은 출력한다.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

POLITE_HISTORY = [
    {"role": "user", "content": "요즘 운동 시작이 안 돼"},
    {"role": "assistant", "content": "운동을 시작하기가 쉽지 않으시군요. 어떤 점이 가장 어려우세요?"},
    {"role": "user", "content": "퇴근하면 너무 피곤해서"},
    {"role": "assistant", "content": "퇴근 후에는 많이 지치시죠. 그래도 해 보고 싶으신 마음은 있으시네요."},
]
CASUAL_HISTORY = [
    {"role": "user", "content": "요즘 운동 시작이 안 돼요"},
    {"role": "assistant", "content": "운동 시작이 쉽지 않구나. 뭐가 제일 힘들어?"},
    {"role": "user", "content": "퇴근하면 너무 피곤해서요"},
    {"role": "assistant", "content": "퇴근하면 지치지. 그래도 해 보고 싶은 마음은 있구나."},
]
TONE_CASES = [
    ("casual", POLITE_HISTORY, ["그래서 주말에만 하려고 했는데 그것도 잘 안 돼", "수영을 해 볼까 생각 중이야", "너는 어떻게 생각해?"]),
    ("polite", CASUAL_HISTORY, ["그래서 주말에만 하려고 했는데 그것도 잘 안 돼요", "수영을 해 볼까 생각 중이에요", "당신은 어떻게 생각하세요?"]),
]
# 사용자가 배포된 도우미를 써 보며 실제로 보낸 말(2026-10-21), 순서대로 이어서 보낸다
CONVO = [
    "3일을 기다리지 않고 할 일 칸을 더 늘리고 싶어",
    "수영, 필라테스, 학교, 식단, 병원 일정을 넣으려고 해",
    "그런데 내가 너에게 이것을 말하는 게 무슨 의미가 있는 거야?",
    "내가 이 앱을 사용하는 이유는 일정관리를 위해서야. 얘기하는 것으로는 안 돼",
]


def load_env(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"):
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def post(client, body):
    r = client.post("/api/chat", json=body)
    ev = [json.loads(x) for x in r.text.splitlines() if x]
    return {
        "mode": next((e.get("mode") for e in ev if e["type"] == "mode"), None),
        "text": "".join(e.get("text", "") for e in ev if e["type"] == "delta").strip(),
        "last": ev[-1]["type"] if ev else None,
        "ok": next((e.get("ok") for e in ev if e["type"] == "done"), None),
        "events": [e["type"] for e in ev if e["type"] not in ("delta", "mode")],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--tone", action="store_true")
    ap.add_argument("--convo", action="store_true")
    a = ap.parse_args()
    load_env(a.env)
    from fastapi.testclient import TestClient

    from judge import polite_ratio
    import main as app_main

    real = app_main.get_llm()
    calls = {"n": 0}

    class Counting:
        def __init__(self, inner, force_listen=False):
            self.inner, self.force_listen = inner, force_listen

        def complete_json(self, s, u):
            if self.force_listen:
                return {"mode": "listen", "card_ids": []}
            calls["n"] += 1
            return self.inner.complete_json(s, u)

        def chat_stream(self, m):
            calls["n"] += 1
            return self.inner.chat_stream(m)

        def complete_text(self, m, t):
            calls["n"] += 1
            return self.inner.complete_text(m, t)

    app_main.RATE_PER_IP = app_main.RATE_ALL = 10**6
    if a.tone:
        app_main.app.dependency_overrides[app_main.get_llm] = lambda: Counting(real, force_listen=True)
        client = TestClient(app_main.app)
        total = passed = 0
        for speech, history, finals in TONE_CASES:
            for text in finals:
                body = {"messages": history + [{"role": "user", "content": text}], "character": {"speech": speech, "emoji": "none"}}
                res = post(client, body)
                ratio = polite_ratio(res["text"])
                ok = ratio is not None and ((ratio <= 0.4) if speech == "casual" else (ratio >= 0.6))
                total += 1
                passed += ok
                print(f"[{'준수' if ok else '위반'}] 설정={speech} 존댓말비율={ratio} 이벤트={res['events']}\n   답: {res['text']}")
        print(f"\n말투 준수 {passed}/{total}, 진짜 LLM 호출 {calls['n']}번")
    if a.convo:
        app_main.app.dependency_overrides[app_main.get_llm] = lambda: Counting(real)
        client = TestClient(app_main.app)
        history, qends = [], 0
        for text in CONVO:
            history.append({"role": "user", "content": text})
            res = post(client, {"messages": history})
            ends_q = res["text"].rstrip(" 😊🌟✨").endswith(("?", "？"))
            qends += ends_q
            print(f"사용자: {text}\n  → 모드={res['mode']} 이벤트={res['events']} 질문으로 끝남={ends_q}\n  도우미: {res['text']}\n")
            if res["text"]:
                history.append({"role": "assistant", "content": res["text"]})
        print(f"질문으로 끝난 답 {qends}/{len(CONVO)}, 진짜 LLM 호출 {calls['n']}번")


if __name__ == "__main__":
    main()
