"""K203 read-only differential verifier for Go commutation-aware rewrites."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from competition.optimizer.autonomous.core import parse, prove, cost

def run(source, binary, workers, max_candidates, max_gap):
    lines = source.read_text().splitlines(keepends=True)
    request = dict(lines=lines, workers=workers, max_candidates=max_candidates, max_gap=max_gap)
    t0 = time.perf_counter()
    result = subprocess.run([binary], input=json.dumps(request)+"\n", text=True,
                            capture_output=True, check=True, timeout=120)
    elapsed = time.perf_counter()-t0
    proposals = json.loads(result.stdout)
    accepted = []
    for p in proposals:
        start, stop = p["start"], p["stop"]
        replacement = p["replacement"]
        if not (0 <= start < stop <= len(lines)) or not isinstance(replacement, list):
            continue
        before = [parse(s) for s in lines[start:stop]]
        after = [parse(s) for s in replacement]
        if any(g is None for g in before+after):
            continue
        if cost(after) >= cost(before):
            continue
        proof = prove(before, after, 10)
        if proof["status"] == "EXACT":
            accepted.append({**p, "before_cost": cost(before),
                             "after_cost": cost(after), "proof": proof})
    return {"lines": len(lines), "go_seconds": round(elapsed, 6),
            "proposed": len(proposals), "exact_verified": len(accepted),
            "candidates": accepted}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--go",default="./competition/optimizer/research/k203_scan")
    ap.add_argument("--workers",type=int,default=16)
    ap.add_argument("--max-candidates",type=int,default=1000)
    ap.add_argument("--max-gap",type=int,default=64)
    ap.add_argument("--report",type=Path)
    a=ap.parse_args()
    report=run(a.source,a.go,a.workers,a.max_candidates,a.max_gap)
    if a.report:
        a.report.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="candidates"}))
    for c in report["candidates"][:5]:
        print(json.dumps(c))
if __name__=="__main__":
    main()
