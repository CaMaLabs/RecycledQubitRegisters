"""K195 bounded overlapping symbolic predicate scan and official verification."""
import argparse
import json
from pathlib import Path
from ..autonomous.core import parse, sha, cost, prove
from ..autonomous.symbolic_predicates import symbolic_predicate_share
from ..autonomous.kickmix_trace import physical_lines
from .invsqrt_phase_fit import verify_against_campaign

SINGLE = {"Z_POW", "Z", "S", "S_DAG", "T", "T_DAG"}


def optimize(source, span, stride, passes, max_wires):
    lines = physical_lines(source.decode("utf-8"))
    changes = []
    for iteration in range(passes):
        modified = False
        i = 0
        while i < len(lines):
            end = min(len(lines), i + span)
            segment = [parse(x) for x in lines[i:end]]
            if (all(g is not None for g in segment)
                    and sum(g.op in SINGLE for g in segment) >= 2
                    and len({w for g in segment for w in g.q}) <= max_wires):
                proposal = symbolic_predicate_share(
                    segment, {"max_wires": max_wires}, iteration)
                if proposal:
                    proof = prove(segment, proposal.gates, max_wires=max_wires)
                    if proof["status"] != "EXACT" or cost(proposal.gates) > cost(segment):
                        raise AssertionError("Unproved symbolic rewrite")
                    lines[i:end] = [g.text() for g in proposal.gates]
                    changes.append({"pass": iteration, "start_line": i + 1,
                                    "removed": len(segment)-len(proposal.gates),
                                    "proof": proof})
                    modified = True
                    i = max(0, i - stride)
                    continue
            i += stride
        if not modified:
            break
    return "".join(lines).encode("utf-8"), changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path)
    p.add_argument("--span", type=int, default=64)
    p.add_argument("--stride", type=int, default=16)
    p.add_argument("--passes", type=int, default=3)
    p.add_argument("--max-wires", type=int, default=10)
    p.add_argument("--verifier-timeout", type=float, default=1800)
    a = p.parse_args()
    if not 2 <= a.span <= 256 or not 1 <= a.stride <= a.span or not 1 <= a.passes <= 20 or not 1 <= a.max_wires <= 10:
        p.error("Invalid scan limits")
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Source must not be inside output directory")
    source = a.source.read_bytes()
    candidate, changes = optimize(source, a.span, a.stride, a.passes, a.max_wires)
    report = {"source_sha256": sha(source), "rewrites": len(changes),
              "changes": changes, "candidate": None, "official_status": "NOT_RUN"}
    a.out.mkdir(parents=True, exist_ok=True)
    receipt = a.out / "report.json"
    if changes and sha(candidate) != sha(source):
        path = a.out / (sha(candidate) + ".kmx")
        path.write_bytes(candidate)
        report["candidate"] = {"sha256": sha(candidate), "path": str(path.resolve())}
        if a.campaign_db:
            receipt.write_text(json.dumps(report, indent=2) + "\n")
            verify_against_campaign(path, report, a.campaign_db, a.out, a.verifier_timeout)
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
