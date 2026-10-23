"""도우미(루틴 코치 친구)의 규칙. 모델 판단과 상관없이 코드로 지키는 것: 입력 길이, 위기 키워드, 카드 id 검사, 숫자 검사.

대화 내용은 저장하지도 로그에 남기지도 않는다(이 모듈은 로그를 쓰지 않는다).
"""
import re

import cards as cardlib

from policy import *  # noqa: F401,F403  범위·페르소나·안전 규칙·한도는 policy.py 한 곳에 있다


def is_crisis(text):
    low = text.lower()
    return any(k in low for k in CRISIS_KEYWORDS)


def plan_messages(history, todos_n=0):  # todos_n: 이전 버전 화면과의 호환용 인자. 이제 분류에는 쓰지 않는다(할 일 목록이 없어졌다)
    convo = "\n".join(f"{'사용자' if m['role'] == 'user' else '도우미'}: {m['content']}" for m in history)
    return PLAN_SYSTEM, f"[카드 목록]\n{cardlib.catalogue()}\n\n[대화]\n{convo}"


def clean_history(raw):
    """화면에서 받은 대화를 정리한다. 마지막은 반드시 사용자 말이어야 한다. 아니면 None."""
    out = []
    for m in raw or []:
        role = m.get("role")
        text = " ".join(str(m.get("content") or "").split())[:MAX_MSG]
        if role in ("user", "assistant") and text:
            out.append({"role": role, "content": text})
    merged = []
    for m in out:  # 같은 쪽 말이 이어지면 하나로 합친다(일부 제공사는 번갈아 오는 대화만 받는다)
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = (merged[-1]["content"] + "\n" + m["content"])[:MAX_MSG]
        else:
            merged.append(dict(m))
    out = merged[-MAX_TURNS:]
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out if out and out[-1]["role"] == "user" else None


def clean_context(ctx):
    """사용자가 보여 주기로 한 칸 이름·일수·오늘 칸 상태(0 아직 안 찍음, 1 진하게, 2 연하게). 없으면 None."""
    if not isinstance(ctx, dict):
        return None
    raw_today = ctx.get("today") if isinstance(ctx.get("today"), list) else []
    raw_until = ctx.get("until") if isinstance(ctx.get("until"), list) else []
    pairs, untils = [], []
    for i, s in enumerate((ctx.get("slots") or [])[:MAX_SLOTS]):
        name = " ".join(str(s).split())[:30]
        if not name:
            continue
        v = raw_today[i] if i < len(raw_today) else None
        pairs.append((name, v if v in (0, 1, 2) and not isinstance(v, bool) else None))
        u = raw_until[i] if i < len(raw_until) else None
        untils.append(u if isinstance(u, int) and not isinstance(u, bool) and 1 <= u <= 24 else None)
    try:
        days = max(0, min(int(ctx.get("days", 0)), 100000))
    except (TypeError, ValueError):
        days = 0
    if not pairs:
        return None
    out = {"slots": [n for n, _ in pairs], "days": days}
    if all(v is not None for _, v in pairs):  # 오늘 상태는 모든 칸이 제대로 왔을 때만 쓴다
        out["today"] = [v for _, v in pairs]
    hour = ctx.get("hour")
    if isinstance(hour, int) and not isinstance(hour, bool) and 0 <= hour <= 23:  # 사용자 기기의 현재 시(0~23)만 받는다. 날짜·분은 받지 않는다
        out["hour"] = hour
        # 칸마다 '몇 시까지 할 수 있는 칸인지'(until)를 앱이 보내 준다. 지금 시각이 그 시각 이상이면 시간이 지난 칸이다
        closed = [n for (n, _), u in zip(pairs, untils) if u is not None and hour >= u]
        if closed:
            out["closed"] = closed
    return out


def hour_band(hour):
    return "새벽" if hour < 5 else "아침" if hour < 11 else "점심때" if hour < 14 else "오후" if hour < 18 else "저녁" if hour < 22 else "밤"


def time_note(hour):
    """지금 시각에 이미 지난 활동을 권하지 않고, 못 한 칸 때문에 오늘을 통째로 포기하지 않게 북돋우는 규칙."""
    return (f"[지금 시각(사용자 기기 기준)] {hour_band(hour)} {hour % 12 or 12}시쯤. "
            "권하는 한 걸음은 이 시각에 아직 할 수 있는 것이어야 한다. 이미 지난 시간대의 활동(예: 오후나 저녁에 아침 먹기, 밤에 아침 운동)은 권하지 않는다. "
            "권할 때는 사용자의 칸 중 지금 시간대에 어울리는 것을 고르거나, 지금부터 할 수 있는 가장 가벼운 한 걸음을 고른다. "
            "시간이 지나 못 하게 된 칸이 있어도 놓쳤다고 말하거나 탓하지 않는다. '그 칸은 내일 다시 하면 돼요, 오늘은 지금부터 가능한 걸 해 봐도 좋아요'처럼 "
            "의욕을 북돋워 오늘 전체를 포기하지 않게 돕는다. 사용자가 시각 때문에 못 한다고 말하면 그 말을 받아 주고 곧바로 지금 가능한 쪽으로 넘어간다.")


def closed_note(closed):
    """앱이 알려 준, 지금 시각이 이미 지난 칸. 권하지 않고, 오늘 전체를 포기하지 않도록 격려하는 말을 쓰게 한다."""
    return ("[오늘 이미 시간이 지난 칸(이 앱이 시각으로 판단한 사실)] " + ", ".join(closed) + "\n"
            "이 칸들은 오늘은 권하지 않고 '해 보세요'라고도 말하지 않는다. 사용자가 이 칸을 못 했다고 하면 이렇게 답한다: "
            "① 먼저 그 마음을 받아 준다(예: '그 시간은 지나갔네요'). ② 오늘 하루가 끝난 게 아니라고 말한다(예: '그래도 오늘은 아직 남았어요'). "
            "③ 그 칸은 내일 다시 하면 된다고 말한다. ④ 지금 시각에 아직 할 수 있는 칸(시간이 지난 칸을 뺀 나머지) 중 하나를 가볍게 권하고 "
            "'한 번만 눌러 봐도 충분해요' 같은 부담 없는 말로 마무리한다. 남은 칸이 하나도 없으면 오늘 온 것만으로도 충분하다고 말한다. "
            "비교하거나 탓하는 말('못 했네요', '놓쳤네요')은 쓰지 않는다.")


CLOSED_RETRY = ("[다시 쓰기] 방금 답은 오늘 시간이 지난 칸을 지금 해 보라는 뜻으로 읽힌다. 그 칸 이름은 '내일'과 함께만 말하거나 아예 말하지 않는다. "
                "지금 할 수 있는 칸 하나만 가볍게 권한다.")


def recommends_closed(reply, closed):
    """시간이 지난 칸의 이름이 '내일' 없이 한 문장에 들어 있으면 그 칸을 지금 권하는 것으로 본다(근사 검사: 칸 이름을 다르게 바꿔 말하면 못 거른다)."""
    for sentence in re.split(r"[.!?\n…]+", reply):
        if any(name in sentence for name in closed) and "내일" not in sentence:
            return True
    return False


def closed_fallback(ctx):
    """다시 써도 지난 칸을 권하면 쓰는 고정 답. 지난 칸을 이름으로 말하지 않고, 오늘을 포기하지 않게 하며, 요청을 살피는 말로 끝낸다."""
    left = [n for n in ctx["slots"] if n not in ctx.get("closed", [])]
    step = f"지금은 '{left[0]}'부터 한 번만 가볍게 눌러 볼까요? 한 번이면 충분해요." if left else "오늘은 와 주신 것만으로도 충분해요."
    return f"그 시간은 지나갔지만 괜찮아요. 오늘은 아직 남았고, 놓친 건 내일 다시 하면 돼요 🙂 {step} 필요한 게 있으면 편하게 말씀해 주세요."


TODAY_TEXT = {0: "아직 도장을 안 찍음", 1: "진한 도장(다 했어요)", 2: "연한 도장(조금 했어요)"}


def clean_todos(raw):
    return [" ".join(str(t).split())[:MAX_TODO_LEN] for t in (raw or [])[:MAX_TODOS] if str(t).strip()]


_NAME_STRIP = re.compile(r"[\"'`<>{}\[\]\\\r\n\t]")


def clean_character(raw):
    """화면에서 받은 캐릭터 설정을 허용값으로 정리한다. 필드가 없거나 객체가 아니면 None(= 설정 없음, 기본 동작).
    허용 목록 밖의 값은 기본값으로 바꾸고, 이름은 괄호·따옴표·줄바꿈을 걷어 내고 20자로 자른다."""
    if not isinstance(raw, dict):
        return None
    d = CHARACTER_DEFAULTS
    speech = raw.get("speech") if raw.get("speech") in SPEECH_CHOICES else d["speech"]
    emoji = raw.get("emoji") if raw.get("emoji") in EMOJI_CHOICES else d["emoji"]
    name = " ".join(_NAME_STRIP.sub(" ", str(raw.get("name") or "")).split())[:MAX_NAME]
    return {"name": name, "speech": speech, "emoji": emoji}


def ends_with_question(text):
    return text.strip().rstrip(" 😊🌟✨🙂😄😉👍💪🏃‍♂️🎉").endswith(("?", "？"))


def variation_hint(history):
    """직전 도우미 말이 질문으로 끝났으면 이번에는 질문으로 끝내지 않게 한다(같은 형태 되풀이 방지).
    모델의 판단에 맡기지 않고 서버가 직전 말을 보고 정한다."""
    assistants = [m["content"] for m in (history or []) if m["role"] == "assistant"]
    if not assistants or not ends_with_question(assistants[-1]):
        return ""
    twice = len(assistants) >= 2 and ends_with_question(assistants[-2])
    return ("[이번 답의 형태] 직전 도우미 말이 질문으로 끝났다" + ("(그 전 말도 질문이었다)" if twice else "")
            + ". 이번 답은 질문으로 끝내지 않는다. 사용자가 방금 한 말을 되받아 요약하거나, 선택지 두 개를 주거나, 사용자가 말한 범위 안에서 다음 한 걸음을 제안하며 마무리한다.")


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐❤]")
POLITE_END = re.compile(r"(요|니다|니까|세요|죠|네요|군요)$")
_SENT = re.compile(r"[^.!?。！？\n]+[.!?。！？]?")
_HANGUL = re.compile("[가-힣]")


def polite_ratio(text):
    """한국어 문장 중 존댓말로 끝나는 문장의 비율(휴리스틱). 한글 문장이 없으면 None."""
    ends = []
    for s in _SENT.findall(text):
        if not any(ch.isalpha() for ch in s):
            continue
        s = EMOJI.sub("", s).strip().rstrip(".!?。！？~ ")
        if s and _HANGUL.search(s):
            ends.append(bool(POLITE_END.search(s)))
    return sum(ends) / len(ends) if ends else None


OMITTED = "(앞선 도우미 말은 말투 설정이 달라 생략했어요.)"


def neutralize_history(history, character):
    """말투 설정을 바꾼 직후에는 앞선 도우미 말이 옛 말투라, 모델이 그걸 따라 한다(2026-10-21 실측: 존댓말 설정이 반말로 답하는 일 3/3).
    한국어 도우미 말 중 지금 설정과 말투가 어긋난 것은 내용 대신 생략 표시로 바꿔 모델에 보낸다(화면·저장 기록은 그대로).
    캐릭터 설정이 없거나 한글이 아닌 말은 건드리지 않는다."""
    if not character or not history:
        return history
    out = []
    for m in history:
        if m["role"] == "assistant":
            r = polite_ratio(m["content"])
            if r is not None and ((character["speech"] == "casual" and r > 0.6) or (character["speech"] == "polite" and r < 0.4)):
                m = {"role": "assistant", "content": OMITTED}
        out.append(m)
    return out


def with_tone_reminder(history, character, extra=""):
    """모델에 보내는 대화의 마지막 사용자 말 뒤에 말투 한 줄(과 extra 한 줄)을 붙인 사본을 돌려준다(원본·화면·저장 기록은 그대로).
    앞선 도우미 말투를 모델이 따라 하는 것을 막고(2026-10-21 실측 2/6 → 6/6), 시스템 지시보다 센 '마지막 말 뒤' 자리에 형태 힌트도 둔다.
    캐릭터 설정도 extra 도 없으면 그대로 돌려준다."""
    notes = ([TONE_REMINDER[character["speech"]]] if character else []) + ([extra] if extra else [])
    if not notes or not history or history[-1]["role"] != "user":
        return history
    out = [dict(m) for m in history]
    out[-1]["content"] = out[-1]["content"] + "\n\n" + "\n".join(notes)
    return out


APP_NUMBERS = set(re.findall(r"\d+(?:[.,]\d+)?", APP_GUIDE))  # 앱 안내에 나오는 숫자(3·28·60·6·10 …). 앱 이야기에서만 말해도 된다


def build_system(mode, cards, ctx, todos, character=None, history=None):
    """규칙(안전·범위·카드·위기)은 캐릭터 설정보다 앞에 있고, 설정으로 바뀌지 않는다. 설정은 말투 줄과 이름 칸만 바꾼다."""
    parts = [fixed_rules(tone_for(character), with_character=bool(character))]
    if name_block(character):
        parts.append(name_block(character))
    parts.append(MODE_RULES[mode])
    if mode in ("advise", "quest") and cards:
        parts.append("[근거 카드]\n" + cardlib.card_block(cards))
    parts.append(APP_GUIDE)
    if mode in CHAT_MODES and variation_hint(history):
        parts.append(variation_hint(history))
    info = []
    if ctx:
        info.append(f"[이 앱에 저장된 내 칸(칸 이름과 도장이 쌓인 일수)] 칸: {', '.join(ctx['slots'])} / 도장이 쌓인 일수: {ctx['days']}")
        if ctx.get("today"):
            info.append("[오늘 내 칸 상태(이 앱에서 읽은 사실)] " + " / ".join(f"{n}: {TODAY_TEXT[v]}" for n, v in zip(ctx["slots"], ctx["today"])))
        if ctx.get("hour") is not None:
            info.append(time_note(ctx["hour"]))
        if ctx.get("closed"):
            info.append(closed_note(ctx["closed"]))
    if todos:
        info.append("[내 할 일]\n" + "\n".join(f"- {t}" for t in todos))
    return "\n\n".join(parts + info)


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def numbers_ok(reply, cards, history, ctx, todos, extra=()):
    """답에 들어 있는 숫자가 카드의 수치이거나 사용자가 쓴 말에 있던 숫자(앱 이야기면 앱 안내의 숫자 extra)인지 검사한다.

    아라비아 숫자만 본다(한글 수사나 다른 문자 숫자는 못 거른다). 근사 검사이며 위반율은 평가 세트로 잰다.
    """
    allowed = {n for c in cards for n in c["numbers"]} | set(extra)
    pool = " ".join([m["content"] for m in history] + todos + ((ctx or {}).get("slots") or []))
    allowed |= set(NUM.findall(pool))
    if ctx:
        allowed.add(str(ctx["days"]))
        if ctx.get("hour") is not None:
            allowed.update({str(ctx["hour"]), str(ctx["hour"] % 12 or 12)})  # 지금 시각을 말해도 된다
    for m in NUM.finditer(reply):
        n = m.group(0)
        if n in allowed:
            continue
        return False  # 프롬프트가 숫자 사용을 막았으므로 "5분", "1회" 같은 지어낸 크기도 통과시키지 않는다
    return True


class Limiter:
    """모델이 주는 조각을 길이 상한과 한 줄 규칙에 맞게 걸러 낸다(퀘스트는 한 문장·한 줄)."""

    def __init__(self, max_chars, one_line=False):
        self.max, self.one_line, self.out, self.done, self.started = max_chars, one_line, "", False, False

    def feed(self, piece):
        if self.done:
            return ""
        if not self.started:
            piece = piece.lstrip(" \t\r\n\"'`“”‘’「」*-•·")
            if not piece:
                return ""
            self.started = True
        if self.one_line and "\n" in piece:
            piece, self.done = piece.split("\n", 1)[0], True
        room = self.max - len(self.out)
        if len(piece) >= room:
            piece, self.done = piece[:room], True
        self.out += piece
        return piece
