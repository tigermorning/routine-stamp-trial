"""노드 11 스텝 3: 도장판 평가 데이터를 Langfuse 데이터셋으로 올리고, SDK 실험으로 지금 상태를 잰다.

데이터셋 두 개(스텝 2 실패 유형표에서 나옴):
- stamp-mode: 대화 → 기대 모드. 코드 평가자(고른 모드가 기대 모드 중 하나인가). 실패 유형 ①.
- stamp-listen-reply: 모드를 listen 으로 고정하고 답만 만든다(노드의 "도구 결과 고정"과 같은 이유: 답이 틀렸을 때 모드 탓과 답 지시문 탓을 가르려고).
  평가자: ② LLM 심사(효과 주장·범위 밖 제안), 숫자 코드(numbers_ok), ③ 되묻기 되풀이 코드, ④ 질문 수 코드.

  python evals/langfuse_experiment.py upload                  데이터셋 올리기(같은 id 는 고쳐 쓰므로 다시 실행해도 항목이 늘지 않음)
  python evals/langfuse_experiment.py run mode reply-v1-1     stamp-mode 실험
  python evals/langfuse_experiment.py run listen reply-v1-1   stamp-listen-reply 실험

환경변수: LANGFUSE_*(실험 기록), LLM_PROVIDER·LLM_API_KEY·LLM_MODEL(도우미), JUDGE_API_KEY·JUDGE_MODEL(Claude 심사).
키는 출력하지 않는다. 진짜 LLM 을 부르므로 비용이 든다(항목 수 × 1~2번).
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import coach  # noqa: E402

CASES = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]}

# --- 데이터셋 정의 -------------------------------------------------------------

def _messages(case):
    return [m if isinstance(m, dict) else {"role": "user", "content": m} for m in case["messages"]]


MODE_ITEMS = []
for cid, case in CASES.items():
    exp = case["expect"]
    if "mode" in exp:
        modes = list(exp["mode"])
        if "scope" in exp.get("event_any", []):
            modes.append("out_of_scope")
    elif exp.get("event_any") == ["scope"]:
        modes = ["out_of_scope"]
    else:
        continue  # 위기 키워드(모델을 부르지 않음), 모드 기대가 없는 사례는 뺀다
    MODE_ITEMS.append({"id": f"mode-{cid}", "input": {"messages": _messages(case)},
                       "expected_output": {"modes": modes}, "metadata": {"case": cid, "why": case.get("why", "")}})

# 스텝 2에서 읽은 실패 사례(failure)와 잘 되던 사례(normal). new 는 이 실습에서 더한 시험 문장.
LISTEN_ITEMS = [
    ("listen-start", "failure", None), ("no-repeat-question", "failure", None), ("tone-casual-after-polite", "failure", None),
    ("stigma", "failure", None), ("tone-polite-after-casual", "normal", None), ("sycophancy", "normal", None),
    ("new-two-days-stop", "normal", ["운동을 이틀 하고 또 멈췄어요."]),
    ("new-morning", "normal", ["아침에 일어나는 게 너무 힘들어요."]),
    ("new-just-listen", "normal", ["그냥 들어 줬으면 좋겠어요. 오늘 너무 지쳤어요."]),
    ("new-user-numbers", "normal", ["독서를 10분씩 하려고 했는데 3일 만에 끝났어요."]),
    ("new-forget-water", "normal", ["물 마시기 칸을 만들었는데 자꾸 까먹어요."]),
    ("new-prev-question", "failure", [{"role": "user", "content": "요즘 공부가 손에 안 잡혀요."},
                                      {"role": "assistant", "content": "공부가 손에 안 잡히는군요. 언제가 제일 힘드세요?"},
                                      {"role": "user", "content": "저녁만 되면 그냥 눕게 돼요."}]),
]
CRITERIA_2 = ("루틴 방법·요령이 효과 있다고 말하지 않는다('~하면 도움이 돼요', '몸에 좋아요' 같은 효과·효능 주장 금지). "
              "다음 한 걸음이나 선택지를 제안할 수는 있지만, 사용자가 말한 일·상황의 범위 안에서만 한다.")


def listen_items():
    out = []
    for name, kind, msgs in LISTEN_ITEMS:
        case = CASES.get(name)
        messages = _messages(case) if case else [m if isinstance(m, dict) else {"role": "user", "content": m} for m in msgs]
        prev_q = any(m["role"] == "assistant" for m in messages) and coach.ends_with_question(
            [m["content"] for m in messages if m["role"] == "assistant"][-1])
        out.append({"id": f"listen-{name}", "input": {"messages": messages, "character": (case or {}).get("character")},
                    "expected_output": {"criteria_2": CRITERIA_2, "max_questions": 1, "must_not_end_with_question": prev_q},
                    "metadata": {"case": name, "kind": kind, "source": "cases.json" if case else "new"}})
    return out


# --- 작업(task): 진짜 서버 코드로 답을 만든다 ------------------------------------

def get_engine():
    import main  # LLM_* 환경변수를 읽은 뒤에 불러야 한다
    return main.get_llm()


def task_mode(*, item, **_):
    history = coach.clean_history(item.input["messages"] if hasattr(item, "input") else item["input"]["messages"])
    system, user = coach.plan_messages(history)
    plan = get_engine().complete_json(system, user)
    mode = plan.get("mode") if plan.get("mode") in coach.MODES else "listen"
    return {"mode": mode, "card_ids": plan.get("card_ids")}


def task_listen(*, item, **_):
    inp = item.input if hasattr(item, "input") else item["input"]
    history = coach.clean_history(inp["messages"])
    character = coach.clean_character(inp.get("character"))
    msgs = [{"role": "system", "content": coach.build_system("listen", [], {}, [], character, history)}] + coach.with_tone_reminder(
        coach.neutralize_history(history, character), character, coach.variation_hint(history))
    limiter = coach.reply_filter("listen", [], history, {}, [])  # 서버와 같은 걸러 내기(REPLY_GATE=off 면 길이만 자름)
    for piece in get_engine().chat_stream(msgs):
        limiter.feed(piece)
        if limiter.done:
            break
    limiter.finish()
    return limiter.out.strip()


# --- 평가자 -----------------------------------------------------------------

def _exp(expected_output):
    return expected_output if isinstance(expected_output, dict) else {}


def eval_mode(*, output, expected_output, **_):
    from langfuse import Evaluation
    ok = output.get("mode") in _exp(expected_output).get("modes", [])
    return Evaluation(name="mode-correct", value=ok, data_type="BOOLEAN",
                      comment=f"고른 모드 {output.get('mode')}, 기대 {_exp(expected_output).get('modes')}")


def eval_questions(*, output, **_):
    from langfuse import Evaluation
    n = output.count("?") + output.count("？")
    return Evaluation(name="one-question", value=n <= 1, data_type="BOOLEAN", comment=f"물음표 {n}개(④ 질문은 하나)")


def eval_no_repeat(*, output, expected_output, **_):
    from langfuse import Evaluation
    if not _exp(expected_output).get("must_not_end_with_question"):
        return []  # 직전 도우미 말이 질문이 아닌 항목은 판정하지 않는다
    ok = not coach.ends_with_question(output) or coach.is_proposal(output)
    return Evaluation(name="no-repeat-question", value=ok, data_type="BOOLEAN",
                      comment="③ 직전이 질문이면 이번 답은 되묻는 질문으로 끝나지 않는다('~해 볼까요?' 같은 제안은 통과, 2026-11-03 사람 라벨 기준)")


def eval_not_bare_echo(*, output, **_):
    """실험 D 에서 숫자에 안 잡힌 실패: 되묻기를 버리고 나니 '저녁만 되면 눕게 되는군요.' 한 줄만 남은 빈 맞장구."""
    from langfuse import Evaluation
    sentences = [s for s in re.findall(r"[^.!?。！？\n]+[.!?。！？]?", output) if any(ch.isalnum() for ch in s)]
    bare = len(sentences) <= 1 and not coach.ends_with_question(output)
    return Evaluation(name="not-bare-echo", value=not bare, data_type="BOOLEAN", comment=f"문장 {len(sentences)}개(한 문장뿐이고 질문·제안도 없으면 빈 맞장구)")


def eval_numbers(*, input, output, **_):
    from langfuse import Evaluation
    ok = coach.numbers_ok(output, [], coach.clean_history(input["messages"]), {}, [], coach.APP_NUMBERS)
    return Evaluation(name="no-invented-numbers", value=bool(ok), data_type="BOOLEAN", comment="사용자 말·앱 안내에 없는 숫자가 있으면 실패(서버 check-numbers 와 같은 함수)")


JUDGE_SYSTEM = """너는 루틴 도우미 앱이 '듣기(listen) 모드'로 한 답을 판정하는 평가자다.
판정할 것은 [통과 조건] 하나다. 말투, 길이, 이모지, 친절함, 질문 개수, 답이 질문으로 끝나는지는 판정하지 않는다(다른 평가자가 본다).

판정 기준
1. 루틴 방법·요령이 효과 있다고 단정하면 실패다. 예: "작은 목표를 세우면 도움이 될 수 있어요", "스트레칭은 몸에 좋아요", "음악을 들으면 시작이 쉬워져요", "이런 걸 해보면 수월할 거야".
   의견으로 권하는 말("작은 걸음부터 시작해 보는 게 좋을 것 같아요")은 효과 단정이 아니므로 통과다(2026-11-03 사람 라벨 기준).
2. 다음 한 걸음이나 선택지를 제안하는 것 자체는 통과다. 단, 사용자가 말한 일·상황 밖의 구체적인 새 방법을 꺼내면 실패다.
   예: 사용자가 운동이 안 된다고만 했는데 "명상 앱을 써 보세요"는 범위 밖이다. "운동 칸 하나만 오늘 해 볼까요?"는 범위 안이다.
   "아니면 다른 활동을 해 보실래요?"처럼 구체적인 방법 없이 열어 두는 선택지는 새 방법을 꺼낸 것이 아니므로 통과다.
3. 사용자의 말을 되받아 쓰거나 요약하는 것은 통과다. 사용자가 쓴 낱말(예: '게으르다', '의지가 약하다')을 되받았다는 이유로 실패로 보지 않는다.
4. [통과 조건]에 없는 것은 판정하지 않는다.

예시
- 사용자: "운동 루틴이 자꾸 실패해요" / 답: "작은 목표를 세워서 한 걸음씩 다가가면 도움이 될 수 있어요." / 판정: 실패(방법의 효과 주장)
- 사용자: "운동 루틴이 자꾸 실패해요" / 답: "운동 루틴이 자꾸 끊기는군요. 오늘은 운동 칸 하나만 가볍게 열어 볼까요?" / 판정: 통과(범위 안 제안, 효과 주장 없음)
- 사용자: "물 마시기를 자꾸 까먹어요" / 답: "물 마시기를 자꾸 놓치시는군요. 알림 앱을 깔면 습관이 금방 잡혀요." / 판정: 실패(범위 밖 새 방법 + 효과 주장)

반드시 JSON 한 줄로만 답한다: {"reasoning": "통과 조건을 지켰는지 사용자 말과 답을 근거로 한두 문장", "pass": true 또는 false}"""


def eval_judge(*, input, output, expected_output, **_):
    from langfuse import Evaluation
    import anthropic

    convo = "\n".join(f"{m['role']}: {m['content']}" for m in input["messages"])
    user = f"[대화]\n{convo}\n\n[도우미의 답]\n{output}\n\n[통과 조건]\n{_exp(expected_output).get('criteria_2', CRITERIA_2)}"
    client = anthropic.Anthropic(api_key=os.environ["JUDGE_API_KEY"], timeout=60)
    # 400 토큰으로는 응답이 잘렸다(stop_reason=max_tokens, 글은 몇 글자뿐). 넉넉히 주고, 잘리면 이유를 남긴다
    r = client.messages.create(model=os.environ["JUDGE_MODEL"], max_tokens=2000, system=JUDGE_SYSTEM,
                               messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        verdict = json.loads(m.group(0)) if m else {}
    except ValueError:
        verdict = {}
    if "pass" not in verdict:
        # 빈 값의 BOOLEAN 점수는 Langfuse 가 거절하므로 보내지 않는다(판정 못 한 항목은 따로 센다)
        print(f"JUDGE-UNREAD stop_reason={r.stop_reason} text={text[:120]!r}")
        return []
    return Evaluation(name="judge-no-effect-claim", value=bool(verdict["pass"]), data_type="BOOLEAN", comment=verdict.get("reasoning", ""))


# ⑤ 사람 라벨에서 새로 나온 유형(2026-11-03): 사용자는 말투가 흔들리거나 뜻을 알 수 없는 문장도 실패로 봤다
NATURAL_SYSTEM = """너는 루틴 도우미 앱의 답이 자연스러운 한국어인지 판정하는 평가자다.
판정할 것은 두 가지뿐이다. 내용이 맞는지, 효과 주장, 질문 개수, 길이, 이모지는 판정하지 않는다(다른 평가자가 본다).

판정 기준
1. 말투가 흔들리면 실패다. 한 답 안에서 존댓말과 반말이 섞이면 실패다.
   [말투 설정]이 있으면 그 설정만 본다(편한 말투=반말, 존댓말=존댓말). 사용자가 대화 중간에 설정을 바꾼 것이므로, 앞선 도우미 말과 말투가 달라도 설정을 따랐으면 통과다.
   [말투 설정]이 없으면 [대화]의 앞선 도우미 말과 같은 말투여야 한다. 앞에서 존댓말이었는데 이번 답이 반말이면(또는 그 반대) 실패다.
   (사람 라벨 기준, 2026-11-03: "반말을 쓰려면 앞의 맥락에서도 계속 반말을 썼어야 한다", 단 "설정을 바꾼 상황이면 성공으로 간주")
2. 뜻을 알 수 없는 문장이 있으면 실패다. 낱말이 빠지거나 깨진 문장("어떤 점이 거였나요?"), 앞뒤가 이어지지 않는 문장, 사용자가 한 말과 맞지 않는 엉뚱한 말이 여기에 해당한다.
3. 위 두 가지에 걸리지 않으면 통과다.

예시
- 답: "독서를 10분씩 하셨군요. 혹시 독서에 대해 어떤 점이 거였나요?" / 판정: 실패(깨진 문장)
- 답: "퇴근하면 피곤하시군요. 그럼 오늘은 짧게 해 볼래?" / 판정: 실패(존댓말에서 반말로 바뀜)
- 답: "퇴근하면 피곤하시군요. 오늘은 몸 움직이기 칸을 조금만 열어 볼까요?" / 판정: 통과

반드시 JSON 한 줄로만 답한다: {"reasoning": "말투와 문장 뜻을 근거로 한두 문장", "pass": true 또는 false}"""


def eval_judge_natural(*, input, output, **_):
    from langfuse import Evaluation
    import anthropic

    convo = "\n".join(f"{m['role']}: {m['content']}" for m in input["messages"])
    character = input.get("character") or {}
    tone = {"casual": "편한 말투(반말)", "polite": "존댓말"}.get(character.get("speech"), "없음")
    user = f"[말투 설정]\n{tone}\n\n[대화]\n{convo}\n\n[도우미의 답]\n{output}"
    client = anthropic.Anthropic(api_key=os.environ["JUDGE_API_KEY"], timeout=60)
    r = client.messages.create(model=os.environ["JUDGE_MODEL"], max_tokens=2000, system=NATURAL_SYSTEM,
                               messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        verdict = json.loads(m.group(0)) if m else {}
    except ValueError:
        verdict = {}
    if "pass" not in verdict:
        print(f"JUDGE-UNREAD stop_reason={r.stop_reason} text={text[:120]!r}")
        return []
    return Evaluation(name="judge-natural", value=bool(verdict["pass"]), data_type="BOOLEAN", comment=verdict.get("reasoning", ""))


# ⑥ 사람 라벨의 이유(2026-11-03)를 그대로 옮긴 기준: 맥락에 맞지 않는 질문·제안
RELEVANCE_SYSTEM = """너는 루틴 도우미 앱의 답에 들어 있는 질문과 제안이 대화 맥락에 맞는지 판정하는 평가자다.
이 앱의 사용자는 대개 루틴을 잘 만들지 못해서 앱을 쓴다. 효과 주장, 말투, 질문 개수, 길이는 판정하지 않는다(다른 평가자가 본다).

판정 기준(하나라도 걸리면 실패). 경계는 2026-11-03 사람 라벨과 사용자 결정에 따랐다.
1. 사용자가 이미 말한 일을 "~가 제일 걸리나요?"처럼 되묻는 질문은 항상 실패다. 다른 질문과 함께 있어도 실패다.
   예: 물 마시기를 자꾸 까먹는다는 사람에게 "물 마시기 쪽이 제일 걸리나요?", 운동 루틴이 실패한다는 사람에게 "운동 루틴이 제일 걸리시나요?" — 계속 어기면 당연히 마음에 걸린다.
2. 사용자가 말한 일과 다른 특정한 일을 짚는 질문은 실패다. 예: 아침에 일어나기가 힘들다는 사람에게 "아침 먹기 쪽이 걸리나요?"
   앱의 칸 전체를 두고 어느 칸이 걸리는지 묻는 것("도장을 안 찍은 칸 중 어떤 게 걸리나요?")은 통과다.
3. 무엇을 어떻게 하라는지 알 수 없는 막연한 제안("작은 목표부터", "작은 걸음부터")은, 사용자가 구체적인 일을 말한 경우에 실패다.
   예: 물 마시기를 까먹는 사람에게 "작은 목표를 세워 보세요"(물 마시기를 어떻게 더 작게 하나?), 일어나기가 힘든 사람에게 "작은 목표부터 시작해 보세요".
   사용자가 구체적인 일 없이 막연히 안 된다고만 한 경우("나는 원래 게으른 사람이라 뭘 해도 안 돼요")에는 통과다.
   사용자가 말한 일 안에서 구체적으로 무엇을 할지 보이는 제안("오늘은 물 한 컵만 마셔 볼까요?")은 통과다.
4. 방법·해결책을 사용자에게 되떠넘기는 질문은 실패다. 예: "어떤 걸 고려하고 계신가요?", "어떤 방법이 도움이 될 것 같으세요?" — 대부분 그걸 몰라서 앱을 쓴다.
   무엇을 하고 싶은지(어떤 루틴을 해 보고 싶은지) 묻는 질문, 사용자의 상황(언제, 무엇이 막히는지)을 묻는 질문은 통과다.
5. 구체적인 방법 없이 "아니면 다른 활동을 해 보실래요?"처럼 열어 두는 선택지는 통과다.
6. 위에 걸리지 않으면 통과다.

반드시 JSON 한 줄로만 답한다: {"reasoning": "어느 기준에 걸리거나 걸리지 않는지 사용자 말과 답을 근거로 한두 문장", "pass": true 또는 false}"""


def eval_judge_relevance(*, input, output, **_):
    from langfuse import Evaluation
    import anthropic

    convo = "\n".join(f"{m['role']}: {m['content']}" for m in input["messages"])
    user = f"[대화]\n{convo}\n\n[도우미의 답]\n{output}"
    client = anthropic.Anthropic(api_key=os.environ["JUDGE_API_KEY"], timeout=60)
    r = client.messages.create(model=os.environ["JUDGE_MODEL"], max_tokens=2000, system=RELEVANCE_SYSTEM,
                               messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        verdict = json.loads(m.group(0)) if m else {}
    except ValueError:
        verdict = {}
    if "pass" not in verdict:
        print(f"JUDGE-UNREAD stop_reason={r.stop_reason} text={text[:120]!r}")
        return []
    return Evaluation(name="judge-relevance", value=bool(verdict["pass"]), data_type="BOOLEAN", comment=verdict.get("reasoning", ""))


# --- 실행 ------------------------------------------------------------------

DATASETS = {
    "mode": ("stamp-mode", "도장판 모드 고르기: 대화 → 기대 모드(실패 유형 ①)", lambda: MODE_ITEMS, task_mode, [eval_mode]),
    "listen": ("stamp-listen-reply", "도장판 듣기 모드 답: 모드를 listen 으로 고정(실패 유형 ②③④)", listen_items, task_listen,
               [eval_judge, eval_judge_natural, eval_judge_relevance, eval_numbers, eval_no_repeat, eval_questions, eval_not_bare_echo]),
}


def upload(lf):
    for key, (name, desc, items, _, _) in DATASETS.items():
        lf.create_dataset(name=name, description=desc)
        rows = items()
        for it in rows:
            lf.create_dataset_item(dataset_name=name, id=it["id"], input=it["input"], expected_output=it["expected_output"], metadata=it["metadata"])
        print(f"{name}: 항목 {len(rows)}개 올림")


def run(lf, key, run_name):
    name, _, _, task, evaluators = DATASETS[key]
    dataset = lf.get_dataset(name)
    import prompts
    setting = {"prompt_label": prompts.label(), "reply_gate": coach.gate_on()}
    result = lf.run_experiment(name=name, run_name=run_name, data=dataset.items, task=task, evaluators=evaluators, max_concurrency=2,
                               description=f"노드 11 실험: 프롬프트 라벨 {setting['prompt_label']}, 문장 걸러 내기 {'켬' if setting['reply_gate'] else '끔'}",
                               metadata=setting)
    print("설정:", setting)
    totals = {}
    for ir in result.item_results:
        for ev in ir.evaluations:
            t = totals.setdefault(ev.name, [0, 0])
            if ev.value is not None:
                t[0] += bool(ev.value)
                t[1] += 1
    print(f"{name} / {run_name}: 항목 {len(result.item_results)}개")
    for n, (ok, all_) in totals.items():
        print(f"  {n}: {ok}/{all_} 통과")
    lf.flush()
    return result


if __name__ == "__main__":
    from langfuse import get_client

    lf = get_client()
    if sys.argv[1] == "upload":
        upload(lf)
    else:
        run(lf, sys.argv[2], sys.argv[3])
