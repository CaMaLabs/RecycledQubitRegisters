"""K198: heterogeneous, exact-proved local structural synthesis campaign.

Unlike K197, tries independent arithmetic, affine, factoring, workspace,
phase and SMT algorithms on bounded physical-wire windows. A candidate is
written only after exact full-basis proof of the changed window.
"""
import argparse
import json
from pathlib import Path
import random
import time
from .invsqrt_historical_supervisor import PIN, historical, save
from .invsqrt_phase_fit import verify_against_campaign
from ..autonomous.core import parse, prove, cost, sha
from ..autonomous.passes import PLUGINS

METHODS = ("arithmetic", "workspace_reuse", "factor", "affine",
           "phase_predicate", "phase_function", "parity_spectrum",
           "cancel", "smt")
BUDGET = {"span": 32, "seconds": 0.4, "depth": 4, "max_states": 2000}


def windows(lines, span, stride, max_wires):
    """Emit only contiguous fully parsed regions; never cross syntax barriers."""
    parsed = [parse(line) for line in lines]
    start = 0
    while start < len(lines):
        while start < len(lines) and parsed[start] is None:
            start += 1
        end = start
        while end < len(lines) and parsed[end] is not None:
            end += 1
        if end - start >= 2:
            for i in range(start, end - 1, stride):
                wires = set()
                j = i
                while j < min(end, i + span):
                    new = wires | set(parsed[j].q)
                    if len(new) > max_wires:
                        break
                    wires = new
                    j += 1
                if j - i >= 2:
                    yield i, j, parsed[i:j]
        start = end + 1


def transform(raw, methods, span, stride, max_wires, max_windows, seed):
    lines = raw.decode("utf-8").splitlines(keepends=True)
    count = 0
    eligibility = {name: 0 for name in methods}
    for i, j, gates in windows(lines, span, stride, max_wires):
        count += 1
        if count > max_windows:
            break
        for name in methods:
            eligibility[name] += 1
            try:
                proposal = PLUGINS[name](gates, dict(BUDGET, span=span), seed + i)
                if proposal is None or cost(proposal.gates) >= cost(gates):
                    continue
                evidence = prove(gates, proposal.gates, max_wires)
                if evidence["status"] != "EXACT":
                    continue
                changed = lines[:i] + [g.text() for g in proposal.gates] + lines[j:]
                child = "".join(changed).encode("utf-8")
                return child, {"status": "EXACT", "method": name,
                               "region": [i, j], "proof": evidence,
                               "before_cost": cost(gates), "after_cost": cost(proposal.gates),
                               "detail": proposal.detail, "windows": count,
                               "eligible": eligibility}
            except (ValueError, KeyError, IndexError, TypeError, OverflowError):
                continue
    return None, {"status": "NO_CHANGE", "windows": count, "eligible": eligibility}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--hours", type=float, default=4)
    p.add_argument("--max-parents", type=int, default=100)
    p.add_argument("--max-windows", type=int, default=5000)
    p.add_argument("--span", type=int, default=32)
    p.add_argument("--stride", type=int, default=8)
    p.add_argument("--max-wires", type=int, default=8)
    p.add_argument("--verifier-timeout", type=float, default=600)
    p.add_argument("--methods", default=",".join(METHODS))
    args = p.parse_args()
    if sha(args.source.read_bytes()) != PIN:
        p.error("Baseline digest mismatch")
    if not 0 < args.hours <= 24 or not 1 <= args.max_wires <= 10:
        p.error("Invalid bounds")
    methods = tuple(x.strip() for x in args.methods.split(","))
    if any(x not in METHODS for x in methods):
        p.error("Unknown method")
    args.out.mkdir(parents=True, exist_ok=True)
    statefile = args.out / "state.json"
    state = json.loads(statefile.read_text()) if statefile.exists() else {
        "source_sha256": PIN, "completed": {}, "verified_winner": None}
    if state["source_sha256"] != PIN:
        p.error("Resume digest mismatch")
    parents = [{"sha": PIN, "path": str(args.source.resolve())}]
    parents += historical(args.campaign_db, args.max_parents)
    deadline = time.monotonic() + args.hours * 3600
    for parent in parents:
        if time.monotonic() >= deadline or state["verified_winner"]:
            break
        digest = parent["sha"]
        if digest in state["completed"]:
            continue
        start = time.monotonic()
        outcome = {"parent": digest}
        try:
            path = Path(parent["path"])
            if not path.is_file() or sha(path.read_bytes()) != digest:
                outcome["status"] = "MISSING_OR_DIGEST_MISMATCH"
            else:
                child, report = transform(path.read_bytes(), methods, args.span,
                    args.stride, args.max_wires, args.max_windows, int(digest[:8], 16))
                outcome.update(report)
                if child is not None:
                    childsha = sha(child)
                    folder = args.out / "candidates" / childsha
                    folder.mkdir(parents=True, exist_ok=True)
                    candidate = folder / (childsha + ".kmx")
                    candidate.write_bytes(child)
                    (folder / "local_proof.json").write_text(json.dumps(report, indent=2))
                    outcome["candidate_sha256"] = childsha
                    outcome["candidate_path"] = str(candidate)
                    if deadline - time.monotonic() > 2 * args.verifier_timeout + 10:
                        receipt = {"source_sha256": PIN, "candidate": {"sha256": childsha}}
                        verify_against_campaign(candidate, receipt, args.campaign_db,
                                                folder, args.verifier_timeout)
                        outcome["official_status"] = receipt.get("official_status")
                        outcome["verified_improvement"] = receipt.get("verified_improvement", False)
                        (folder / "official_receipt.json").write_text(json.dumps(receipt, indent=2))
                        if outcome["verified_improvement"]:
                            state["verified_winner"] = outcome
                    else:
                        outcome["official_status"] = "DEFERRED"
        except Exception as exc:
            outcome = {"parent": digest, "status": "ERROR", "reason": repr(exc)}
        outcome["seconds"] = round(time.monotonic() - start, 2)
        state["completed"][digest] = outcome
        save(statefile, state)
        print("K198_RESULT", json.dumps(outcome), flush=True)
    print("K198_SUMMARY", json.dumps({"completed": len(state["completed"]),
          "winner": state["verified_winner"]}), flush=True)


if __name__ == "__main__":
    main()
