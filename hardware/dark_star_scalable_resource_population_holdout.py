#!/usr/bin/env python3
"""Fresh population holdout for Dark Star scalable arithmetic resources.

Preregistered in:
docs/DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_PREREG.md

This is a zero-QPU resource audit. Population selection uses only public N,
ell, deterministic salts, and a fixed public base pool. Hidden factors/orders
are used only after selection for validation and exact ideal-QPE scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import dark_star_ptp_shor_audit as dsbase
import dark_star_recycled_scalable_arithmetic_audit as model


REV = "2026-10-14-dark-star-scalable-resource-population-holdout-v1"
ELLS = (3, 5, 7)
BASE_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
SELECTION_SALT = "QRR-scalable-resource-population-holdout-v1-20261014"
BASE_SALT = "QRR-scalable-resource-population-base-v1-20261014"
DEFAULT_OUT = Path(
    "results/dark_star_ptp/"
    "dark_star_scalable_resource_population_holdout.json"
)


def hash_int(salt: str, *parts) -> int:
    msg = "|".join([salt, *(str(x) for x in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(msg).digest(), "big")


def semiprime_pairs(
    *, prime_min: int, n_min: int, n_max: int
) -> list[tuple[int, int]]:
    primes = [p for p in dsbase.sieve_primes(n_max) if p >= prime_min]
    out = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n > n_max:
                break
            if n >= n_min:
                out.append((p, q))
    return out


def choose_public_base(n: int, ell: int) -> int:
    start = hash_int(BASE_SALT, "base", ell, n) % len(BASE_POOL)
    for offset in range(len(BASE_POOL)):
        a = BASE_POOL[(start + offset) % len(BASE_POOL)]
        if math.gcd(a, n) == 1:
            return int(a)
    raise AssertionError(f"N={n}: no coprime base in fixed pool")


def select_balanced(
    pairs: list[tuple[int, int]], ell: int, per_group: int
) -> list[tuple[str, int, int]]:
    groups = {"trigger": [], "control": []}
    for p, q in pairs:
        n = p * q
        if n % ell == 0:
            continue
        group = "control" if n % ell == 1 else "trigger"
        groups[group].append((p, q))

    selected = []
    for group in ("trigger", "control"):
        ranked = sorted(
            groups[group],
            key=lambda pq: (
                hash_int(SELECTION_SALT, ell, group, pq[0] * pq[1]),
                pq[0] * pq[1],
            ),
        )
        if len(ranked) < per_group:
            raise RuntimeError(
                f"ell={ell} group={group}: requested {per_group}, "
                f"only {len(ranked)} available"
            )
        selected.extend((group, p, q) for p, q in ranked[:per_group])
    return selected


def factor_pair(w: dict):
    fs = w.get("factors") or []
    return tuple(fs[0]) if fs else None


def make_row(
    group: str,
    p: int,
    q: int,
    ell: int,
    *,
    start_bits: int,
    step_bits: int,
    shots_per_stage: int,
) -> dict:
    n = int(p * q)
    a = choose_public_base(n, ell)
    b = pow(a, ell, n)
    lam = math.lcm(p - 1, q - 1)

    r0 = model.multiplicative_order_from_lambda(a, n, lam)
    r1 = model.multiplicative_order_from_lambda(b, n, lam)
    expected_r1 = r0 // math.gcd(r0, ell)

    w0 = model.factor_witness(a, r0, n)
    w1 = model.factor_witness(b, r1, n)
    s0 = model.power2_chain_shortcut(a, n)
    s1 = model.power2_chain_shortcut(b, n)

    theorem_ok = r1 == expected_r1
    witness_ok = True
    if w0["factor_success"]:
        witness_ok = (
            w1["factor_success"]
            and w0.get("x") == w1.get("x")
            and factor_pair(w0) == factor_pair(w1)
        )

    eligible = bool(
        theorem_ok
        and witness_ok
        and w0["factor_success"]
        and w1["factor_success"]
        and not s0["factor_found"]
        and not s1["factor_found"]
    )

    row = {
        "N": n,
        "ell": int(ell),
        "group": group,
        "N_mod_ell": int(n % ell),
        "p_validation_only": int(p),
        "q_validation_only": int(q),
        "base": a,
        "transformed_base": int(b),
        "lambda_validation_only": int(lam),
        "baseline_order_validation_only": int(r0),
        "transformed_order_validation_only": int(r1),
        "expected_transformed_order_validation_only": int(expected_r1),
        "order_identity_pass": bool(theorem_ok),
        "witness_preservation_pass": bool(witness_ok),
        "baseline_factor_capable": bool(w0["factor_success"]),
        "transformed_factor_capable": bool(w1["factor_success"]),
        "baseline_classical_shortcut": s0,
        "transformed_classical_shortcut": s1,
        "eligible_quantum_row": eligible,
        "order_reduced": bool(r1 < r0),
        "order_reduction_factor": float(r0 / r1),
    }

    if not eligible:
        return row

    cache = {}
    baseline = model.evaluate_policy(
        n=n,
        base=a,
        order=r0,
        kind="recycled",
        start_bits=start_bits,
        step_bits=step_bits,
        shots_per_stage=shots_per_stage,
        modmul_cache=cache,
    )
    transformed = model.evaluate_policy(
        n=n,
        base=b,
        order=r1,
        kind="recycled",
        start_bits=start_bits,
        step_bits=step_bits,
        shots_per_stage=shots_per_stage,
        modmul_cache=cache,
    )

    bccx = float(
        baseline["expected_resources_per_attempted_session"].get("ccx", 0.0)
    )
    tccx = float(
        transformed["expected_resources_per_attempted_session"].get("ccx", 0.0)
    )
    brounds = float(baseline["expected_phase_rounds_per_attempted_session"])
    trounds = float(transformed["expected_phase_rounds_per_attempted_session"])

    width = model.arithmetic_width(n)
    cap = 2 * n.bit_length()
    baseline_wide_peak = width["arithmetic_qubits_excluding_phase"] + cap
    transformed_recycled_peak = width["recycled_logical_qubits"]

    ccx_ratio = tccx / bccx if bccx else None
    phase_ratio = trounds / brounds if brounds else None
    per_round_ratio = (
        ccx_ratio / phase_ratio
        if ccx_ratio is not None and phase_ratio not in (None, 0)
        else None
    )

    row["resource"] = {
        "baseline_expected_ccx": bccx,
        "transformed_expected_ccx": tccx,
        "expected_ccx_ratio": ccx_ratio,
        "baseline_expected_phase_rounds": brounds,
        "transformed_expected_phase_rounds": trounds,
        "expected_phase_round_ratio": phase_ratio,
        "ccx_per_phase_round_ratio": per_round_ratio,
        "baseline_success_probability_by_cap": float(
            baseline["success_probability_by_cap"]
        ),
        "transformed_success_probability_by_cap": float(
            transformed["success_probability_by_cap"]
        ),
        "baseline_wide_peak_logical_qubits": int(baseline_wide_peak),
        "transformed_recycled_peak_logical_qubits": int(
            transformed_recycled_peak
        ),
        "combined_peak_width_ratio": float(
            transformed_recycled_peak / baseline_wide_peak
        ),
        "combined_peak_width_reduction": float(
            1.0 - transformed_recycled_peak / baseline_wide_peak
        ),
    }
    return row


def median_or_none(vals):
    vals = [float(x) for x in vals if x is not None]
    return statistics.median(vals) if vals else None


def mean_or_none(vals):
    vals = [float(x) for x in vals if x is not None]
    return statistics.mean(vals) if vals else None


def summarize_group(rows: list[dict]) -> dict:
    eligible = [r for r in rows if r["eligible_quantum_row"]]
    resource = [r for r in eligible if "resource" in r]

    def frac(k: int, n: int):
        return k / n if n else None

    sum_b_ccx = sum(r["resource"]["baseline_expected_ccx"] for r in resource)
    sum_t_ccx = sum(
        r["resource"]["transformed_expected_ccx"] for r in resource
    )
    sum_b_phase = sum(
        r["resource"]["baseline_expected_phase_rounds"] for r in resource
    )
    sum_t_phase = sum(
        r["resource"]["transformed_expected_phase_rounds"] for r in resource
    )

    ccx_ratios = [r["resource"]["expected_ccx_ratio"] for r in resource]
    phase_ratios = [
        r["resource"]["expected_phase_round_ratio"] for r in resource
    ]
    per_round = [
        r["resource"]["ccx_per_phase_round_ratio"] for r in resource
    ]

    return {
        "selected_rows": len(rows),
        "eligible_rows": len(eligible),
        "eligibility_fraction": frac(len(eligible), len(rows)),
        "eligible_order_reduced_rows": sum(r["order_reduced"] for r in eligible),
        "eligible_order_reduced_fraction": frac(
            sum(r["order_reduced"] for r in eligible), len(eligible)
        ),
        "median_order_reduction_factor": median_or_none(
            [r["order_reduction_factor"] for r in eligible]
        ),
        "aggregate_expected_ccx_ratio_sum_T_over_sum_B": (
            sum_t_ccx / sum_b_ccx if sum_b_ccx else None
        ),
        "aggregate_expected_ccx_reduction": (
            1.0 - sum_t_ccx / sum_b_ccx if sum_b_ccx else None
        ),
        "median_row_expected_ccx_ratio": median_or_none(ccx_ratios),
        "mean_row_expected_ccx_ratio": mean_or_none(ccx_ratios),
        "eligible_rows_expected_ccx_improved": sum(x < 1.0 - 1e-12 for x in ccx_ratios),
        "eligible_rows_expected_ccx_tied": sum(abs(x - 1.0) <= 1e-12 for x in ccx_ratios),
        "eligible_rows_expected_ccx_worsened": sum(x > 1.0 + 1e-12 for x in ccx_ratios),
        "fraction_eligible_rows_expected_ccx_tied": frac(
            sum(abs(x - 1.0) <= 1e-12 for x in ccx_ratios), len(ccx_ratios)
        ),
        "fraction_eligible_rows_expected_ccx_worsened": frac(
            sum(x > 1.0 + 1e-12 for x in ccx_ratios), len(ccx_ratios)
        ),
        "fraction_eligible_rows_lower_expected_ccx": frac(
            sum(x < 1.0 for x in ccx_ratios if x is not None),
            len(ccx_ratios),
        ),
        "aggregate_expected_phase_round_ratio_sum_T_over_sum_B": (
            sum_t_phase / sum_b_phase if sum_b_phase else None
        ),
        "aggregate_expected_phase_round_reduction": (
            1.0 - sum_t_phase / sum_b_phase if sum_b_phase else None
        ),
        "median_row_expected_phase_round_ratio": median_or_none(phase_ratios),
        "median_ccx_per_phase_round_ratio": median_or_none(per_round),
        "mean_ccx_per_phase_round_ratio": mean_or_none(per_round),
        "mean_row_expected_phase_round_ratio": mean_or_none(phase_ratios),
        "aggregate_ccx_per_phase_round_ratio": (
            (sum_t_ccx / sum_b_ccx) / (sum_t_phase / sum_b_phase)
            if sum_b_ccx and sum_b_phase and sum_t_phase else None
        ),
        "median_combined_peak_width_reduction": median_or_none(
            [r["resource"]["combined_peak_width_reduction"] for r in resource]
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-min", type=int, default=65536)
    ap.add_argument("--n-max", type=int, default=131071)
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--per-group", type=int, default=16)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.n_min != 65536 or args.n_max != 131071:
        raise SystemExit(
            "Preregistered default population is fixed at 65536..131071; "
            "edit the preregistration before changing the range."
        )
    if args.prime_min != 11:
        raise SystemExit("Preregistered minimum factor prime is fixed at 11.")
    if (args.start_bits, args.step_bits, args.shots_per_stage) != (4, 2, 4):
        raise SystemExit("Preregistered staged policy is fixed at 4,2,4.")
    if args.per_group != 16:
        raise SystemExit(
            "Preregistered default sample is fixed at 16 per group per ell."
        )

    pairs = semiprime_pairs(
        prime_min=args.prime_min,
        n_min=args.n_min,
        n_max=args.n_max,
    )

    out = {
        "experiment": "dark_star_scalable_resource_population_holdout_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "preregistered_population": {
            "n_min": args.n_min,
            "n_max": args.n_max,
            "prime_min": args.prime_min,
            "per_group_per_ell": args.per_group,
            "ells": list(ELLS),
            "selection_salt": SELECTION_SALT,
            "base_salt": BASE_SALT,
            "base_pool": list(BASE_POOL),
        },
        "staged_policy": {
            "start_bits": args.start_bits,
            "step_bits": args.step_bits,
            "shots_per_stage": args.shots_per_stage,
        },
        "rows": [],
        "summaries": {},
        "comparisons": {},
        "claim_boundary": (
            "Fresh deterministic small-semiprime population; polynomial logical "
            "reversible-arithmetic resource model only. No QPU runtime/fidelity, "
            "surface-code, asymptotic-Shor, or practical-RSA claim."
        ),
    }

    for ell in ELLS:
        selected = select_balanced(pairs, ell, args.per_group)
        print(f"ell={ell}: selected {len(selected)} rows")
        for idx, (group, p, q) in enumerate(selected, 1):
            n = p * q
            print(
                f"  [{idx:02d}/{len(selected)}] group={group} N={n} "
                f"p={p} q={q}"
            )
            row = make_row(
                group,
                p,
                q,
                ell,
                start_bits=args.start_bits,
                step_bits=args.step_bits,
                shots_per_stage=args.shots_per_stage,
            )
            out["rows"].append(row)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(out, indent=2, default=str) + "\n",
                encoding="utf-8",
            )

        ell_rows = [r for r in out["rows"] if r["ell"] == ell]
        out["summaries"][str(ell)] = {}
        for group in ("trigger", "control"):
            rr = [r for r in ell_rows if r["group"] == group]
            out["summaries"][str(ell)][group] = summarize_group(rr)

        tr = out["summaries"][str(ell)]["trigger"]
        cr = out["summaries"][str(ell)]["control"]
        t_ratio = tr["aggregate_expected_ccx_ratio_sum_T_over_sum_B"]
        c_ratio = cr["aggregate_expected_ccx_ratio_sum_T_over_sum_B"]
        out["comparisons"][str(ell)] = {
            "trigger_aggregate_ccx_ratio": t_ratio,
            "control_aggregate_ccx_ratio": c_ratio,
            "trigger_stronger_than_control": (
                t_ratio is not None and c_ratio is not None and t_ratio < c_ratio
            ),
            "control_minus_trigger_aggregate_ccx_ratio": (
                c_ratio - t_ratio
                if t_ratio is not None and c_ratio is not None
                else None
            ),
        }

    out["violations"] = {
        "order_identity": [
            {"N": r["N"], "ell": r["ell"]}
            for r in out["rows"]
            if not r["order_identity_pass"]
        ],
        "witness_preservation": [
            {"N": r["N"], "ell": r["ell"]}
            for r in out["rows"]
            if not r["witness_preservation_pass"]
        ],
    }

    args.out.write_text(
        json.dumps(out, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    print("\n===== SCALABLE-RESOURCE POPULATION HOLDOUT =====")
    for ell in ELLS:
        print(f"ell={ell}")
        for group in ("trigger", "control"):
            s = out["summaries"][str(ell)][group]
            ar = s["aggregate_expected_ccx_ratio_sum_T_over_sum_B"]
            pr = s["aggregate_expected_phase_round_ratio_sum_T_over_sum_B"]
            print(
                f"  {group}: eligible={s['eligible_rows']}/{s['selected_rows']} "
                f"order_reduced={s['eligible_order_reduced_rows']}/"
                f"{s['eligible_rows']} "
                f"CCX T/B={ar:.4f} "
                f"({100*s['aggregate_expected_ccx_reduction']:.2f}% less) "
                f"phase T/B={pr:.4f} "
                f"median per-round CCX ratio="
                f"{s['median_ccx_per_phase_round_ratio']:.4f}"
            )
        c = out["comparisons"][str(ell)]
        print(
            f"  trigger_stronger_than_control="
            f"{c['trigger_stronger_than_control']} "
            f"control-trigger ratio gap="
            f"{c['control_minus_trigger_aggregate_ccx_ratio']:.4f}"
        )

    print(
        "\nviolations:",
        json.dumps(out["violations"], sort_keys=True),
    )
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
