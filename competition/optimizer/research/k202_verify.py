"""K202 read-only Go proposal verifier. Does not mutate K200 checkpoints."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from competition.optimizer.autonomous.core import parse, prove, cost

def verify(source: Path, binary: str, workers: int, max_candidates: int):
    lines = source.read_text().splitlines(keepends=True)
    request = {"lines": lines, "workers": workers, "max_candidates": max_candidates}
    start = time.perf_counter()
    run = subprocess.run([binary], input=json.dumps(request) + "\n", text=True,
                         capture_output=True, check=True, timeout=120)
    scan_seconds = time.perf_counter() - start
    candidates = json.loads(run.stdout)
    verified = []
    for item in candidates:
        a, b = item["start"], item["stop"]
        replacement = item["replacement"]
        if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= len(lines)):
            continue
        if not isinstance(replacement, list) or not all(isinstance(s, str) for s in replacement):
            continue
        before = [parse(s) for s in lines[a:b]]
        after = [parse(s) for s in replacement]
        if any(g is None for g in before + after):
            continue
        if cost(after) >= cost(before):
            continue
        proof = prove(before, after, 10)
        if proof["status"] != "EXACT":
            continue
        verified.append({**item, "before_cost": cost(before),
                         "after_cost": cost(after), "proof": proof})
    return {"lines": len(lines), "go_seconds": round(scan_seconds, 6),
            "proposed": len(candidates), "exact_verified": len(verified),
            "candidates": verified}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--go", default="./competition/optimizer/research/k202_scan")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--max-candidates", type=int, default=256)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    result = verify(args.source, args.go, args.workers, args.max_candidates)
    output = json.dumps(result, indent=2)
    if args.report:
        args.report.write_text(output + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "candidates"}))
    for candidate in result["candidates"][:5]:
        print(json.dumps(candidate))

if __name__ == "__main__":
    main()
