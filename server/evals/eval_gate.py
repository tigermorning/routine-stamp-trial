"""노드 11 섹션 6: 평가 관문. 프롬프트 라벨을 옮기기 전이나 배포 전에 실험을 돌리고, 기준에 못 미치면 1로 끝난다(배포를 멈춘다).

  python evals/eval_gate.py              지금 설정(PROMPT_LABEL·REPLY_GATE)으로 stamp-mode·stamp-listen-reply 를 한 번씩 돌려 판정
  python evals/eval_gate.py --runs 2     두 번씩(흔들림이 커서 판단에는 두 번을 권한다)

기준은 evals/gate_thresholds.json(2026-11-03 v2 를 내보낼 때 실험 결과로 정한 바닥값). 진짜 LLM 을 부르므로 비용이 든다.
필요한 환경변수: LANGFUSE_*, LLM_*(도우미), JUDGE_API_KEY·JUDGE_MODEL(Claude 심사). deploy.sh --eval-gate 가 부른다.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

JUDGES = ("judge-no-effect-claim", "judge-natural", "judge-relevance")


def summarize(result):
    """평가자별 통과 수와, 심사 셋을 모두 통과한 항목 수."""
    per, all_judges = {}, 0
    for ir in result.item_results:
        vals = {ev.name: ev.value for ev in ir.evaluations}
        for name, v in vals.items():
            if v is not None:
                per[name] = per.get(name, 0) + bool(v)
        if all(vals.get(j) for j in JUDGES) and all(j in vals for j in JUDGES):
            all_judges += 1
    return per, all_judges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    a = ap.parse_args()
    from langfuse import get_client
    import langfuse_experiment as X

    th = json.loads((HERE / "gate_thresholds.json").read_text(encoding="utf-8"))
    lf = get_client()
    stamp = datetime.now().strftime("%m%d-%H%M")
    got = {"mode-correct": [], "all-judges": [], "no-invented-numbers": [], "no-repeat-question": [], "one-question": []}
    for i in range(1, a.runs + 1):
        per, _ = summarize(X.run(lf, "mode", f"gate-{stamp}-{i}"))
        got["mode-correct"].append(per.get("mode-correct", 0))
        per, all_j = summarize(X.run(lf, "listen", f"gate-{stamp}-{i}"))
        got["all-judges"].append(all_j)
        for k in ("no-invented-numbers", "no-repeat-question", "one-question"):
            got[k].append(per.get(k, 0))
    failed = []
    for key, floor in th["floors"].items():
        avg = sum(got[key]) / len(got[key])
        ok = avg >= floor
        print(f"{'통과' if ok else '탈락'} {key}: 평균 {avg:.1f} (바닥 {floor})")
        if not ok:
            failed.append(key)
    if failed:
        print("평가 관문 탈락:", ", ".join(failed), "— 라벨을 옮기거나 배포하지 않는다")
        return 1
    print("평가 관문 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
