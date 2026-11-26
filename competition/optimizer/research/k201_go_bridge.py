"""K201 Go fast-path for K200. Fail closed: Python proves every Go proposal."""
import argparse
import json
from pathlib import Path
import subprocess
from .invsqrt_cumulative_campaign_k200 import find_rewrite as python_find
from ..autonomous.core import parse, prove, cost

def find_rewrite(lines, methods, span, stride, max_wires, max_windows, deadline, seed,
                 executable="./competition/optimizer/research/k201_go_scan"):
    try:
        result = subprocess.run([executable], input=json.dumps({
            "lines": lines, "max_windows": max_windows})+"\n",
            text=True, capture_output=True, timeout=10, check=True)
        proposal = json.loads(result.stdout)
        if proposal:
            start, stop = proposal["start"], proposal["stop"]
            if not (0 <= start < stop <= len(lines)):
                raise ValueError("Invalid Go bounds")
            before = [parse(x) for x in lines[start:stop]]
            after = [parse(x) for x in proposal["replacement"]]
            if all(x is not None for x in before + after):
                if cost(after) < cost(before):
                    proof = prove(before, after, max_wires)
                    if proof["status"] == "EXACT":
                        return lines[:start]+proposal["replacement"]+lines[stop:], {
                            "method": "go_commuting_cancel", "region": [start,stop],
                            "before_cost": cost(before), "after_cost": cost(after),
                            "proof": proof, "detail": {"go_kind": proposal["kind"]},
                            "windows_scanned": proposal["scanned"]}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    return python_find(lines, methods, span, stride, max_wires, max_windows, deadline, seed)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--go",default="./competition/optimizer/research/k201_go_scan")
    a=p.parse_args()
    lines=a.source.read_text().splitlines(keepends=True)
    import time
    candidate, detail=find_rewrite(lines,(),32,8,8,10000,time.monotonic()+60,0,a.go)
    print(json.dumps({"found":candidate is not None,"detail":detail},default=str))

if __name__=="__main__":
    main()
