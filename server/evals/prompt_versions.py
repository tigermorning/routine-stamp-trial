"""노드 11 섹션 4: Langfuse 프롬프트 버전 관리. 문장은 policy.py 에 있다(V1 = 처음 문장, 지금 코드는 stamp-plan v3·stamp-listen-rule v3).

  python evals/prompt_versions.py create      stamp-plan v1(production·staging)·v2(staging), stamp-listen-rule v1·v2 를 만든다(처음 한 번만)
  python evals/prompt_versions.py create-v3   stamp-listen-rule v3(staging)
  python evals/prompt_versions.py labels      지금 라벨이 어느 버전을 가리키는지 본다
  python evals/prompt_versions.py promote stamp-listen-rule 3   그 버전에 production 라벨을 옮긴다(롤백도 같은 명령으로 이전 번호)

2026-11-03 실행 기록: create → stamp-plan v1·v2, stamp-listen-rule v1·v2 / create-v3 → stamp-listen-rule v3 /
promote stamp-plan 2(기준 1 통과) / promote stamp-listen-rule 3(실험 D 기준 2·3 통과) /
create-plan-v3 → stamp-plan v3(관계 고민 회귀 고침) / promote stamp-plan 3(모드 20·20, 회귀 0).
라벨을 옮기기 전에 evals/eval_gate.py 로 평가 관문을 돌린다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import policy  # noqa: E402

VERSIONS = {
    "stamp-plan": [policy.PLAN_SYSTEM_V1, policy.PLAN_SYSTEM_V2],
    "stamp-listen-rule": [policy.LISTEN_RULE_V1, policy.LISTEN_RULE_V2],
}

if __name__ == "__main__":
    from langfuse import get_client

    lf = get_client()
    cmd = sys.argv[1]
    if cmd == "create":
        for name, (v1, v2) in VERSIONS.items():
            p1 = lf.create_prompt(name=name, prompt=v1, labels=["production", "staging"], type="text", commit_message="v1: policy.py 의 처음 문장")
            p2 = lf.create_prompt(name=name, prompt=v2, labels=["staging"], type="text", commit_message="v2: 노드 11 실패 유형 고침")
            print(name, "v1 =", p1.version, "| v2 =", p2.version)
    elif cmd == "create-v3":
        p3 = lf.create_prompt(name="stamp-listen-rule", prompt=policy.LISTEN_RULE_V3, labels=["staging"], type="text",
                              commit_message="v3: v2 실험에서 남은 효과 단정·비워 둔 제안 막기")
        print("stamp-listen-rule v3 =", p3.version)
    elif cmd == "create-plan-v3":
        p = lf.create_prompt(name="stamp-plan", prompt=policy.PLAN_SYSTEM_V3, labels=["staging"], type="text",
                             commit_message="v3: 자기 경험 규칙을 루틴·앱으로 좁혀 관계 고민 회귀 고침")
        print("stamp-plan v3 =", p.version)
    elif cmd == "labels":
        for name in VERSIONS:
            for lab in ("production", "staging"):
                p = lf.get_prompt(name, label=lab, type="text", cache_ttl_seconds=0)
                print(name, lab, "→ 버전", p.version)
    elif cmd == "promote":
        name, version = sys.argv[2], int(sys.argv[3])
        lf.update_prompt(name=name, version=version, new_labels=["production"])
        print(name, "버전", version, "에 production 라벨")
