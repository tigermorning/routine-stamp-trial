"""배포 뒤 확인: Langfuse 트레이스(environment=quest08)를 release(버전)별로 나눠 같은 현상을 센다.
  python evals/quest08_versions.py v1-baseline v1-newconv v2-fix
빈 답 = generate-reply 의 reply_chars 가 0. 한도 도달 = 출력 토큰이 그 버전의 한도 이상(옛 450, 고친 1500).
"""
import base64
import collections
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
for line in (HERE.parents[1] / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip(chr(34) + chr(39)))
tok = base64.b64encode(f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()).decode()
CAP = {"v1-baseline": 450, "v1-newconv": 450, "v2-fix": 1500}


def get(path):
    for i in range(8):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request("https://us.cloud.langfuse.com" + path, headers={"Authorization": "Basic " + tok})))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(8 * (i + 1))


obs, cur = [], ""
while True:
    d = get("/api/public/v2/observations?limit=1000&fields=core,basic,usage,metadata&fromStartTime=2026-11-09T00:00:00Z&toStartTime=2026-11-12T00:00:00Z" + (f"&cursor={cur}" if cur else ""))
    obs += d["data"]
    cur = d["meta"].get("cursor")
    if not cur or not d["data"]:
        break
by = collections.defaultdict(lambda: collections.defaultdict(dict))
for o in obs:
    if o["environment"] == "quest08":
        by[(o.get("metadata") or {}).get("resourceAttributes.langfuse.release")][o["traceId"]].setdefault(o["name"], []).append(o)
print("| 버전(release) | 턴 | 답 생성 턴 | 빈 답 | 한도 도달(끊김) | 시간 p50 / p90 (초) | 답 단계 출력 토큰 평균 | 한 턴 비용 평균 ($) |\n|---|---|---|---|---|---|---|---|")
summary = {}
for rel in sys.argv[1:]:
    T = list(by[rel].values())
    T = [v for v in T if "chat-turn" in v]
    gen = [v["generate-reply"][0] for v in T if "generate-reply" in v]
    empty = [g for g in gen if (g.get("metadata") or {}).get("reply_chars") == 0]
    cut = [g for g in gen if g["usageDetails"].get("output", 0) >= CAP.get(rel, 450)]
    lat = sorted(v["chat-turn"][0]["latency"] for v in T)
    cost = [sum((x.get("totalCost") or 0) for n in ("generate-reply", "choose-mode") for x in v.get(n, [])) for v in T]
    toks = [g["usageDetails"].get("output", 0) for g in gen]
    print(f"| {rel} | {len(T)} | {len(gen)} | {len(empty)} ({100*len(empty)/max(1,len(gen)):.0f}%) | {len(cut)} ({100*len(cut)/max(1,len(gen)):.0f}%) | {lat[len(lat)//2]:.1f} / {lat[int(len(lat)*.9)]:.1f} | {sum(toks)/max(1,len(toks)):.0f} | {sum(cost)/max(1,len(cost)):.5f} |")
    summary[rel] = {"turns": len(T), "gen": len(gen), "empty": len(empty), "cut": len(cut), "lat_p50": lat[len(lat)//2], "lat_p90": lat[int(len(lat)*.9)], "empty_traces": [g["traceId"] for g in empty][:20]}
(HERE / "quest08" / "versions.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
