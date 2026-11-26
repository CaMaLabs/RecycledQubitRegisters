"""K204: cumulative, crash-resumable application of K203 exact local rewrites.

Writes only to --out. Never changes K200 checkpoint or invokes official verifier.
Every accepted candidate is re-proven against the current circuit using Python.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from competition.optimizer.autonomous.core import parse, prove, cost

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic(path, data):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)

def scan(lines, binary, workers, limit, gap):
    request = {"lines": lines, "workers": workers,
               "max_candidates": limit, "max_gap": gap}
    proc = subprocess.run([str(binary)], input=json.dumps(request) + "\n",
                          text=True, capture_output=True, check=True, timeout=120)
    proposals = json.loads(proc.stdout)
    if not isinstance(proposals, list):
        raise ValueError("Go scanner did not return a list")
    return proposals

def validated(lines, item, max_wires):
    try:
        start, stop = item["start"], item["stop"]
        repl = item["replacement"]
        if type(start) is not int or type(stop) is not int:
            return None
        if not (0 <= start < stop <= len(lines)) or not isinstance(repl, list):
            return None
        if any(not isinstance(s, str) or not s.endswith("\n") for s in repl):
            return None
        before = [parse(x) for x in lines[start:stop]]
        after = [parse(x) for x in repl]
        if any(x is None for x in before + after):
            return None
        old, new = cost(before), cost(after)
        if new >= old:
            return None
        proof = prove(before, after, max_wires)
        if proof["status"] != "EXACT":
            return None
        return (lines[:start] + repl + lines[stop:],
                {"method": "k204_" + str(item.get("method", "go")),
                 "region": [start, stop], "before_cost": old,
                 "after_cost": new, "proof": proof})
    except (KeyError, TypeError, ValueError, OverflowError, IndexError):
        return None

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--go", type=Path,
                   default=Path("competition/optimizer/research/k203_scan"))
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--max-gap", type=int, default=128)
    p.add_argument("--max-candidates", type=int, default=2000)
    p.add_argument("--max-wires", type=int, default=10)
    p.add_argument("--max-rewrites", type=int, default=500)
    p.add_argument("--hours", type=float, default=2)
    args = p.parse_args()
    if args.max_rewrites < 1 or args.hours <= 0 or not 2 <= args.max_wires <= 10:
        p.error("invalid campaign limits")
    src = args.source.resolve()
    out = args.out.resolve()
    if src == out / "current.kmx":
        p.error("source must not be the output checkpoint")
    if out == src.parent or out in src.parents:
        p.error("output must not contain the source")
    source_bytes = src.read_bytes()
    source_sha = digest(source_bytes)
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "state.json"
    circuit_path = out / "current.kmx"
    if state_path.exists() != circuit_path.exists():
        p.error("partial checkpoint: inspect manually before resuming")
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state["source_sha256"] != source_sha:
            p.error("source SHA mismatch")
        raw = circuit_path.read_bytes()
        if digest(raw) != state["current_sha256"]:
            p.error("checkpoint SHA mismatch")
    else:
        raw = source_bytes
        state = {"source_sha256": source_sha, "current_sha256": source_sha,
                 "rewrites": [], "official_status": "NOT_RUN"}
        atomic(circuit_path, raw)
        atomic(state_path, json.dumps(state, indent=2).encode())
    lines = raw.decode("utf-8").splitlines(keepends=True)
    deadline = time.monotonic() + args.hours * 3600
    while len(state["rewrites"]) < args.max_rewrites and time.monotonic() < deadline:
        start_time = time.monotonic()
        proposals = scan(lines, args.go, args.workers,
                         args.max_candidates, args.max_gap)
        chosen = None
        # Go already prioritizes CCX; Python independently checks every candidate.
        for proposal in proposals:
            chosen = validated(lines, proposal, args.max_wires)
            if chosen is not None:
                break
        if chosen is None:
            print("K204_STALLED", json.dumps({"proposals": len(proposals)}), flush=True)
            break
        updated, detail = chosen
        child = "".join(updated).encode("utf-8")
        child_sha = digest(child)
        event = {"index": len(state["rewrites"]) + 1,
                 "parent_sha256": state["current_sha256"],
                 "sha256": child_sha, **detail}
        # Persist immutable candidate before changing active checkpoint.
        folder = out / "candidates" / child_sha
        folder.mkdir(parents=True, exist_ok=True)
        atomic(folder / "circuit.kmx", child)
        atomic(folder / "local_proof.json", json.dumps(event, indent=2).encode())
        # Recoverable if interrupted between these writes: immutable candidate
        # and parent are retained. Do not silently accept partial checkpoints.
        atomic(circuit_path, child)
        state["rewrites"].append(event)
        state["current_sha256"] = child_sha
        atomic(state_path, json.dumps(state, indent=2).encode())
        lines = updated
        print("K204_REWRITE", json.dumps({
            "index": event["index"], "method": detail["method"],
            "region": detail["region"], "sha256": child_sha,
            "seconds": round(time.monotonic() - start_time, 3)}), flush=True)
    print("K204_SUMMARY", json.dumps({
        "rewrites": len(state["rewrites"]),
        "instructions": len(lines),
        "sha256": state["current_sha256"],
        "official_status": "NOT_RUN"}), flush=True)

if __name__ == "__main__":
    main()
