"""지시문을 Langfuse 에서 라벨로 가져오기(prompts.py) 시험. 실제 Langfuse 에는 연결하지 않는다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prompts
import tracing


class FakePrompt:
    def __init__(self, text, is_fallback=False, version=2):
        self.text, self.is_fallback, self.version = text, is_fallback, version

    def compile(self):
        return self.text


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.asked = result, error, []

    def get_prompt(self, name, **kw):
        self.asked.append((name, kw["label"]))
        if self.error:
            raise self.error
        return self.result


def test_without_langfuse_uses_code_text(monkeypatch):
    monkeypatch.setattr(tracing, "get_client", lambda: None)
    assert prompts.get("stamp-plan", "코드 문장") == ("코드 문장", None)


def test_fetch_error_falls_back_to_code_text(monkeypatch):
    monkeypatch.setattr(tracing, "get_client", lambda: FakeClient(error=ConnectionError("down")))
    assert prompts.get("stamp-plan", "코드 문장") == ("코드 문장", None)  # 대답은 그대로 이어 간다


def test_fetched_prompt_is_returned_for_linking(monkeypatch):
    fake = FakePrompt("v2 문장")
    client = FakeClient(result=fake)
    monkeypatch.setattr(tracing, "get_client", lambda: client)
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("PROMPT_LABEL", raising=False)
    assert prompts.get("stamp-plan", "코드 문장") == ("v2 문장", fake)
    assert client.asked == [("stamp-plan", "production")]


def test_sdk_fallback_object_is_not_linked(monkeypatch):
    monkeypatch.setattr(tracing, "get_client", lambda: FakeClient(result=FakePrompt("코드 문장", is_fallback=True)))
    assert prompts.get("stamp-plan", "코드 문장") == ("코드 문장", None)


def test_label_defaults_and_override(monkeypatch):
    monkeypatch.delenv("PROMPT_LABEL", raising=False)
    monkeypatch.setenv("ENV", "development")
    assert prompts.label() == "staging"
    monkeypatch.setenv("PROMPT_LABEL", "prod-b")
    assert prompts.label() == "prod-b"
