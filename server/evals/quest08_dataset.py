"""Main Quest 08: 기준선(v1) 대화에서 데이터셋을 만든다. 문제 항목(빈 답 16) + 정상 항목(비지 않고 한도 전에 끝난 답 16).
항목 = 그 턴까지의 대화(사용자 말 + 그때까지의 도우미 답)와 맥락. 결과: quest08/dataset.json
  python evals/quest08_dataset.py            파일 만들기
  python evals/quest08_dataset.py upload     Langfuse 데이터셋 stamp-quest08-empty-reply 로 올리기(같은 id 는 고쳐 씀)
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
convs = {c["id"]: c for c in json.loads((HERE / "quest08/convs_a.json").read_text(encoding="utf-8"))}
rows = json.loads((HERE / "quest08/run_a_v1.json").read_text(encoding="utf-8"))


def history(r):
    h = []
    for p in [x for x in rows if x["conv"] == r["conv"] and x["turn"] <= r["turn"]]:
        h.append({"role": "user", "content": p["user"]})
        if p["turn"] < r["turn"] and p["reply"]:
            h.append({"role": "assistant", "content": p["reply"]})
    return h


gen = [r for r in rows if r["out_tokens"] is not None]
problem = [r for r in gen if not r["reply"]]
normal_pool = [r for r in gen if r["reply"] and r["out_tokens"] < 450]
normal = normal_pool[::max(1, len(normal_pool) // 16)][:16]
items = []
for group, lst in (("problem", problem), ("normal", normal)):
    for r in lst:
        items.append({"id": f"{r['conv']}-t{r['turn']}", "group": group, "messages": history(r), "context": convs[r["conv"]].get("context"),
                      "baseline": {"trace": r["trace"], "mode": r["mode"], "empty": not r["reply"], "out_tokens": r["out_tokens"], "latency": r["latency"]}})


def upload():
    from langfuse import Langfuse
    lf = Langfuse()
    name = "stamp-quest08-empty-reply"
    try:
        lf.create_dataset(name=name, description="Main Quest 08: 빈 답(문제 16) + 정상 답(정상 16). 입력=대화, 메타=기준선 결과")
    except Exception:
        pass
    for it in items:
        lf.create_dataset_item(dataset_name=name, id=f"q08-{it['id']}", input={"messages": it["messages"], "context": it["context"]},
                               metadata={"group": it["group"], **it["baseline"]})
    lf.flush()
    print("uploaded", len(items))


if __name__ == "__main__":
    (HERE / "quest08/dataset.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("items", len(items), "problem", len(problem), "normal", len(normal))
    if len(sys.argv) > 1 and sys.argv[1] == "upload":
        for line in (HERE.parents[1] / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip(chr(34)+chr(39)))
        upload()
