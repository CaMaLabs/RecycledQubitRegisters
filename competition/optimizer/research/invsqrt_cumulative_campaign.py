"""K199 cumulative exact local rewrites with durable checkpoints.

All accepted transformations are exact on their full local wire basis, and
strictly reduce the lexicographic local cost. Official validation is separate:
an official rejection never deletes an exact local improvement.
"""
import argparse
import json
from pathlib import Path
import time

from .invsqrt_historical_supervisor import PIN, save
from .invsqrt_phase_fit import verify_against_campaign
from ..autonomous.core import parse, prove, cost, sha
from ..autonomous.passes import PLUGINS

METHODS = ("arithmetic", "workspace_reuse", "factor", "affine",
           "phase_predicate", "phase_function", "cancel")
BUDGET = {"span": 32, "seconds": 0.25, "depth": 4, "max_states": 500}


def regions(lines, span, stride, max_wires):
    parsed = [parse(x) for x in lines]
    i = 0
    while i < len(lines):
        if parsed[i] is None:
            i += 1
            continue
        end = i
        while end < len(lines) and parsed[end] is not None:
            end += 1
        for start in range(i, end - 1, stride):
            wires = set()
            stop = start
            while stop < min(end, start + span):
                nxt = wires | set(parsed[stop].q)
                if len(nxt) > max_wires:
                    break
                wires = nxt
                stop += 1
            if stop - start >= 2:
                yield start, stop, parsed[start:stop]
        i = end


def find_rewrite(lines, methods, span, stride, max_wires, max_windows, deadline, seed):
    scanned = 0
    for start, stop, gates in regions(lines, span, stride, max_wires):
        if time.monotonic() >= deadline or scanned >= max_windows:
            break
        scanned += 1
        for method in methods:
            if time.monotonic() >= deadline:
                break
            try:
                proposal = PLUGINS[method](gates, dict(BUDGET, span=span), seed + start)
                if proposal is None or cost(proposal.gates) >= cost(gates):
                    continue
                proof = prove(gates, proposal.gates, max_wires)
                if proof["status"] != "EXACT":
                    continue
                replacement = [g.text() for g in proposal.gates]
                if replacement == lines[start:stop]:
                    continue
                return (lines[:start] + replacement + lines[stop:],
                        {"method": method, "region": [start, stop],
                         "before_cost": cost(gates), "after_cost": cost(proposal.gates),
                         "proof": proof, "detail": proposal.detail,
                         "windows_scanned": scanned})
            except (ValueError, KeyError, IndexError, TypeError, OverflowError):
                continue
    return None, {"windows_scanned": scanned}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--hours", type=float, default=4)
    p.add_argument("--max-rewrites", type=int, default=500)
    p.add_argument("--max-windows", type=int, default=5000)
    p.add_argument("--span", type=int, default=32)
    p.add_argument("--stride", type=int, default=8)
    p.add_argument("--max-wires", type=int, default=8)
    p.add_argument("--verify-every", type=int, default=20)
    p.add_argument("--verifier-timeout", type=float, default=600)
    p.add_argument("--methods", default=",".join(METHODS))
    a = p.parse_args()
    if not 0 < a.hours <= 24 or a.max_rewrites < 1 or a.verify_every < 1:
        p.error("Invalid campaign limits")
    if not 2 <= a.max_wires <= 10 or a.span < 2 or a.stride < 1 or a.max_windows < 1:
        p.error("Invalid window limits")
    methods = tuple(x.strip() for x in a.methods.split(","))
    if not methods or any(x not in METHODS for x in methods):
        p.error("Unsupported method")
    source = a.source.read_bytes()
    if sha(source) != PIN:
        p.error("Source digest mismatch")
    a.out.mkdir(parents=True, exist_ok=True)
    statefile = a.out / "state.json"
    checkpoint = a.out / "current.kmx"
    if statefile.exists():
        state = json.loads(statefile.read_text())
        if state["source_sha256"] != PIN or not checkpoint.is_file():
            p.error("Invalid resume checkpoint")
        raw = checkpoint.read_bytes()
        if sha(raw) != state["current_sha256"]:
            p.error("Checkpoint digest mismatch")
    else:
        raw = source
        state = {"source_sha256": PIN, "current_sha256": PIN,
                 "rewrites": [], "official_checks": [], "best_verified": None}
        checkpoint.write_bytes(raw)
        save(statefile, state)
    lines = raw.decode("utf-8").splitlines(keepends=True)
    deadline = time.monotonic() + a.hours * 3600
    # A fixed stride can miss opportunities; vary the offset after each pass.
    # Each rewrite restarts the search on the cumulative circuit.
    stalled = 0
    while len(state["rewrites"]) < a.max_rewrites and time.monotonic() < deadline:
        sequence = len(state["rewrites"])
        offset = stalled % a.stride
        prefix = lines[:offset]
        candidate, detail = find_rewrite(lines[offset:], methods, a.span,
            a.stride, a.max_wires, a.max_windows, deadline, sequence + stalled)
        if candidate is None:
            stalled += 1
            print("K199_SCAN", json.dumps({"offset": offset, **detail}), flush=True)
            if stalled >= a.stride:
                break
            continue
        stalled = 0
        updated = prefix + candidate
        child = "".join(updated).encode("utf-8")
        digest = sha(child)
        # Write immutable candidate and proof before switching the active checkpoint.
        folder = a.out / "candidates" / digest
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (digest + ".kmx")
        path.write_bytes(child)
        (folder / "local_proof.json").write_text(json.dumps(detail, indent=2))
        event = {"index": sequence + 1, "sha256": digest,
                 "parent_sha256": state["current_sha256"],
                 "path": str(path), **detail}
        # Atomic checkpoint swap, followed by state persistence.
        tmp = checkpoint.with_suffix(".tmp")
        tmp.write_bytes(child)
        tmp.replace(checkpoint)
        state["current_sha256"] = digest
        state["rewrites"].append(event)
        save(statefile, state)
        lines = updated
        print("K199_REWRITE", json.dumps(event), flush=True)
        if len(state["rewrites"]) % a.verify_every == 0:
            if deadline - time.monotonic() >= a.verifier_timeout * 2 + 10:
                receipt = {"source_sha256": PIN, "candidate": {"sha256": digest}}
                try:
                    verify_against_campaign(path, receipt, a.campaign_db,
                                            folder, a.verifier_timeout)
                except Exception as exc:
                    receipt["official_status"] = "ERROR"
                    receipt["error"] = repr(exc)
                (folder / "official_receipt.json").write_text(json.dumps(receipt, indent=2))
                state["official_checks"].append(receipt)
                if receipt.get("verified_improvement"):
                    state["best_verified"] = event
                save(statefile, state)
                print("K199_OFFICIAL", json.dumps(receipt), flush=True)
    print("K199_SUMMARY", json.dumps({"rewrites": len(state["rewrites"]),
          "current_sha256": state["current_sha256"],
          "official_checks": len(state["official_checks"]),
          "best_verified": state["best_verified"]}), flush=True)


if __name__ == "__main__":
    main()
