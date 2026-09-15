#!/usr/bin/env python3
"""Zero-QPU mechanism decomposition for the cube/PTP stratified control.

Reads the existing stratified-control receipt and asks *why* the public
N mod 3 == 2 trigger works better than the N mod 3 == 1 control.

For semiprimes p*q with p,q != 3:
- N mod 3 == 2 forces factor residues {1,2}, hence 3 | lambda(N).
- N mod 3 == 1 allows hidden factor residues {1,1} or {2,2}; only the first
  forces 3 | lambda(N).
- For b=a^3 mod N, ord_N(b)=r/gcd(r,3), so the order is reduced iff 3|r.

This script uses p,q,lambda,r only as validation labels after the public policy
has already been fixed. It verifies the exact mechanism and reports the hidden
factor-residue decomposition of the trigger/control contrast.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median

DEFAULT_RECEIPT = Path(
    "results/dark_star_ptp/dark_star_shor_cube_stratified_control_audit.json"
)
DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_cube_mechanism_decomposition_audit.json"
)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Exact two-sided Fisher p-value for a 2x2 table, stdlib only."""
    r1, r2 = a + b, c + d
    c1 = a + c
    n = r1 + r2
    lo = max(0, c1 - r2)
    hi = min(r1, c1)

    def prob(x: int) -> float:
        return (math.comb(c1, x) * math.comb(n - c1, r1 - x)) / math.comb(n, r1)

    p_obs = prob(a)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-18))


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"rows": 0}
    reduced = [r for r in rows if r["transformed_order_validation_only"] < r["baseline_order_validation_only"]]
    ratios = [float(r["unconditional_phase_round_ratio"]) for r in rows if r.get("unconditional_phase_round_ratio") is not None]
    return {
        "rows": len(rows),
        "distinct_N": len({r["N"] for r in rows}),
        "lambda_div_3_fraction": sum(int(r["lambda_div_3_validation_only"]) for r in rows) / len(rows),
        "r_div_3_fraction": sum(int(r["r_div_3_validation_only"]) for r in rows) / len(rows),
        "order_reduced_rows": len(reduced),
        "order_reduced_fraction": len(reduced) / len(rows),
        "mean_phase_round_ratio": mean(ratios) if ratios else None,
        "median_phase_round_ratio": median(ratios) if ratios else None,
        "fraction_phase_work_improved": sum(x < 1.0 for x in ratios) / len(ratios) if ratios else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanism decomposition of cube/PTP stratified control")
    ap.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tol", type=float, default=1e-12)
    args = ap.parse_args()

    if not args.receipt.exists():
        raise SystemExit(f"missing receipt: {args.receipt}")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))

    eligible = []
    violations = []
    for row in receipt.get("rows", []):
        if not row.get("baseline_factor_success_validation_only"):
            continue
        if not row.get("paired_quantum_guardrail_pass"):
            continue

        p = int(row["p_validation_only"])
        q = int(row["q_validation_only"])
        n = int(row["N"])
        r0 = int(row["baseline_order_validation_only"])
        r1 = int(row["transformed_order_validation_only"])
        lam = math.lcm(p - 1, q - 1)
        factor_residues = tuple(sorted((p % 3, q % 3)))
        expected_r1 = r0 // math.gcd(r0, 3)
        ratio = row.get("unconditional_phase_round_ratio")

        item = {
            **row,
            "factor_residues_mod_3_validation_only": list(factor_residues),
            "lambda_validation_only_recomputed": lam,
            "lambda_div_3_validation_only": lam % 3 == 0,
            "r_div_3_validation_only": r0 % 3 == 0,
        }
        eligible.append(item)

        if r1 != expected_r1:
            violations.append({"N": n, "base": row["base"], "type": "order_identity"})
        if n % 3 == 2 and factor_residues != (1, 2):
            violations.append({"N": n, "base": row["base"], "type": "trigger_factor_residue_pattern", "got": factor_residues})
        if n % 3 == 2 and lam % 3 != 0:
            violations.append({"N": n, "base": row["base"], "type": "trigger_lambda_guarantee"})
        if lam % 3 != 0 and r0 % 3 == 0:
            violations.append({"N": n, "base": row["base"], "type": "order_not_dividing_lambda"})
        if r0 % 3 != 0:
            if r1 != r0:
                violations.append({"N": n, "base": row["base"], "type": "cube_changed_order_without_3_dividing_r"})
            if ratio is not None and abs(float(ratio) - 1.0) > args.tol:
                violations.append({
                    "N": n,
                    "base": row["base"],
                    "type": "same_order_expected_same_exact_phase_work",
                    "ratio": ratio,
                })

    trigger = [r for r in eligible if int(r["N"]) % 3 == 2]
    control = [r for r in eligible if int(r["N"]) % 3 == 1]
    control_11 = [r for r in control if tuple(r["factor_residues_mod_3_validation_only"]) == (1, 1)]
    control_22 = [r for r in control if tuple(r["factor_residues_mod_3_validation_only"]) == (2, 2)]
    r3 = [r for r in eligible if r["r_div_3_validation_only"]]
    rnot3 = [r for r in eligible if not r["r_div_3_validation_only"]]

    ta = sum(r["transformed_order_validation_only"] < r["baseline_order_validation_only"] for r in trigger)
    tb = len(trigger) - ta
    ca = sum(r["transformed_order_validation_only"] < r["baseline_order_validation_only"] for r in control)
    cb = len(control) - ca

    trigger_rate = ta / len(trigger) if trigger else None
    control_rate = ca / len(control) if control else None
    risk_ratio = (trigger_rate / control_rate) if trigger_rate is not None and control_rate not in (None, 0) else None

    result = {
        "experiment": "dark_star_shor_cube_mechanism_decomposition_audit_v1",
        "zero_qpu": True,
        "receipt": str(args.receipt),
        "public_mechanism": {
            "trigger": "N mod 3 == 2 forces hidden factor residues {1,2}, therefore 3 divides lambda(N)",
            "cube_identity": "ord_N(a^3)=r/gcd(r,3)",
            "resource_consequence": "under this exact staged model, if 3 does not divide r then cubing preserves r and the phase-work expectation is unchanged; if 3 divides r, cubing reduces r by exactly 3",
        },
        "eligible_rows": len(eligible),
        "trigger": summarize(trigger),
        "control": summarize(control),
        "control_hidden_factor_residue_11": summarize(control_11),
        "control_hidden_factor_residue_22": summarize(control_22),
        "all_rows_with_3_dividing_r": summarize(r3),
        "all_rows_with_3_not_dividing_r": summarize(rnot3),
        "trigger_vs_control_order_reduction": {
            "table": [[ta, tb], [ca, cb]],
            "trigger_rate": trigger_rate,
            "control_rate": control_rate,
            "absolute_difference": (trigger_rate - control_rate) if trigger_rate is not None and control_rate is not None else None,
            "risk_ratio": risk_ratio,
            "fisher_exact_two_sided_p_row_level": fisher_two_sided(ta, tb, ca, cb) if trigger and control else None,
            "independence_caveat": "Fisher p treats base rows as independent; multiple bases share N, so use it as descriptive support rather than the sole inferential claim.",
        },
        "theorem_violations": violations,
        "interpretation": (
            "The public PTP trigger is not the source of the cube identity; it is a useful selector. "
            "It deterministically enriches for 3|lambda(N), which in turn greatly increases the chance that a chosen base has 3|r and therefore benefits from a->a^3."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== CUBE/PTP MECHANISM DECOMPOSITION =====")
    print(json.dumps({
        "trigger": result["trigger"],
        "control": result["control"],
        "control_hidden_factor_residue_11": result["control_hidden_factor_residue_11"],
        "control_hidden_factor_residue_22": result["control_hidden_factor_residue_22"],
        "all_rows_with_3_dividing_r": result["all_rows_with_3_dividing_r"],
        "all_rows_with_3_not_dividing_r": result["all_rows_with_3_not_dividing_r"],
        "trigger_vs_control_order_reduction": result["trigger_vs_control_order_reduction"],
    }, indent=2))
    print("\n===== OVERALL =====")
    print(json.dumps({
        "pass": not violations,
        "zero_qpu": True,
        "theorem_violations": violations,
        "saved": str(args.out.resolve()),
    }, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
