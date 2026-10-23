"""POST /api/chat 시험. 실행: server 폴더에서 python -m pytest tests  (키 없이 가짜 LLM 으로 돈다)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import cards as cardlib
import coach
import main
from llm import FakeLLM


class Scripted(FakeLLM):
    """계획은 정해 둔 값, 답은 정해 둔 조각을 내보낸다. 호출 기록을 남긴다."""

    def __init__(self, plan, pieces=("...",), exc=None):
        super().__init__(delay=0)
        self.plan, self.pieces, self.exc, self.plan_calls, self.stream_calls = plan, pieces, exc, 0, []

    def complete_json(self, system, user):
        self.plan_calls += 1
        if isinstance(self.plan, Exception):
            raise self.plan
        return self.plan

    def chat_stream(self, messages):
        self.stream_calls.append(messages)
        yield from self.pieces
        if self.exc:
            raise self.exc


@pytest.fixture(autouse=True)
def fresh():
    main._hits.clear()
    yield
    main.app.dependency_overrides.clear()


def use(llm):
    main.app.dependency_overrides[main.get_llm] = lambda: llm
    return TestClient(main.app)


def post(client, text, **extra):
    body = {"messages": [{"role": "user", "content": text}], **extra}
    r = client.post("/api/chat", json=body)
    return r, [json.loads(x) for x in r.text.splitlines() if x]


def types(ev):
    return [e["type"] for e in ev]


def joined(ev):
    return "".join(e["text"] for e in ev if e["type"] == "delta")


def fake():
    return use(FakeLLM(delay=0))


# ---- 카드 파일 ----
def test_cards_file_valid_and_numbers_only_when_fully_checked():
    cs = cardlib.load_cards()
    assert len(cs) >= 8
    for c in cs.values():
        assert c["level"] == "full" or c["numbers"] == []
        assert all(s["doi"].startswith("10.") for s in c["sources"])


def test_card_loader_rejects_numbers_on_abstract_only_card(tmp_path):
    bad = {"cards": [{"id": "x", "topics": ["a"], "summary": "s", "can_say": ["c"], "limits": "l", "numbers": ["73"],
                      "level": "abstract", "sources": [{"short": "A 2020", "title": "t", "doi": "10.1/x", "checked": "abstract"}]}]}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(AssertionError):
        cardlib.load_cards(p)


def test_pick_keeps_only_real_unique_cards_max_two():
    got = cardlib.pick(["missed-one-day", "nope", "missed-one-day", "takes-time", "if-then"])
    assert [c["id"] for c in got] == ["missed-one-day", "takes-time"]
    assert cardlib.pick("not-a-list") == [] and cardlib.pick(None) == []


# ---- 듣기·정리 ----
def test_listen_streams_and_done_ok():
    r, ev = post(fake(), "요즘 계속 실패해요")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    assert types(ev)[0] == "mode" and ev[0]["mode"] == "listen"
    assert types(ev).count("delta") > 1 and ev[-1] == {"type": "done", "ok": True, "mode": "listen", "basis": "none", "cards": []}


def test_organize_is_gone_todos_are_accepted_but_handled_as_listen():
    # 2026-10-21 사용자 결정: '내 할 일' 목록을 화면에서 없앴다. 모델이 organize 를 골라도(또는 이전 화면이 todos 를 보내도) listen 으로 처리한다
    _, ev = post(fake(), "fake:organize 정리해 줘")
    assert ev[0]["mode"] == "listen"
    r, ev = post(fake(), "fake:organize 정리해 줘", todos=["운동", "책"])
    assert r.status_code == 200 and ev[0]["mode"] == "listen" and ev[-1]["type"] == "done"
    assert "organize" not in __import__("policy").MODES


# ---- 조언·퀘스트(근거 카드) ----
def test_advise_uses_only_existing_cards_and_reports_sources():
    _, ev = post(fake(), "fake:advise 하루 빠졌어요")
    done = ev[-1]
    assert done["type"] == "done" and done["ok"] and done["mode"] == "advise"
    assert [c["id"] for c in done["cards"]] == ["missed-one-day"]  # 없는 id·중복은 버려짐
    assert done["cards"][0]["level"] == "abstract" and done["cards"][0]["sources"][0]["doi"] == "10.1002/ejsp.674"


def test_advise_with_only_unknown_cards_falls_back_to_listen_with_notice():
    llm = Scripted({"mode": "advise", "card_ids": ["no-such-card"]}, ["그랬군요. 더 얘기해 줄래요?"])
    _, ev = post(use(llm), "방법 알려 줘")
    assert types(ev)[0] == "notice" and ev[0]["key"] == "noEvidence"
    assert ev[1] == {"type": "mode", "mode": "listen"} and ev[-1]["cards"] == []
    assert "[카드 " not in llm.stream_calls[0][0]["content"]  # 카드 없이 방법을 말하게 두지 않는다


def test_only_selected_card_text_goes_into_prompt():
    llm = Scripted({"mode": "advise", "card_ids": ["takes-time"]}, ["두 달쯤 걸려요."])
    post(use(llm), "왜 안 될까요")
    system = llm.stream_calls[0][0]["content"]
    assert "[카드 takes-time]" in system and "[카드 missed-one-day]" not in system
    assert "카드에 없는 방법" in system  # 카드 밖 금지 규칙


def test_made_up_number_is_flagged_not_ok():
    _, ev = post(fake(), "fake:badnum 효과 있어요?")
    assert ev[-1]["type"] == "done" and ev[-1]["ok"] is False


@pytest.mark.parametrize("reply,ok", [
    ("5분만 해 보세요.", False),                   # 지어낸 행동 크기도 막는다(2026-10-21 첫 진짜 시험에서 "10분간", "1회"가 나옴)
    ("한 번만 해 보세요.", True),
    ("연구에서는 59일에서 66일이라고 했어요.", True),   # 원문 확인 카드의 수치
    ("연구에서는 73%가 좋아졌어요.", False),
    ("21일이면 습관이 돼요.", False),
])
def test_numbers_check(reply, ok):
    card = cardlib.CARDS["takes-time"]
    assert coach.numbers_ok(reply, [card], [{"role": "user", "content": "왜 안 돼요"}], None, []) is ok


def test_abstract_only_card_gives_no_allowed_numbers():
    card = cardlib.CARDS["missed-one-day"]
    assert coach.numbers_ok("96명을 봤어요.", [card], [{"role": "user", "content": "x"}], None, []) is False


def test_quest_is_single_line_with_card_meta():
    _, ev = post(fake(), "fake:quest 오늘 뭐 하죠", context={"slots": ["스트레칭"], "days": 4})
    done = ev[-1]
    assert done["mode"] == "quest" and done["ok"] and [c["id"] for c in done["cards"]] == ["if-then"]
    assert "\n" not in joined(ev) and joined(ev).startswith("만약")


def test_quest_cut_to_one_line():
    llm = Scripted({"mode": "quest", "card_ids": ["if-then"]}, ["만약 밥을 먹으면, ", "물을 마신다.\n그리고 또 긴 계획", " 추가"])
    _, ev = post(use(llm), "오늘 뭐 하죠")
    assert joined(ev) == "만약 밥을 먹으면, 물을 마신다." and ev[-1]["ok"]


# ---- 범위 밖·위기 ----
def test_out_of_scope_gets_fixed_scope_event_without_streaming():
    llm = Scripted({"mode": "out_of_scope", "card_ids": []})
    _, ev = post(use(llm), "우울증 약 먹어도 되나요")
    assert types(ev) == ["scope"] and llm.stream_calls == []


def test_model_flagged_crisis_gives_crisis_event():
    _, ev = post(fake(), "fake:modelcrisis")
    assert types(ev) == ["crisis"]


def test_crisis_keywords_never_reach_the_llm():
    llm = Scripted({"mode": "listen", "card_ids": []})
    client = use(llm)
    for text in ["죽고 싶어요", "I want to die", "我想自杀", "quiero morir", "haluan kuolla"]:
        _, ev = post(client, text)
        assert types(ev) == ["crisis"], text
    assert llm.plan_calls == 0 and llm.stream_calls == []


# ---- 실패·입력 ----
def test_plan_failure_falls_back_to_listen():
    llm = Scripted(RuntimeError("x"), ["그랬군요."])
    _, ev = post(use(llm), "힘들어요")
    assert ev[0]["mode"] == "listen" and ev[-1]["ok"]


def test_garbage_plan_is_treated_as_listen():
    _, ev = post(fake(), "fake:badjson")
    assert ev[0]["mode"] == "listen" and ev[-1]["type"] == "done"


def test_stream_error_gives_error_event_not_done():
    _, ev = post(fake(), "fake:error 방법 알려 줘")
    assert ev[-1] == {"type": "error"} and not any(e["type"] == "done" for e in ev)


def test_empty_or_assistant_last_rejected():
    c = fake()
    assert c.post("/api/chat", json={"messages": []}).status_code == 400
    assert c.post("/api/chat", json={"messages": [{"role": "assistant", "content": "안녕"}]}).status_code == 400
    assert c.post("/api/chat", json={}).status_code == 400


def test_history_limits_and_context_are_cleaned():
    llm = Scripted({"mode": "listen", "card_ids": []}, ["네."])
    msgs = []
    for i in range(30):
        msgs += [{"role": "user", "content": f"u{i} " + "가" * 900}, {"role": "assistant", "content": f"a{i}"}]
    msgs.append({"role": "user", "content": "마지막"})
    r = use(llm).post("/api/chat", json={"messages": msgs, "context": {"slots": ["달리기"] * 9, "days": "x", "도장기록": {"2026-10-01": 1}},
                                          "todos": ["가" * 200] * 40})
    assert r.status_code == 200
    sent = llm.stream_calls[0]
    assert len(sent) - 1 <= coach.MAX_TURNS and sent[1]["role"] == "user" and sent[-1]["content"] == "마지막"
    assert all(len(m["content"]) <= coach.MAX_MSG for m in sent[1:])
    system = sent[0]["content"]
    assert "도장이 쌓인 일수: 0" in system and "2026-10-01" not in system and system.count("- 가") == coach.MAX_TODOS


def test_context_absent_means_no_slot_info_in_prompt():
    llm = Scripted({"mode": "listen", "card_ids": []}, ["네."])
    post(use(llm), "안녕", context=None, todos=[])
    assert "[이 앱에 저장된 내 칸(칸 이름" not in llm.stream_calls[0][0]["content"]  # 칸 정보 블록은 context 가 있을 때만(규칙 안의 짧은 이름 언급은 별개)


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_PER_IP", 2)
    c = fake()
    assert post(c, "a")[0].status_code == 200 and post(c, "b")[0].status_code == 200
    assert post(c, "c")[0].status_code == 429


def test_conversation_not_logged(caplog):
    with caplog.at_level("DEBUG"):
        post(fake(), "비밀스러운문장 fake:error 방법")
        post(fake(), "비밀스러운문장")
    assert "비밀스러운문장" not in caplog.text


def test_page_and_health():
    c = fake()
    assert c.get("/health").json() == {"status": "ok"}
    assert "루틴 도장" in c.get("/").text


# ---- 퀘스트에 모델이 지어내기 어려운 구조: 한 줄 상한 ----
def test_limiter_trims_decoration_and_caps_length():
    lim = coach.Limiter(10, one_line=True)
    out = lim.feed('"스트레칭') + lim.feed(" 1분 하고 나서 더 길게\n다음")
    assert out == "스트레칭 1분 하고 나" or len(lim.out) == 10
    assert lim.done


def test_hour_adds_time_note_and_is_validated():
    llm = Scripted({"mode": "listen", "card_ids": []}, ["네."])
    post(use(llm), "안녕", context={"slots": ["아침 먹기"], "days": 2, "hour": 16}, todos=[])
    system = llm.stream_calls[0][0]["content"]
    assert "[지금 시각(사용자 기기 기준)] 오후 4시쯤" in system
    assert "이미 지난 시간대의 활동" in system and "포기하지 않게" in system
    for bad in (24, -1, "16", True, None):  # 범위 밖·문자열·불리언은 버린다
        llm2 = Scripted({"mode": "listen", "card_ids": []}, ["네."])
        post(use(llm2), "안녕", context={"slots": ["아침 먹기"], "days": 2, "hour": bad}, todos=[])
        assert "[지금 시각" not in llm2.stream_calls[0][0]["content"]


def test_hour_bands_and_numbers_allow_current_hour():
    assert [coach.hour_band(h) for h in (3, 8, 12, 16, 20, 23)] == ["새벽", "아침", "점심때", "오후", "저녁", "밤"]
    ctx = {"slots": ["달리기"], "days": 1, "hour": 16}
    assert coach.numbers_ok("지금 4시쯤이니 가볍게 걸어 봐요.", [], [], ctx, [])
    assert not coach.numbers_ok("지금 5시쯤이니 가볍게 걸어 봐요.", [], [], ctx, [])
