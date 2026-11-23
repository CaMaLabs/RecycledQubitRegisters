"""K194 full-circuit exact local predicate-sharing screen."""
import argparse
import json
from pathlib import Path

from ..autonomous.core import parse, sha, cost, prove
from ..autonomous.kickmix_trace import physical_lines
from ..autonomous.predicate_sharing import predicate_share
from .invsqrt_phase_fit import verify_against_campaign


def optimize(source, span, passes):
    lines = physical_lines(source.decode("utf-8"))
    changes = []
    for iteration in range(passes):
        changed = False
        i = 0
        while i < len(lines):
            if parse(lines[i]) is None:
                i += 1
                continue
            end = i
            while end < len(lines) and end - i < span and parse(lines[end]) is not None:
                end += 1
            gates = [parse(x) for x in lines[i:end]]
            proposal = predicate_share(gates, {}, iteration)
            if proposal is not None:
                proof = prove(gates, proposal.gates)
                if proof["status"] != "EXACT" or cost(proposal.gates) > cost(gates):
                    raise AssertionError("Unproved or more expensive rewrite")
                lines[i:end] = [g.text() for g in proposal.gates]
                changes.append({"pass": iteration, "line": i + 1,
                                "before": len(gates), "after": len(proposal.gates),
                                "proof": proof})
                changed = True
                i = max(0, i - span)
            else:
                i = end
        if not changed:
            break
    return "".join(lines).encode("utf-8"), changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path)
    p.add_argument("--span", type=int, default=64)
    p.add_argument("--passes", type=int, default=4)
    p.add_argument("--verifier-timeout", type=float, default=1800)
    a = p.parse_args()
    if not 3 <= a.span <= 256 or not 1 <= a.passes <= 20:
        p.error("span must be 3..256, passes 1..20")
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Source must be outside output directory")
    source = a.source.read_bytes()
    candidate, changes = optimize(source, a.span, a.passes)
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
            verify_against_campaign(path, report, a.campaign_db,
                                    a.out, a.verifier_timeout)
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
