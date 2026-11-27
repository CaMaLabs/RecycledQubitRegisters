"""K205: exact CCX factoring via affine conjugation, cumulative checkpoint campaign.

Identity (all four wires distinct):
CCX(a,c,t) CCX(b,c,t) = CX(a,b) CCX(b,c,t) CX(a,b).
Two CCX become one CCX and two CX. A candidate is accepted ONLY if
the existing exhaustive dirty-ancilla prover returns EXACT.
"""
import argparse
import json
import time
from pathlib import Path
from collections import Counter

from competition.optimizer.autonomous.core import parse, commute, prove, cost
from competition.optimizer.research.k204_cumulative import atomic, digest

def candidates(lines, gap=128, cap=2000):
    gates = [parse(line) for line in lines]
    emitted = 0
    for i, first in enumerate(gates):
        if first is None or first.op != "CCX":
            continue
        for j in range(i + 1, min(len(gates), i + gap + 2)):
            other = gates[j]
            if other is None:
                break
            if other.op == "CCX" and first.q[2] == other.q[2]:
                shared = set(first.q[:2]) & set(other.q[:2])
                if len(shared) == 1:
                    c = next(iter(shared))
                    a = next(x for x in first.q[:2] if x != c)
                    b = next(x for x in other.q[:2] if x != c)
                    t = first.q[2]
                    if len({a,b,c,t}) == 4:
                        # The first CCX commutes with every intervening gate,
                        # so it can be moved immediately before the second.
                        replacement = (lines[i+1:j] +
                                       [f"CX q{a} q{b}\n",
                                        f"CCX q{b} q{c} q{t}\n",
                                        f"CX q{a} q{b}\n"])
                        yield i, j + 1, replacement
                        emitted += 1
                        if emitted >= cap:
                            return
            if not commute(first, other):
                break

def counts(lines):
    return Counter(x.split()[0] for x in lines if x.split())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--max-gap", type=int, default=128)
    p.add_argument("--max-candidates", type=int, default=2000)
    p.add_argument("--max-rewrites", type=int, default=500)
    p.add_argument("--hours", type=float, default=2)
    p.add_argument("--max-wires", type=int, default=10)
    args = p.parse_args()
    if args.max_gap < 0 or args.max_candidates < 1 or args.max_rewrites < 1 or args.hours <= 0 or not 4 <= args.max_wires <= 10:
        p.error("invalid limits")
    source = args.source.resolve()
    out = args.out.resolve()
    if source == out / "current.kmx" or out == source.parent or out in source.parents:
        p.error("source must remain outside output directory")
    original = source.read_bytes()
    original_sha = digest(original)
    out.mkdir(parents=True, exist_ok=True)
    state_path, circuit_path = out / "state.json", out / "current.kmx"
    if state_path.exists() != circuit_path.exists():
        p.error("partial checkpoint; inspect before restarting")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        raw = circuit_path.read_bytes()
        if state["source_sha256"] != original_sha or state["current_sha256"] != digest(raw):
            p.error("checkpoint/source SHA mismatch")
    else:
        raw = original
        state = {"source_sha256": original_sha, "current_sha256": original_sha,
                 "rewrites": [], "official_status": "NOT_RUN"}
        atomic(circuit_path, raw)
        atomic(state_path, (json.dumps(state, indent=2)+"\n").encode())
    lines = raw.decode().splitlines(keepends=True)
    deadline = time.monotonic() + args.hours * 3600
    while len(state["rewrites"]) < args.max_rewrites and time.monotonic() < deadline:
        chosen = None
        seen = 0
        for i, j, replacement in candidates(lines, args.max_gap, args.max_candidates):
            seen += 1
            before = [parse(x) for x in lines[i:j]]
            after = [parse(x) for x in replacement]
            if any(g is None for g in before + after) or cost(after) >= cost(before):
                continue
            proof = prove(before, after, args.max_wires)
            if proof["status"] == "EXACT":
                chosen = (i, j, replacement, proof, cost(before), cost(after))
                break
        if chosen is None:
            print("K205_STALLED", json.dumps({"proposals": seen}), flush=True)
            break
        i, j, replacement, proof, old_cost, new_cost = chosen
        lines = lines[:i] + replacement + lines[j:]
        child = "".join(lines).encode()
        child_sha = digest(child)
        event = {"index": len(state["rewrites"])+1, "method": "ccx_affine_conjugation",
                 "region": [i,j], "before_cost": old_cost, "after_cost": new_cost,
                 "parent_sha256": state["current_sha256"], "sha256": child_sha,
                 "proof": proof}
        folder = out / "candidates" / child_sha
        folder.mkdir(parents=True, exist_ok=True)
        atomic(folder / "circuit.kmx", child)
        atomic(folder / "local_proof.json", (json.dumps(event,indent=2)+"\n").encode())
        atomic(circuit_path, child)
        state["rewrites"].append(event)
        state["current_sha256"] = child_sha
        atomic(state_path, (json.dumps(state,indent=2)+"\n").encode())
        c = counts(lines)
        print("K205_REWRITE", json.dumps({"index":event["index"],"region":[i,j],
              "CCX":c["CCX"],"CX":c["CX"],"sha256":child_sha}),flush=True)
    c = counts(lines)
    print("K205_SUMMARY",json.dumps({"rewrites":len(state["rewrites"]),
          "instructions":len(lines),"CCX":c["CCX"],"CX":c["CX"],"X":c["X"],
          "sha256":state["current_sha256"],"official_status":"NOT_RUN"}),flush=True)

if __name__ == "__main__":
    main()
