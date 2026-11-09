"""의견 보내기(/api/feedback): 보내는 글·제한·오류·메일 구성(실제로 보내지 않는다)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import feedback
import main


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    main._hits.clear()
    monkeypatch.setenv("FEEDBACK_SMTP_USER", "me@example.com")
    monkeypatch.setenv("FEEDBACK_SMTP_PASSWORD", "secret-pw")
    monkeypatch.delenv("FEEDBACK_TO", raising=False)
    yield
    main._hits.clear()


def test_sends_text_and_stats(monkeypatch):
    sent = []
    monkeypatch.setattr(feedback, "send", lambda text, stats="": sent.append((text, stats)))
    r = TestClient(main.app).post("/api/feedback", json={"text": "  좋아요  ", "stats": "[auto] stamps=3"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert sent == [("좋아요", "[auto] stamps=3")]


def test_empty_is_400_and_not_sent(monkeypatch):
    monkeypatch.setattr(feedback, "send", lambda *a, **k: pytest.fail("보내면 안 된다"))
    r = TestClient(main.app).post("/api/feedback", json={"text": "  \n ", "stats": "x"})
    assert r.status_code == 400 and r.json() == {"error": "empty"}


def test_not_configured_is_503(monkeypatch):
    monkeypatch.delenv("FEEDBACK_SMTP_PASSWORD")
    r = TestClient(main.app).post("/api/feedback", json={"text": "안녕"})
    assert r.status_code == 503 and r.json() == {"error": "notConfigured"}


def test_send_failure_is_502_and_logs_only_the_error_kind(monkeypatch, caplog):
    def boom(text, stats=""):
        raise RuntimeError("비밀 의견 본문 secret-pw")
    monkeypatch.setattr(feedback, "send", boom)
    with caplog.at_level("INFO"):
        r = TestClient(main.app).post("/api/feedback", json={"text": "비밀 의견 본문"})
    assert r.status_code == 502 and r.json() == {"error": "failed"}
    assert "RuntimeError" in caplog.text and "비밀 의견 본문" not in caplog.text and "secret-pw" not in caplog.text


def test_per_ip_limit(monkeypatch):
    monkeypatch.setattr(feedback, "send", lambda *a, **k: None)
    c = TestClient(main.app)
    codes = [c.post("/api/feedback", json={"text": "a"}).status_code for _ in range(main.RATE_FEEDBACK_PER_IP + 1)]
    assert codes[:-1] == [200] * main.RATE_FEEDBACK_PER_IP and codes[-1] == 429


def test_message_is_built_without_user_text_in_headers(monkeypatch):
    monkeypatch.setenv("FEEDBACK_TO", "dev@example.com")
    m = feedback.build_message("제목 줄\nBcc: x@evil.com\n본문", "[auto] a=1")
    assert m["To"] == "dev@example.com" and m["From"] == "me@example.com" and m["Bcc"] is None
    assert "Bcc: x@evil.com" in m.get_content() and m.get_content().rstrip().endswith("[auto] a=1")


def test_clean_limits_and_strips_control_chars():
    assert feedback.clean("a\x00b\x07c\n d", 100) == "abc\n d"
    assert len(feedback.clean("가" * 5000, feedback.MAX_TEXT)) == feedback.MAX_TEXT
