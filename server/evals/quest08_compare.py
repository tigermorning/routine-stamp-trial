"""Langfuse 트레이스(environment=quest08)를 release 별로 나눠 센다. 재생 결과 파일과 시작 시각 순서로 짝지어 항목별 판정을 낸다.
  python evals/quest08_compare.py --data dataset.json --runs v1-replay=replay_v1.json exp-A-tokens1500=replay_A.json ...
출력: 표(마크다운)와 quest08/compare_<태그>.json. 키는 출력하지 않는다.
"""
import argparse
import base64
import collections
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--data", default="dataset.json")
ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--tag", default="compare")
ap.add_argument("--cap", type=int, default=450)
a = ap.parse_args()
for line in (HERE.parents[1] / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip(chr(34) + chr(39)))
tok = base64.b64encode(f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()).decode()


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
    if o["environment"] != "quest08":
        continue
    rel = (o.get("metadata") or {}).get("resourceAttributes.langfuse.release")
    by[rel][o["traceId"]].setdefault(o["name"], []).append(o)
data = json.loads((HERE / "quest08" / a.data).read_text(encoding="utf-8"))
result = {}
print("| 변형(release) | 항목 | 빈 답(문제) | 빈 답(정상) | 한도에서 끊김 | 시간 p50 / p90 (초) | 모드 바뀜 | 출력 토큰 평균 |\n|---|---|---|---|---|---|---|---|")
for spec in a.runs:
    rel, fn = spec.split("=")
    cap = a.cap
    if ":" in fn:
        fn, cap = fn.split(":")
        cap = int(cap)
    rep = json.loads((HERE / "quest08" / fn).read_text(encoding="utf-8"))
    T = sorted([v for v in by[rel].values() if "chat-turn" in v], key=lambda v: v["chat-turn"][0]["startTime"])
    if len(T) != len(rep):
        print(f"!! {rel}: 트레이스 {len(T)}개 / 재생 {len(rep)}개 — 짝이 맞지 않음(전송이 덜 끝났을 수 있음)")
        continue
    rows = []
    for it, r, v in zip(data, rep, T):
        g = (v.get("generate-reply") or [None])[0]
        rows.append({"id": it["id"], "group": it["group"], "empty": not r["reply"], "mode": r["mode"], "base_mode": it["baseline"]["mode"], "ok": r["ok"],
                     "out": g["usageDetails"].get("output") if g else None, "lat": v["chat-turn"][0]["latency"], "trace": v["chat-turn"][0]["traceId"], "reply": r["reply"]})
    lat = sorted(x["lat"] for x in rows)
    outs = [x["out"] for x in rows if x["out"] is not None]
    pe = sum(x["empty"] for x in rows if x["group"] == "problem")
    ne = sum(x["empty"] for x in rows if x["group"] == "normal")
    cut = sum(1 for x in rows if x["out"] is not None and x["out"] >= cap)
    mc = sum(1 for x in rows if x["mode"] != x["base_mode"])
    print(f"| {rel} | {len(rows)} | {pe}/16 | {ne}/16 | {cut} | {lat[len(lat)//2]:.1f} / {lat[int(len(lat)*.9)]:.1f} | {mc} | {sum(outs)/max(1,len(outs)):.0f} |")
    result[rel] = rows
(HERE / "quest08" / f"{a.tag}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
