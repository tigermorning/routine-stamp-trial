"""도우미 평가 실행기. 서버 코드를 같은 프로세스 안에서 부른다(HTTP 서버 불필요).

  python evals/run_eval.py --fake                 가짜 LLM(모델 호출 0번, 흐름만 확인. 내용 검사는 대부분 실패하는 것이 정상)
  python evals/run_eval.py --real                 진짜 LLM, core 사례만(약 6건, 호출 약 12번)
  python evals/run_eval.py --real --all           진짜 LLM, 전체 사례
  python evals/run_eval.py --real --only a,b      진짜 LLM, 고른 사례만
  --env PATH                                      LLM_PROVIDER·LLM_API_KEY·LLM_MODEL 을 읽을 .env 경로(이 프로세스 안에서만 쓰고 출력하지 않는다)

진짜 호출은 비용이 든다. 호출 횟수를 마지막에 보여 준다. 답 본문은 화면에 보이지만 키는 나오지 않는다.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))


def load_env(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"):
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


class Counting:
    """진짜 LLM 호출 횟수를 센다."""

    def __init__(self, inner):
        self.inner, self.calls = inner, 0

    def complete_json(self, *a, **k):
        self.calls += 1
        return self.inner.complete_json(*a, **k)

    def chat_stream(self, *a, **k):
        self.calls += 1
        return self.inner.chat_stream(*a, **k)


def run_case(client, main, case, character=None):
    body = {"messages": [], "context": case.get("context"), "todos": case.get("todos", [])}
    if character:
        body["character"] = character
    for m in case["messages"]:  # 문자열은 사용자 말, 사전은 {role, content} 그대로(여러 턴 사례)
        body["messages"].append(m if isinstance(m, dict) else {"role": "user", "content": m})
    r = client.post("/api/chat", json=body)
    events = [json.loads(x) for x in r.text.splitlines() if x]
    return {
        "events": [e["type"] for e in events if e["type"] not in ("mode", "delta", "notice")],
        "mode": next((e["mode"] for e in events if e["type"] == "mode"), None),
        "text": "".join(e.get("text", "") for e in events if e["type"] == "delta"),
        "cards": [c["id"] for e in events if e["type"] == "done" for c in e.get("cards", [])],
        "notice": next((e["key"] for e in events if e["type"] == "notice"), None),
        "done_ok": next((e["ok"] for e in events if e["type"] == "done"), None),
    }


def main_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--env", default="")
    ap.add_argument("--character", default="", help='JSON, 예: {"name":"하루","speech":"casual","emoji":"often"}')
    a = ap.parse_args()
    if a.real == a.fake:
        sys.exit("--fake 와 --real 중 하나를 고르세요.")
    if a.fake:
        os.environ["LLM_PROVIDER"] = "fake"
    elif a.env:
        load_env(a.env)
    from fastapi.testclient import TestClient

    import cards as cardlib
    import main
    from judge import judge

    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]
    if a.only:
        want = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in want]
    elif not a.all and a.real:
        cases = [c for c in cases if c.get("core")]
    character = json.loads(a.character) if a.character else None
    llm = Counting(main.get_llm())
    main.app.dependency_overrides[main.get_llm] = lambda: llm
    main.RATE_PER_IP = main.RATE_ALL = 10**6
    client = TestClient(main.app)
    failed = 0
    for case in cases:
        before = llm.calls
        case_character = case.get("character") or character  # 사례에 말투 설정이 있으면 그것을 쓴다
        res = run_case(client, main, case, case_character)
        res["llm_calls"] = llm.calls - before
        fails = judge(case, res, cardlib.CARDS, case_character)
        failed += bool(fails)
        print(f"[{'FAIL' if fails else 'PASS'}] {case['id']}  모드={res['mode']} 이벤트={res['events']} 카드={res['cards']} 호출={res['llm_calls']}")
        if res["text"]:
            print("   답:", res["text"].replace("\n", " / "))
        for f in fails:
            print("   ✗", f)
    kind = "가짜 LLM 호출(비용 없음)" if a.fake else "진짜 LLM 호출(비용 발생)"
    print(f"\n{len(cases) - failed}/{len(cases)} 통과, {kind} {llm.calls}번. 휴리스틱 검사는 사람이 답을 읽고 확인해야 한다.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main_cli())
