"""오늘의 한마디: 실제로 있는 격언·속담 모음(server/quotes.json)을 읽어 서버 DB 표(quotes)에 넣는다.

- 이 앱이 지어낸 문장은 넣지 않는다(사용자 지적 2026-11-04: 지어낸 말은 감동이 없다). 속담과 저작권이 끝난 고전만 쓰고, 항목마다 출처와 확인한 주소를 적는다.
- SNS(Pinterest·Instagram)에 퍼진 문구는 모으지 않는다(저작권·약관·출처 불명). 항목은 verified=true 이고 ko·author·source·source_url 이 모두 있는 것만 받는다.
"""
import json
from pathlib import Path

QUOTES_FILE = Path(__file__).resolve().parent / "quotes.json"
REQUIRED = ("ko", "author", "source", "source_url")


def valid(item):
    return isinstance(item, dict) and item.get("verified") is True and all(str(item.get(k, "")).strip() for k in REQUIRED)


def load_quotes(path=None):
    p = Path(path) if path else QUOTES_FILE
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [i for i in data if valid(i)] if isinstance(data, list) else []
