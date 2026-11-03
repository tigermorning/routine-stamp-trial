"""지시문을 Langfuse 프롬프트 관리에서 라벨로 가져온다(노드 11 섹션 4). 가져오지 못하면 코드의 문장(fallback)으로 답한다.

- 이름: stamp-plan(모드 고르기 지시문), stamp-listen-rule(듣기 모드 규칙).
- 라벨: PROMPT_LABEL 이 있으면 그 라벨, 없으면 ENV 가 production 이면 production, 그 밖에는 staging.
  배포는 실험을 통과한 버전에 production 라벨을 옮기는 일이고, 롤백은 이전 버전에 다시 붙이는 일이다(코드 재배포 없음).
- Langfuse 키가 없으면(tracing 꺼짐) 아무것도 가져오지 않고 코드의 문장을 쓴다. 가져온 결과는 60초 캐시한다(SDK).
- 돌려주는 prompt 객체를 generation 에 연결하면 트레이스에서 프롬프트 이름과 버전이 보인다.
"""
import logging
import os

import tracing

log = logging.getLogger("coach")
CACHE_SECONDS = 60


def label():
    explicit = os.environ.get("PROMPT_LABEL", "").strip()
    if explicit:
        return explicit
    return "production" if os.environ.get("ENV", "").strip().lower() == "production" else "staging"


def get(name, fallback):
    """(지시문 글, prompt 객체 또는 None). 실패해도 예외를 내지 않고 fallback 글을 돌려준다."""
    client = tracing.get_client()
    if client is None:
        return fallback, None
    try:
        prompt = client.get_prompt(name, label=label(), type="text", fallback=fallback, cache_ttl_seconds=CACHE_SECONDS,
                                   fetch_timeout_seconds=3, max_retries=1)
        text = prompt.compile()
        # fallback 으로 만든 객체는 Langfuse 버전이 아니므로 generation 에 연결하지 않는다
        return text, (None if getattr(prompt, "is_fallback", False) else prompt)
    except Exception as error:  # 키·주소 오류여도 대답은 코드의 문장으로 이어 간다
        log.warning("prompt fetch failed: %s", type(error).__name__)
        return fallback, None
