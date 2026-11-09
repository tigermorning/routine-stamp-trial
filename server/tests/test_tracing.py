"""Langfuse 계측 시험. 실제 Langfuse 에는 아무것도 보내지 않고, 호출을 기록하는 가짜 클라이언트를 끼운다. 실행: server 폴더에서 python -m pytest tests"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import main
import tracing
from llm import FakeLLM


class FakeObs:
    def __init__(self, rec, name, as_type, kw):
        self.rec, self.name, self.as_type, self.kw, self.updates, self.ended = rec, name, as_type, kw, [], False
        rec.append(self)

    def start_observation(self, name, as_type="span", **kw):
        return FakeObs(self.rec, name, as_type, kw)

    def update(self, **kw):
        self.updates.append(kw)

    def end(self):
        self.ended = True


class FakeClient:
    def __init__(self):
        self.rec, self.flushed = [], 0

    def start_observation(self, name, as_type="span", **kw):
        return FakeObs(self.rec, name, as_type, kw)

    def flush(self):
        self.flushed += 1


@pytest.fixture(autouse=True)
def fresh():
    main._hits.clear()
    yield
    main.app.dependency_overrides.clear()


def use_tracing(monkeypatch, client):
    monkeypatch.setattr(tracing, "get_client", lambda: client)


def chat(text):
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM(delay=0)
    r = TestClient(main.app).post("/api/chat", json={"messages": [{"role": "user", "content": text}]})
    return [json.loads(x) for x in r.text.splitlines() if x]


def everything(client):
    """기록된 모든 관찰 단위의 입력·출력·메타데이터를 한 글자열로(원문이 샜는지 찾는 용)."""
    out = []
    for o in client.rec:
        out.append(json.dumps([o.kw, o.updates], ensure_ascii=False, default=str))
    return "\n".join(out)


def test_off_without_keys(monkeypatch):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(tracing, "_tried", False)
    monkeypatch.setattr(tracing, "_client", None)
    assert tracing.get_client() is None
    assert [e["type"] for e in chat("안녕")][-1] == "done"  # 꺼져 있어도 대화는 그대로


def test_normal_turn_steps(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    ev = chat("어제 하루 빠졌어 fake:advise")
    assert [e["type"] for e in ev][-1] == "done"
    names = [(o.name, o.as_type) for o in c.rec]
    assert names == [("chat-turn", "agent"), ("check-safety", "guardrail"), ("choose-mode", "generation"), ("generate-reply", "generation"), ("check-numbers", "guardrail")]
    assert all(o.ended for o in c.rec)
    assert c.flushed == 1
    plan = c.rec[2].updates[-1]["metadata"]
    assert plan["mode"] == "advise" and plan["card_ids"] == ["missed-one-day"] and plan["asked_cards"] == 3
    reply = next(o for o in c.rec if o.name == "generate-reply")
    assert any("completion_start_time" in u for u in reply.updates)  # 첫 글자 시각


def test_no_raw_text_by_default(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    monkeypatch.setattr(tracing, "CAPTURE_TEXT", False)
    chat("내 전화번호는 010-1234-5678 이고 fake:advise")
    dump = everything(c)
    assert "010" not in dump and "전화번호" not in dump
    assert "하루 빠진 것만으로" not in dump  # 답 본문도 남기지 않는다


def test_crisis_stops_before_model(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    ev = chat("죽고 싶다")
    assert [e["type"] for e in ev] == ["crisis"]
    assert [o.name for o in c.rec] == ["chat-turn", "check-safety"]  # 모델을 부르는 단계가 없다
    assert c.rec[0].ended and c.flushed == 1


def test_tracing_failure_does_not_break_chat(monkeypatch):
    class Broken(FakeClient):
        def start_observation(self, *a, **k):
            raise RuntimeError("boom")

        def flush(self):
            raise RuntimeError("boom")

    use_tracing(monkeypatch, Broken())
    assert [e["type"] for e in chat("안녕")][-1] == "done"


def test_stream_error_marks_error_level(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    ev = chat("fake:error")
    assert ev[-1]["type"] == "error"
    reply = next(o for o in c.rec if o.name == "generate-reply")
    assert any(u.get("level") == "ERROR" and u.get("status_message") == "RuntimeError" for u in reply.updates)
    assert "fake stream error" not in everything(c)  # 오류 문구는 남기지 않고 종류만


def test_plan_failure_marked_once_and_keeps_fallback_mode(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    ev = chat("fake:planerror")
    assert ev[-1]["type"] == "done"  # 계획이 실패해도 듣기 모드로 답한다
    plan = next(o for o in c.rec if o.name == "choose-mode")
    assert plan.ended
    assert any(u.get("level") == "ERROR" for u in plan.updates)
    assert plan.updates[-1]["metadata"]["mode"] == "listen"  # 오류 표시 뒤에 고른 모드를 덧붙여 한 번만 닫았다


class UsageLLM(FakeLLM):
    """진짜 제공사처럼 넘겨받은 dict 에 토큰 수를 채우는 가짜."""

    def complete_json(self, system, user, usage=None):
        usage.update(input=11, output=7)
        return super().complete_json(system, user)

    def chat_stream(self, messages, usage=None):
        yield from super().chat_stream(messages)
        usage.update(input=120, output=40)


def test_usage_details_on_generations(monkeypatch):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    main.app.dependency_overrides[main.get_llm] = lambda: UsageLLM(delay=0)
    TestClient(main.app).post("/api/chat", json={"messages": [{"role": "user", "content": "어제 하루 빠졌어 fake:advise"}]})
    used = {o.name: next((u["usage_details"] for u in o.updates if u.get("usage_details")), None) for o in c.rec}
    assert used["choose-mode"] == {"input": 11, "output": 7}
    assert used["generate-reply"] == {"input": 120, "output": 40}


def test_usage_kw_only_when_accepted():
    box = {}
    assert tracing.usage_kw(lambda system, user: None, box) == {}  # usage 인자가 없는 옛 가짜 LLM
    assert tracing.usage_kw(lambda system, user, usage=None: None, box) == {"usage": box}
    assert tracing.usage_kw(lambda *a, **k: None, box) == {"usage": box}  # 평가 실행기의 호출 수 세기 감싸개


def test_mask_patterns():
    s = tracing.mask(data={"a": ["연락 010-1234-5678 / a.b@x.co.kr / 4111 1111 1111 1111"]})["a"][0]
    assert "5678" not in s and "x.co.kr" not in s and "4111" not in s
    assert "[전화번호]" in s and "[이메일]" in s and "[카드번호]" in s


def test_flush_logs_duration_and_trace_id_without_text(monkeypatch, caplog):
    c = FakeClient()
    use_tracing(monkeypatch, c)
    with caplog.at_level("INFO", logger="coach"):
        chat("어제 하루 빠졌어 fake:advise")
    line = next(r.getMessage() for r in caplog.records if r.getMessage().startswith("tracing flush"))
    assert "trace=" in line and "ms=" in line and "빠졌" not in line
