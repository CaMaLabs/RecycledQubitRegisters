#!/usr/bin/env python3
"""Independent out-of-range replication of the ell=5/7 residue selector effect.

This is the confirmatory follow-up to dark_star_shor_residue_prime_panel_audit.py.
The hypotheses, range, sample sizes, salts, endpoints, and success gate are fixed
in this file before examining the new range.

Confirmatory population
-----------------------
- ell in {5,7};
- squarefree semiprimes N=pq, p<q, p,q >= 11;
- fresh range 32768 <= N <= 65535;
- 240 SHA-256-ranked trigger and 240 control N values per ell;
- trigger: N mod ell not in {0,1};
- control: N mod ell == 1;
- one deterministic public base per N from the fixed small-prime pool;
- identical transform b = a^ell mod N in both groups.

Primary endpoint
----------------
Independent-N fraction with ell | ord_N(a).  The replication passes only if,
for BOTH ell=5 and ell=7:
  (1) trigger fraction > control fraction; and
  (2) Holm-adjusted two-sided Fisher p < 0.05 across the two hypotheses.

Secondary endpoints
-------------------
- ell | lambda(N) mechanism check;
- eligible order-reduction rate after the existing Shor-success and public
  repeated-squaring/GCD shortcut guardrails;
- exact conservative staged-QPE work on 20 deterministic eligible rows/group.

Hardware scout
--------------
After the confirmatory test, a separate small-N scout identifies the smallest
clean trigger case for each ell that is Shor-factor-capable, survives both
classical shortcut checks, and has the exact ell-fold order reduction.  This is
explicitly validation-guided case-study selection and is NOT part of the
confirmatory inference.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_ptp3_independent_holdout_audit as fixed_holdout
import dark_star_shor_residue_prime_panel_audit as panel

ELLS = (5, 7)
BASE_POOL = tuple(panel.BASE_POOL)
SELECTION_SALT = "QRR-residue-ell-replication-v1"
SCOUT_SALT = "QRR-hardware-candidate-scout-v1"
DEFAULT_OUT = Path("results/dark_star_ptp/dark_star_shor_residue_prime_replication_audit.json")


def hash_int(salt: str, *parts) -> int:
    msg = "|".join([salt, *(str(x) for x in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(msg).digest(), "big")


def semiprime_pairs(prime_min: int, n_min: int, n_max: int) -> list[tuple[int, int]]:
    primes = [p for p in base.sieve_primes(n_max) if p >= prime_min]
    out = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n > n_max:
                break
            if n >= n_min:
                out.append((p, q))
    return out


def choose_public_base(n: int, ell: int, salt: str) -> int:
    start = hash_int(salt, "base", ell, n) % len(BASE_POOL)
    for offset in range(len(BASE_POOL)):
        a = BASE_POOL[(start + offset) % len(BASE_POOL)]
        if math.gcd(a, n) == 1:
            return int(a)
    raise AssertionError(f"no coprime base for N={n}")


def select_balanced_pairs(pairs, ell: int, per_group: int):
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
                hash_int(SELECTION_SALT, "N", ell, group, pq[0] * pq[1]),
                pq[0] * pq[1],
            ),
        )
        if len(ranked) < per_group:
            raise RuntimeError(
                f"ell={ell} group={group}: requested {per_group}, only {len(ranked)} available"
            )
        selected.extend((group, p, q) for p, q in ranked[:per_group])
    return selected


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def fisher_boolean(rows, key: str) -> dict:
    tr = [r for r in rows if r["group"] == "trigger"]
    cr = [r for r in rows if r["group"] == "control"]
    a = sum(bool(r[key]) for r in tr); b = len(tr) - a
    c = sum(bool(r[key]) for r in cr); d = len(cr) - c
    tf = a / len(tr); cf = c / len(cr)
    return {
        "table": [[a, b], [c, d]],
        "trigger_fraction": tf,
        "control_fraction": cf,
        "absolute_rate_difference": tf - cf,
        "risk_ratio": tf / cf if cf else None,
        "fisher_exact_two_sided_p_independent_N": fixed_holdout.fisher_two_sided(a, b, c, d),
    }


def fisher_eligible(rows) -> dict:
    vals = {}
    for group in ("trigger", "control"):
        rr = [r for r in rows if r["group"] == group and r["eligible_quantum_row"]]
        k = sum(r["order_reduced"] for r in rr)
        vals[group] = (k, len(rr) - k, len(rr))
    a, b, nt = vals["trigger"]; c, d, nc = vals["control"]
    tf = a / nt if nt else None; cf = c / nc if nc else None
    return {
        "table": [[a, b], [c, d]],
        "trigger_rows": nt,
        "control_rows": nc,
        "trigger_fraction": tf,
        "control_fraction": cf,
        "absolute_rate_difference": tf - cf if tf is not None and cf is not None else None,
        "risk_ratio": tf / cf if tf is not None and cf else None,
        "fisher_exact_two_sided_p_independent_N": fixed_holdout.fisher_two_sided(a, b, c, d),
    }


def holm_two(p_by_ell: dict[int, float]) -> dict[str, float]:
    ordered = sorted(p_by_ell.items(), key=lambda kv: kv[1])
    out = {}; prev = 0.0; m = len(ordered)
    for i, (ell, p) in enumerate(ordered):
        adj = max(prev, min(1.0, (m - i) * p))
        out[str(ell)] = float(adj); prev = adj
    return out


def phase_summary(rows) -> dict:
    if not rows:
        return {"rows": 0}
    ratios = [r["phase_ratio"] for r in rows]
    sum_b = sum(r["phase_baseline_work"] for r in rows)
    sum_t = sum(r["phase_transformed_work"] for r in rows)
    agg = sum_t / sum_b if sum_b else None
    return {
        "rows": len(rows),
        "mean_ratio": mean(ratios),
        "median_ratio": median(ratios),
        "aggregate_ratio_sum_T_over_sum_B": agg,
        "aggregate_reduction_fraction": 1.0 - agg if agg is not None else None,
        "fraction_rows_lower_work": sum(x < 1.0 - 1e-12 for x in ratios) / len(ratios),
        "order_reduced_rows": sum(r["order_reduced"] for r in rows),
    }


def make_row(group: str, p: int, q: int, ell: int, salt: str) -> tuple[dict, list[dict]]:
    n = p * q
    a = choose_public_base(n, ell, salt)
    b = pow(a, ell, n)
    lam = base.lcm(p - 1, q - 1)
    r0 = base.multiplicative_order_from_lambda(a, n, lam)
    r1 = base.multiplicative_order_from_lambda(b, n, lam)
    expected = r0 // math.gcd(r0, ell)
    violations = []
    if r1 != expected:
        violations.append({"N": n, "ell": ell, "type": "order_identity", "got": r1, "expected": expected})

    w0 = pre.factor_witness(a, r0, n)
    w1 = pre.factor_witness(b, r1, n)
    witness_preserved = (
        (not w0["order_even"] or w0["half_power"] == w1["half_power"])
        and pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n)
    )
    if not witness_preserved:
        violations.append({"N": n, "ell": ell, "type": "witness_preservation"})

    s0 = qvalue.power2_chain_shortcut(a, n)
    s1 = qvalue.power2_chain_shortcut(b, n)
    guard = not s0["factor_found"] and not s1["factor_found"]
    factor_capable = bool(w0["factor_success"])
    eligible = factor_capable and guard

    row = {
        "N": n, "ell": ell, "N_mod_ell": n % ell, "group": group,
        "p_validation_only": p, "q_validation_only": q,
        "base": a, "transformed_base": b,
        "lambda_validation_only": lam,
        "lambda_div_ell_validation_only": lam % ell == 0,
        "baseline_order_validation_only": r0,
        "transformed_order_validation_only": r1,
        "order_div_ell_validation_only": r0 % ell == 0,
        "order_reduced": r1 < r0,
        "order_reduction_factor": r0 / r1,
        "baseline_factor_success_validation_only": factor_capable,
        "half_order_witness_preserved": witness_preserved,
        "baseline_classical_shortcut": s0,
        "transformed_classical_shortcut": s1,
        "paired_quantum_guardrail_pass": guard,
        "eligible_quantum_row": eligible,
        "phase_ratio": None,
        "phase_baseline_work": None,
        "phase_transformed_work": None,
    }
    return row, violations


def run_phase_subset(rows, ell: int, per_group: int, start_bits: int, step_bits: int, shots: int):
    out = {}
    for group in ("trigger", "control"):
        eligible = [r for r in rows if r["group"] == group and r["eligible_quantum_row"]]
        ranked = sorted(
            eligible,
            key=lambda r: (hash_int(SELECTION_SALT, "phase", ell, group, r["N"]), r["N"]),
        )[:per_group]
        for i, r in enumerate(ranked, start=1):
            bits = staged.stage_schedule(r["N"], start_bits, step_bits)
            br = panel.fast_exact_phase_expectation(
                n=r["N"], r_validation_only=r["baseline_order_validation_only"],
                stage_bits=bits, shots_per_stage=shots,
            )
            tr = panel.fast_exact_phase_expectation(
                n=r["N"], r_validation_only=r["transformed_order_validation_only"],
                stage_bits=bits, shots_per_stage=shots,
            )
            bw = br["unconditional"]["mean_phase_round_executions_per_attempted_session"]
            tw = tr["unconditional"]["mean_phase_round_executions_per_attempted_session"]
            r["phase_baseline_work"] = bw
            r["phase_transformed_work"] = tw
            r["phase_ratio"] = safe_ratio(tw, bw)
            if i % 5 == 0:
                print(f"ell={ell} {group}: staged-QPE {i}/{len(ranked)}")
        out[group] = phase_summary(ranked)
    return out


def scout_hardware_candidates(prime_min: int, n_min: int, n_max: int, start_bits: int, step_bits: int, shots: int):
    pairs = semiprime_pairs(prime_min, n_min, n_max)
    out = {}
    for ell in ELLS:
        clean = []
        for p, q in pairs:
            n = p * q
            if n % ell in (0, 1):
                continue
            row, violations = make_row("trigger", p, q, ell, SCOUT_SALT)
            if violations:
                continue
            if row["eligible_quantum_row"] and row["order_reduced"]:
                clean.append(row)
        if not clean:
            out[str(ell)] = None
            continue
        chosen = min(clean, key=lambda r: (r["N"], r["base"]))
        bits = staged.stage_schedule(chosen["N"], start_bits, step_bits)
        br = panel.fast_exact_phase_expectation(
            n=chosen["N"], r_validation_only=chosen["baseline_order_validation_only"],
            stage_bits=bits, shots_per_stage=shots,
        )
        tr = panel.fast_exact_phase_expectation(
            n=chosen["N"], r_validation_only=chosen["transformed_order_validation_only"],
            stage_bits=bits, shots_per_stage=shots,
        )
        bw = br["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        tw = tr["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        out[str(ell)] = {
            "selection_boundary": "post-confirmatory validation-guided case-study scout; not inferential",
            "criterion": "smallest N satisfying trigger + factor-capable + paired shortcut guardrail + exact ell-fold order reduction",
            "N": chosen["N"], "p_validation_only": chosen["p_validation_only"], "q_validation_only": chosen["q_validation_only"],
            "base": chosen["base"], "transformed_base": chosen["transformed_base"],
            "baseline_order_validation_only": chosen["baseline_order_validation_only"],
            "transformed_order_validation_only": chosen["transformed_order_validation_only"],
            "order_reduction_factor": chosen["order_reduction_factor"],
            "stage_bits": bits,
            "exact_unconditional_phase_work_baseline": bw,
            "exact_unconditional_phase_work_transformed": tw,
            "exact_unconditional_phase_work_ratio": safe_ratio(tw, bw),
            "exact_unconditional_phase_work_reduction_fraction": 1.0 - tw / bw if bw else None,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Independent ell=5/7 residue-selector replication")
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=32768)
    ap.add_argument("--N-max", type=int, default=65535)
    ap.add_argument("--per-group", type=int, default=240)
    ap.add_argument("--phase-per-group", type=int, default=20)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--scout-N-min", type=int, default=143)
    ap.add_argument("--scout-N-max", type=int, default=4095)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pairs = semiprime_pairs(args.prime_min, args.N_min, args.N_max)
    panels = {}; raw_p = {}; all_violations = []

    for ell in ELLS:
        selected = select_balanced_pairs(pairs, ell, args.per_group)
        rows = []
        for i, (group, p, q) in enumerate(selected, start=1):
            row, violations = make_row(group, p, q, ell, SELECTION_SALT)
            rows.append(row); all_violations.extend(violations)
            if i % 120 == 0:
                print(f"ell={ell}: processed {i}/{len(selected)} independent N rows")

        mechanism = fisher_boolean(rows, "lambda_div_ell_validation_only")
        primary = fisher_boolean(rows, "order_div_ell_validation_only")
        eligible = fisher_eligible(rows)
        raw_p[ell] = primary["fisher_exact_two_sided_p_independent_N"]
        phase = run_phase_subset(
            rows, ell, args.phase_per_group, args.start_bits, args.step_bits, args.shots_per_stage
        )
        panels[str(ell)] = {
            "trigger_definition": f"N mod {ell} not in {{0,1}}",
            "control_definition": f"N mod {ell} == 1",
            "transform": f"a -> a^{ell} mod N in both groups",
            "mechanism_lambda_divisibility": mechanism,
            "primary_order_divisibility": primary,
            "eligible_order_reduction": eligible,
            "phase_subset": phase,
            "rows": rows,
        }

    holm = holm_two(raw_p)
    pass_by_ell = {}
    for ell in ELLS:
        p = panels[str(ell)]["primary_order_divisibility"]
        p["holm_adjusted_p_across_5_7"] = holm[str(ell)]
        pass_by_ell[str(ell)] = bool(
            p["trigger_fraction"] > p["control_fraction"] and holm[str(ell)] < 0.05
        )

    candidates = scout_hardware_candidates(
        args.prime_min, args.scout_N_min, args.scout_N_max,
        args.start_bits, args.step_bits, args.shots_per_stage,
    )

    replication_pass = all(pass_by_ell.values()) and not all_violations
    result = {
        "experiment": "dark_star_shor_residue_prime_replication_audit_v1",
        "zero_qpu": True, "monte_carlo_used": False,
        "preregistered_success_gate": {
            "definition": "both ell=5 and ell=7 require trigger>control on ell|order and Holm-adjusted Fisher p<0.05; zero theorem/witness violations",
            "per_ell_pass": pass_by_ell,
            "overall_pass": replication_pass,
        },
        "selection": {
            "N_min": args.N_min, "N_max": args.N_max, "prime_min": args.prime_min,
            "per_group": args.per_group, "phase_per_group": args.phase_per_group,
            "ells": list(ELLS), "base_pool": list(BASE_POOL), "selection_salt": SELECTION_SALT,
        },
        "holm_adjusted_primary_p": holm,
        "panels": panels,
        "hardware_candidate_scout": candidates,
        "violation_count": len(all_violations), "violations": all_violations,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\n===== ELL=5/7 INDEPENDENT REPLICATION =====")
    for ell in ELLS:
        r = panels[str(ell)]
        m = r["mechanism_lambda_divisibility"]
        p = r["primary_order_divisibility"]
        e = r["eligible_order_reduction"]
        ph = r["phase_subset"]
        print(
            f"ell={ell}: lambda-div {m['trigger_fraction']:.4f}/{m['control_fraction']:.4f}; "
            f"order-div {p['trigger_fraction']:.4f}/{p['control_fraction']:.4f}; "
            f"p={p['fisher_exact_two_sided_p_independent_N']:.6g}; Holm={holm[str(ell)]:.6g}"
        )
        print(
            f"       eligible reduced {e['trigger_fraction']:.4f}/{e['control_fraction']:.4f}; "
            f"phase aggregate ratio {ph['trigger'].get('aggregate_ratio_sum_T_over_sum_B'):.4f}/"
            f"{ph['control'].get('aggregate_ratio_sum_T_over_sum_B'):.4f}"
        )
        c = candidates[str(ell)]
        if c:
            print(
                f"       hardware scout N={c['N']} a={c['base']} -> {c['transformed_base']}; "
                f"order {c['baseline_order_validation_only']}->{c['transformed_order_validation_only']}; "
                f"phase ratio={c['exact_unconditional_phase_work_ratio']:.4f}"
            )
    print(f"replication_pass={replication_pass}")
    print(f"violations={len(all_violations)}")
    print(f"wrote {args.out}")
    return 0 if replication_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
