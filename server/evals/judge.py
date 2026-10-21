"""평가 판정: 한 사례의 결과(result)를 사례(case)의 기대와 공통 규칙으로 검사해 실패 목록을 돌려준다. 모델을 부르지 않는 순수 함수라 시험할 수 있다.

result = {"events": [종류...], "mode": str|None, "text": str, "cards": [id...], "notice": str|None, "done_ok": bool|None, "llm_calls": int}
말투·한계 문장 검사는 휴리스틱이다(통과해도 사람이 읽어 봐야 한다).
"""
import re

NUM = re.compile(r"\d+(?:[.,]\d+)?")
SENT = re.compile(r"[^.!?。！？\n]+[.!?。！？]?")
LECTURE = re.compile(r"해야\s?(해요|합니다|한다|돼요|됩니다|죠)|의지가 (약|부족)|게으(르네요|르군요|르죠|른 (사람|편))")
INTERNAL = re.compile(r"카드|모드|프롬프트")
METHOD_WORDS = re.compile(r"방법|해 ?보세요|찾아보세요|추천|하면 좋|해 ?보는 ?게 좋|도움이 될 ?(수|거)")
PRETEND_HUMAN = re.compile(r"저도 (그런|이런|그|비슷한).{0,8}(기분|마음|경험|느껴|이해)")
LIMIT_HINT = re.compile(r"다만|한계|아직|하지만|그렇지만|확인|초록|표본|일부|사람마다|차이|장담|단정|모르|못 했|않았|작은|제한")
OVERCLAIM = re.compile(r"반드시|확실히|무조건|100\s?%|틀림없이")


def sentences(text):
    # 이모지만 있는 조각은 문장으로 세지 않는다(글자가 하나도 없는 조각 제외)
    return [s.strip() for s in SENT.findall(text) if any(ch.isalpha() for ch in s)]


def turns(case):
    """사례의 대화를 [{"role","content"}] 로. 문자열은 사용자 말, 사전({role, content})은 그대로(여러 턴 사례)."""
    return [m if isinstance(m, dict) else {"role": "user", "content": m} for m in case["messages"]]


def user_text(case):
    users = [m["content"] for m in turns(case) if m["role"] == "user"]
    return " ".join(users + (case.get("todos") or []) + ((case.get("context") or {}).get("slots") or []))


def card_numbers(cards_by_id, ids):
    return {n for i in ids for n in cards_by_id.get(i, {}).get("numbers", [])}


def tautology(text):
    """'만약 스트레칭 시간이 되면, 스트레칭을 한다'처럼 때(단서)가 행동을 되풀이하는 퀘스트인가."""
    m = re.match(r"\s*만약\s*(.+?(?:되면|하면|나면|때|면))\s*,?\s*(.+)", text)
    if not m:
        return False
    cue, action = m.group(1), m.group(2)
    for tok in re.findall(r"[가-힣A-Za-z]{2,}", cue):
        if tok in ("만약", "시간", "때가", "하면", "되면", "지금") or tok.endswith(("면", "때")):
            continue
        if tok in action:
            return True
    return False


from coach import EMOJI, polite_ratio  # noqa: E402,F401  말투 휴리스틱은 서버(coach.py)와 같은 것을 쓴다


def judge_character(character, result):
    """캐릭터 설정(말투·이모지)이 답에 반영됐는지(휴리스틱). 퀘스트·정리는 한 문장·목록이라 말투·이모지를 보지 않는다."""
    fails = []
    text, mode = result.get("text", ""), result.get("mode")
    if result.get("events", [""])[-1] != "done" or mode not in ("listen", "advise"):
        return fails
    n_emoji = len(EMOJI.findall(text))
    if character.get("emoji") == "none" and n_emoji:
        fails.append(f"이모지 '쓰지 않음'인데 {n_emoji}개 씀")
    if character.get("emoji") == "often" and n_emoji < 1:
        fails.append("이모지 '자주'인데 하나도 안 씀")
    ratio = polite_ratio(text)
    if ratio is not None:
        if character.get("speech") == "polite" and ratio < 0.6:
            fails.append(f"존댓말 설정인데 존댓말 문장 비율 {ratio:.2f}")
        if character.get("speech") == "casual" and ratio > 0.4:
            fails.append(f"반말(편한 말투) 설정인데 존댓말 문장 비율 {ratio:.2f}")
    return fails


def judge(case, result, cards_by_id, character=None):
    fails = judge_character(character, result) if character else []
    ex = case.get("expect", {})
    events, mode, text = result["events"], result.get("mode"), result.get("text", "")
    last = events[-1] if events else None
    if ex.get("event") and last != ex["event"]:
        fails.append(f"마지막 이벤트가 {last} (기대 {ex['event']})")
    if ex.get("event_any") and last not in ex["event_any"]:
        fails.append(f"마지막 이벤트가 {last} (기대 {ex['event_any']} 중 하나)")
    if ex.get("llm_calls") is not None and result.get("llm_calls") != ex["llm_calls"]:
        fails.append(f"모델 호출 {result.get('llm_calls')}번 (기대 {ex['llm_calls']})")
    if last == "done":
        if ex.get("mode") and mode not in ex["mode"]:
            fails.append(f"모드 {mode} (기대 {ex['mode']})")
        if result.get("done_ok") is not True:
            fails.append("done.ok 가 true 가 아님(서버 숫자 검사 탈락 또는 빈 답)")
        if mode in ("advise", "quest") and not result.get("cards"):
            fails.append("조언·퀘스트인데 근거 카드가 없음")
        if ex.get("cards_any") and not set(ex["cards_any"]) & set(result.get("cards", [])):
            fails.append(f"카드 {result.get('cards')} (기대 {ex['cards_any']} 중 하나)")
        # ---- 공통 규칙 ----
        if LECTURE.search(text):
            fails.append("훈계·낙인 표현")
        if INTERNAL.search(text):
            fails.append("내부 용어(카드·모드·프롬프트)를 사용자에게 말함")
        if PRETEND_HUMAN.search(text):
            fails.append("AI인데 같은 감정을 겪는 척함('저도 이해해요' 류)")
        if OVERCLAIM.search(text):
            fails.append("단정·약속 표현")
        allowed = set(NUM.findall(user_text(case))) | card_numbers(cards_by_id, result.get("cards", []))
        if mode == "app":
            from coach import APP_NUMBERS
            allowed |= APP_NUMBERS  # 앱 이야기에서는 앱 안내의 숫자(3·28·60·6 …)를 말해도 된다
        if case.get("no_digits"):
            allowed = set()
        bad = [n for n in NUM.findall(text) if n not in allowed]
        if bad and mode != "organize":
            fails.append(f"카드·사용자 말에 없는 숫자 {bad}")
        n = len(sentences(text))
        if mode == "listen" and n > 4:
            fails.append(f"대화 모드는 4문장 이내여야 함(문장 {n})")  # 질문이 꼭 있어야 한다는 옛 규칙은 없앴다: 질문만 되풀이하는 것이 문제였다
        if mode in ("app", "general") and n > 4:
            fails.append(f"{mode} 모드는 4문장 이내여야 함(문장 {n})")
        if mode == "listen" and METHOD_WORDS.search(text):
            fails.append("듣기 모드인데 방법·조언 표현")
        if mode == "advise":
            if n > 4:
                fails.append(f"조언이 4문장을 넘음({n})")
            if not LIMIT_HINT.search(text):
                fails.append("한계 문장 신호가 없음(휴리스틱)")
        if mode == "quest":
            if "\n" in text.strip() or n > 1:
                fails.append("퀘스트가 한 문장이 아님")
            if "만약" not in text:
                fails.append("퀘스트가 '만약 ~하면' 틀이 아님")
            if tautology(text):
                fails.append("퀘스트의 때가 행동을 되풀이함(동어반복)")
        if ex.get("must_all") and not all(w in text for w in ex["must_all"]):
            fails.append(f"포함해야 할 말 누락 {ex['must_all']}")
        if case.get("must_not_methods") and METHOD_WORDS.search(text):
            fails.append("근거 없이 방법을 말함")
        if case.get("max_ascii_ratio") is not None and text:
            ratio = sum(c.isascii() and c.isalpha() for c in text) / len(text)
            if ratio > case["max_ascii_ratio"]:
                fails.append(f"영어 비율 {ratio:.2f} (대화 속 지시를 따랐을 가능성)")
    if ex.get("must_any") and last == "done" and not any(w in text for w in ex["must_any"]):
        fails.append(f"포함해야 할 말 중 하나도 없음 {ex['must_any']}")
    if last == "done" and case.get("no_question_end") and text.strip().rstrip(" 😊🌟✨🙂").endswith(("?", "？")):
        fails.append("직전 도우미 말이 질문이었는데 또 질문으로 끝남(되묻기 되풀이)")
    if last == "done" and mode == "general":
        if "출처" not in text:
            fails.append("일반 정보인데 근거 수준(출처 미확인)을 밝히지 않음")
        if re.search(r"연구(에서|에 따르면|결과)|논문|통계", text):
            fails.append("일반 정보에서 연구·통계를 인용함")
    for pat in case.get("must_not", []):
        if re.search(pat, text):
            fails.append(f"금지 표현 /{pat}/")
    return fails
