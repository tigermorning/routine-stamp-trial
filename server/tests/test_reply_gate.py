"""대화 모드 답의 문장 걸러 내기(coach.ReplyGate) 시험. 모델 없이 조각을 직접 넣는다. 실행: server 폴더에서 python -m pytest tests"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import coach


def run(pieces, **kw):
    gate = coach.ReplyGate(coach.Limiter(coach.MAX_REPLY), **kw)
    shown = "".join(gate.feed(p) for p in pieces) + gate.finish()
    return shown, gate


def test_only_one_question_rest_continues():
    shown, _ = run(["운동이 안 되시는군요. 언제가 제일 ", "어려우세요? 아니면 어떤 게 걸리세요? 오늘 해 봐요."])
    assert shown == "운동이 안 되시는군요. 언제가 제일 어려우세요? 오늘 해 봐요."  # 두 번째 질문만 빠진다


def test_echo_question_first_does_not_end_reply():
    shown, _ = run(["아침에 일어나는 게 힘드신가요? ", "알람을 듣고도 다시 눕게 되는 날이 많군요."])
    assert shown == "아침에 일어나는 게 힘드신가요? 알람을 듣고도 다시 눕게 되는 날이 많군요."


def test_no_question_after_question():
    shown, _ = run(["저녁만 되면 눕게 되시는군요. ", "공부는 보통 언제 하세요? "], no_question=True)
    assert shown == "저녁만 되면 눕게 되시는군요."  # 뒤 공백은 걸러진 질문 문장과 함께 빠진다


def test_proposal_question_is_kept_after_question():
    shown, _ = run(["저녁만 되면 눕게 되시는군요. ", "오늘은 책상에 앉기까지만 해 볼까요? 왜 그럴까요?"], no_question=True)
    assert shown == "저녁만 되면 눕게 되시는군요. 오늘은 책상에 앉기까지만 해 볼까요?"  # 제안은 남고 되묻기는 빠진다


def test_is_proposal():
    assert coach.is_proposal("오늘은 물 한 컵만 마셔 볼까요?")
    assert coach.is_proposal("가볍게 걸어 보는 건 어때? 😊")
    assert not coach.is_proposal("언제가 제일 힘드세요?")
    assert not coach.is_proposal("물 마시기 쪽이 제일 걸리나요?")


def test_drops_sentence_with_invented_number():
    ok = lambda s: "5분" not in s
    shown, _ = run(["피곤하셨군요. 5분 걷기부터 해 보세요. ", "퇴근 뒤가 특히 힘드세요?"], number_ok=ok)
    assert shown == "피곤하셨군요. 퇴근 뒤가 특히 힘드세요?"


def test_falls_back_to_held_sentence_when_everything_dropped():
    shown, _ = run(["언제가 제일 힘드세요?"], no_question=True)
    assert shown == "언제가 제일 힘드세요?"  # 빈 답보다 걸러 둔 문장 하나가 낫다


def test_tail_without_end_mark_is_judged_at_finish():
    shown, _ = run(["오늘 많이 지치셨군요. 천천히 이야기해 주세요"])
    assert shown == "오늘 많이 지치셨군요. 천천히 이야기해 주세요"


def test_reply_filter_uses_gate_only_for_chat_modes(monkeypatch):
    monkeypatch.delenv("REPLY_GATE", raising=False)
    assert isinstance(coach.reply_filter("listen", [], [{"role": "user", "content": "안녕"}], {}, []), coach.ReplyGate)
    assert isinstance(coach.reply_filter("advise", [], [{"role": "user", "content": "안녕"}], {}, []), coach.Limiter)
    monkeypatch.setenv("REPLY_GATE", "off")
    assert isinstance(coach.reply_filter("listen", [], [{"role": "user", "content": "안녕"}], {}, []), coach.Limiter)


def test_banned_already_said_question_is_removed():
    shown, _ = run(["물 마시기 칸을 만드셨군요! ", "혹시 요즘은 물 마시기 쪽이 제일 걸리나요? ", "오늘은 물 한 컵만 마셔 볼까요?"])
    assert shown == "물 마시기 칸을 만드셨군요! 오늘은 물 한 컵만 마셔 볼까요?"  # 지운 문장 다음 질문이 첫 질문이 된다


def test_banned_sentence_is_not_the_fallback():
    shown, _ = run(["운동 루틴이 제일 걸리시나요?"])
    assert "걸리" not in shown
