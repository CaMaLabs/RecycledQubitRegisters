"""K193: jointly refit all fine rotations and test quantized angle grids.

This is a modeled full-domain screen. Only the official verifier can establish
a score improvement. The source circuit and campaign database remain untouched.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from .invsqrt_phase_fit import (
    TRANSCRIPTS, UNIT, circuit, load_backend, profile, render,
    signed_residual, simulate, verify_against_campaign,
)
from ..autonomous.core import sha
from ..autonomous.phase_margin import fit_phase, rotation_price, angle_shift


def screen(source, backend, seconds, grid_bits):
    parsed = circuit(source, backend)
    target, tolerance = backend.invsqrt_reference()
    tolerance = tolerance.astype(np.int64)
    masks, residual = profile(backend, parsed, target)
    count = len(parsed.rotations)
    rounding = count + 4
    original_margin = int((tolerance - np.abs(residual)).min())
    if original_margin <= rounding:
        raise ValueError("Baseline has insufficient modeled margin")
    base_price = rotation_price(count, original_margin + rounding)
    fit = fit_phase(masks, residual, tolerance, count, seconds=seconds)
    records = []
    best = None
    # Each grid constrains all angle adjustments to a common lattice in units
    # of 2^-64 turns. Grid 0 is the unrestricted joint refit.
    for bits in grid_bits:
        step = 1 << bits
        delta = tuple(int(round(v / step) * step) for v in fit.delta)
        predicted = int((tolerance - np.abs(residual + angle_shift(masks, delta))).min())
        rec = {"grid_bits": bits, "grid_step_units": step,
               "predicted_margin_units": predicted,
               "fit_rounds": fit.rounds, "fit_converged": fit.converged}
        records.append(rec)
        if predicted <= rounding:
            rec["rejection"] = "modeled_error_limit"
            continue
        candidate = render(parsed, delta, None, None)
        if sha(candidate) == sha(source):
            rec["rejection"] = "unchanged_circuit"
            continue
        replacement = circuit(candidate, backend)
        if len(replacement.rotations) != count:
            rec["rejection"] = "rotation_class_changed"
            continue
        replay_margin = min(
            int((tolerance - np.abs(signed_residual(
                simulate(backend, replacement, transcript), target))).min())
            for transcript in TRANSCRIPTS
        )
        rec["replayed_margin_units"] = replay_margin
        if replay_margin <= rounding:
            rec["rejection"] = "full_domain_replay_failed"
            continue
        new_price = rotation_price(count, replay_margin - rounding)
        saving = parsed.width * (base_price - new_price)
        rec["modeled_cost_saving"] = float(saving)
        if not np.isfinite(saving) or saving <= 0:
            rec["rejection"] = "no_modeled_cost_improvement"
            continue
        if best is None or saving > best[0]:
            best = saving, candidate, rec
    report = {
        "source_sha256": sha(source),
        "baseline_margin_units": original_margin,
        "baseline_fine_rotations": count,
        "joint_fit_margin_units": fit.margin,
        "joint_fit_converged": fit.converged,
        "trials": records, "candidate": None, "official_status": "NOT_RUN",
    }
    if best is None:
        return None, report
    _, candidate, record = best
    report["candidate"] = {**record, "sha256": sha(candidate)}
    return candidate, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--backend", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path)
    p.add_argument("--seconds-per-fit", type=float, default=45)
    p.add_argument("--grid-bits", type=int, nargs="+", default=[0, 4, 8, 12, 16, 20])
    p.add_argument("--verifier-timeout", type=float, default=1800)
    a = p.parse_args()
    if not 0 < a.seconds_per_fit <= 300 or any(not 0 <= b <= 35 for b in a.grid_bits):
        p.error("Fit seconds must be in (0,300], grid bits in [0,35]")
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Output must not contain immutable source")
    backend = load_backend(a.backend)
    source = a.source.read_bytes()
    candidate, report = screen(source, backend, a.seconds_per_fit, a.grid_bits)
    report["backend_sha256"] = sha(a.backend.read_bytes())
    a.out.mkdir(parents=True, exist_ok=True)
    receipt = a.out / "report.json"
    if candidate is not None:
        path = a.out / (report["candidate"]["sha256"] + ".kmx")
        path.write_bytes(candidate)
        report["candidate"]["path"] = str(path.resolve())
        if a.campaign_db:
            receipt.write_text(json.dumps(report, indent=2) + "\n")
            verify_against_campaign(path, report, a.campaign_db, a.out,
                                    a.verifier_timeout)
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
