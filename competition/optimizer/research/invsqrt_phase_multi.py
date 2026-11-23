"""K192 coordinated fine-rotation deletion screen; full-domain replay and optional official verification."""
import argparse
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path
import numpy as np

from .invsqrt_phase_fit import (
    MAX_X, TRANSCRIPTS, UNIT, circuit, load_backend, profile,
    signed_residual, simulate, verify_against_campaign,
)
from ..autonomous.core import Gate, TURN, sha
from ..autonomous.phase_margin import fit_phase, rotation_price


def render_many(parsed, delta, dropped):
    lines = parsed.lines.copy()
    for slot, ((op, gate), adjustment) in enumerate(zip(parsed.rotations.items(), delta)):
        line = parsed.source_lines[op]
        if slot in dropped:
            lines[line] = ""
        elif adjustment:
            lines[line] = Gate("Z_POW", gate.q, (gate.angle + adjustment * UNIT) % TURN).text()
    return "".join(lines).encode("utf-8")


def search(source, backend, max_drops, pool, seconds, max_trials):
    parsed = circuit(source, backend)
    target, tolerance = backend.invsqrt_reference()
    tolerance = tolerance.astype(np.int64)
    masks, residual = profile(backend, parsed, target)
    if np.any(np.abs(residual) > tolerance):
        raise ValueError("Baseline fails the full-domain model")
    count = len(parsed.rotations)
    rounding = count + 4
    margin0 = int((tolerance - np.abs(residual)).min())
    baseline_price = rotation_price(count, margin0 + rounding)
    angles = [round(Fraction(g.angle, UNIT)) for g in parsed.rotations.values()]
    eligible = sorted(
        (i for i, a in enumerate(angles) if 0 < a <= (1 << 35)),
        key=lambda i: angles[i],
    )[:pool]
    report = {
        "source_sha256": sha(source), "domain_size": MAX_X,
        "transcripts": list(TRANSCRIPTS), "baseline_margin_units": margin0,
        "baseline_fine_rotations": count, "trials": [],
        "candidate": None, "official_status": "NOT_RUN",
    }
    best = None
    for n in range(1, max_drops + 1):
        for slots in combinations(eligible, n):
            if len(report["trials"]) >= max_trials:
                break
            fixed = {i: -angles[i] for i in slots}
            fit = fit_phase(masks, residual, tolerance, count, fixed, seconds=seconds)
            remaining = count - n
            saving = (parsed.width * (baseline_price -
                rotation_price(remaining, fit.margin - rounding)))
            rec = {
                "dropped_slots": list(slots), "margin_units": int(fit.margin),
                "rounds": fit.rounds, "converged": bool(fit.converged),
                "modeled_cost_saving": float(saving) if np.isfinite(saving) else None,
            }
            report["trials"].append(rec)
            if not (fit.converged and np.isfinite(saving) and saving > 0):
                continue
            proposal = render_many(parsed, fit.delta, set(slots))
            replacement = circuit(proposal, backend)
            if len(replacement.rotations) != remaining:
                rec["rejection"] = "rotation_count_mismatch"
                continue
            replay_margin = min(int((tolerance - np.abs(signed_residual(
                simulate(backend, replacement, transcript), target))).min())
                for transcript in TRANSCRIPTS)
            replay_price = rotation_price(remaining, replay_margin - rounding)
            actual_saving = parsed.width * (baseline_price - replay_price)
            rec["replayed_margin_units"] = replay_margin
            rec["replayed_modeled_saving"] = float(actual_saving) if np.isfinite(actual_saving) else None
            if replay_margin <= rounding or not np.isfinite(actual_saving) or actual_saving <= 0:
                rec["rejection"] = "full_domain_replay_or_price"
                continue
            if best is None or actual_saving > best[0]:
                best = (actual_saving, proposal, rec)
        if len(report["trials"]) >= max_trials:
            break
    if best is None:
        return None, report
    _, candidate, rec = best
    report["candidate"] = {**rec, "sha256": sha(candidate)}
    return candidate, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--backend", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--campaign-db", type=Path)
    p.add_argument("--max-drops", type=int, default=2)
    p.add_argument("--pool", type=int, default=8)
    p.add_argument("--max-trials", type=int, default=36)
    p.add_argument("--seconds-per-fit", type=float, default=12)
    p.add_argument("--verifier-timeout", type=float, default=1800)
    a = p.parse_args()
    if not 1 <= a.max_drops <= 3 or not 1 <= a.pool <= 20 or a.max_trials < 1:
        p.error("Require 1<=max-drops<=3, 1<=pool<=20, max-trials>=1")
    if not 0 < a.seconds_per_fit <= 60:
        p.error("seconds-per-fit must be in (0,60]")
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Keep immutable source outside output directory")
    backend = load_backend(a.backend)
    source = a.source.read_bytes()
    candidate, report = search(source, backend, a.max_drops, a.pool,
                                a.seconds_per_fit, a.max_trials)
    report["backend_sha256"] = sha(a.backend.read_bytes())
    a.out.mkdir(parents=True, exist_ok=True)
    receipt = a.out / "report.json"
    if candidate is not None:
        path = a.out / (report["candidate"]["sha256"] + ".kmx")
        path.write_bytes(candidate)
        report["candidate"]["path"] = str(path.resolve())
        if a.campaign_db:
            receipt.write_text(json.dumps(report, indent=2) + "\n")
            verify_against_campaign(path, report, a.campaign_db,
                                    a.out, a.verifier_timeout)
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
