#!/usr/bin/env python3
"""Dark Star: 16 previously frozen 24-bit N/a pairs, exploratory full-outcome
ideal-QPE cost follow-up. Source population already has published order labels:
this is NOT an independent holdout. CPU ONLY; zero IBM QPU/Runtime.

All 16 indexed shards must complete before a validated merge.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import dark_star_n22_numerical_precision_audit as prec
import dark_star_n22_full_tail_qpe_holdout as tail
import dark_star_n22_selector_vs_cube as classical
import dark_star_recycled_scalable_arithmetic_audit as gates

ROOT = Path("results/dark_star_ptp")
MANIFEST = ROOT / "dark_star_n24_public_predictor_manifest.json"
OLD_VALIDATION = ROOT / "dark_star_n24_public_predictor_validation.json"
PREREG = "docs/DARK_STAR_N24_FULL_QPE_FOLLOWUP_PREREG.md"
SHA = "d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889"
N_ROWS = 16
STAGES = tuple(range(4, 49, 2))
FAMILY = N_ROWS * 2 * len(STAGES) * 2 * 2
ALPHA = .01
assert len(STAGES) == 23 and FAMILY == 2944

# Only deliberate changes to previously audited ideal-QPE estimator:
# m=48 and all-16-row simultaneous error budget.
prec.STAGES = STAGES
prec.TOTAL_TESTS = FAMILY
prec.DELTA = ALPHA / FAMILY
prec.LOG = math.log(2 / prec.DELTA)
assert prec.N_SAMPLES == 131072
assert prec.W == 32 and prec.EXACT_M == 18
assert prec.SALT == "QRR-n22-precision-audit-iid-20261015"


def canonical(rows):
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def read_frozen():
    m = json.loads(MANIFEST.read_text())
    rows = m["selected_public_rows"]
    assert m["selected_sha256"] == SHA
    assert hashlib.sha256(canonical(rows).encode()).hexdigest() == SHA
    assert len(rows) == 16 and len({x["N"] for x in rows}) == 16
    assert m["no_QPU"] and m["qpu_jobs_submitted"] == 0
    assert m["no_validation_factors_or_orders"]
    assert m["labels_not_evaluated_or_used_for_selection"]
    old = json.loads(OLD_VALIDATION.read_text())
    assert old["source_public_manifest_sha256"] == SHA
    assert old["QPE_not_scored"] and old["no_QPU"]
    assert len(old["rows"]) == 16
    for j, (x, y) in enumerate(zip(rows, old["rows"])):
        n, a = x["N"], x["base"]
        assert (1 << 23) <= n < (1 << 24), (j, n)
        assert math.gcd(n, a) == 1
        assert x["public_cube"] == pow(a, 3, n)
        assert x["public_B31_unfactored"]
        assert x["group"] == ("G1_mod3_1" if n % 3 == 1 else "G2_mod3_2")
        assert x["P1_mod3_1_predict_positive"] == (n % 3 == 1)
        assert all(y[k] == value for k, value in x.items()), j
        assert y["public_post_B31_classical"]["classically_factored"]
    return rows, old["rows"]


def inverse_ratio(interval):
    lo, hi = interval
    if lo is None or hi is None or lo <= 0 or hi <= 0:
        return [None, None]
    return [1 / hi, 1 / lo]


def policy_comparisons(row):
    cube_cmp = row["cube_vs_plain"]
    selections = {
        "P1_mod3_1": bool(row["public_features"]["P1_mod3_1_predict_positive"]),
        "P2_bitweight": bool(
            row["public_features"]["P2_public_bitweight_proxy"]["P2_source_proxy_predict_positive"]
        ),
    }
    out = {}
    for name, take_cube in selections.items():
        ratio = [1., 1.] if take_cube else inverse_ratio(cube_cmp["ratio"])
        selected = row["cube"] if take_cube else row["plain"]
        if take_cube:
            status = "same_as_always_cube"
        elif None in ratio:
            status = "undefined_factor_incapable_or_unbounded"
        elif ratio[1] < 1:
            status = "robust_selector_win"
        elif ratio[0] > 1:
            status = "robust_selector_loss"
        else:
            status = "inconclusive"
        out[name] = dict(
            select_cube=take_cube,
            selected_base=selected["base"],
            selected_factor_capable=not selected["exact_factor_incapable"],
            cube_factor_capable=not row["cube"]["exact_factor_incapable"],
            selected_vs_always_cube_ratio=ratio,
            status=status,
        )
    return out


def score_index(index, rows, old_rows):
    x, old = rows[index], old_rows[index]
    n, a, b = x["N"], x["base"], x["public_cube"]
    start = time.process_time()
    print("PRE-FROZEN MANIFEST", SHA, "INDEX", index, "N", n, "BASE", a, flush=True)
    classical_ledger = classical.public_additional_classical(n)
    assert classical_ledger["classically_factored"], n
    factor = int(classical_ledger["factor"])
    assert 1 < factor < n and n % factor == 0
    assert factor in old["validation_only"]["factors"]
    print("PUBLIC CLASSICAL FACTOR", factor, "source",
          classical_ledger["first_factor_source"], flush=True)

    # These O(N) public modular + gcd scans can already factor N and MUST
    # be cost-accounted as classical preprocessing; no hidden order involved.
    cert_a = tail.public_factor_certificates(n, a)
    cert_b = tail.public_factor_certificates(n, b)
    print("PUBLIC CF certificates", len(cert_a[0]), len(cert_b[0]),
          "classical operation ledgers retained", flush=True)
    p, q = sorted((factor, n // factor))
    assert p * q == n and p != q
    lam = math.lcm(p - 1, q - 1)
    ra = gates.multiplicative_order_from_lambda(a, n, lam)
    rb = gates.multiplicative_order_from_lambda(b, n, lam)
    assert ra == old["validation_only"]["order_plain"]
    assert rb == old["validation_only"]["order_cube"]
    assert rb == ra // math.gcd(ra, 3)
    assert old["validation_only"]["exact_cube_half_order_witness_invariance_verified"]

    gate_cache, phase_cache = {}, {}
    plain = prec.score_base(n, a, ra, cert_a, gate_cache, phase_cache)
    cube = prec.score_base(n, b, rb, cert_b, gate_cache, phase_cache)
    assert [z["m"] for z in plain["all_stages"]] == list(STAGES)
    assert [z["m"] for z in cube["all_stages"]] == list(STAGES)
    comparison = tail.classify(plain, cube)
    out = dict(
        N=n, base=a, public_cube=b, group=x["group"], rank=x["rank"],
        public_features=x, frozen_earlier_validation_labels_only={
            "order_plain": ra, "order_cube": rb,
            "half_order_witness_invariant": True,
            "previous_joint_shortening_witness_label":
                old["label_T_shrunk_and_factor_witness"],
        },
        public_classical_ledger=classical_ledger,
        plain=plain, cube=cube, cube_vs_plain=comparison,
        zero_QPU=True,
    )
    out["fixed_policies"] = policy_comparisons(out)
    out["model_CPU_seconds"] = round(time.process_time() - start, 5)
    assert all(z["lower"] <= z["upper"]
               for arm in (plain, cube) for z in arm["all_stages"])
    print("DONE", index, "N", n, "r", ra, "r3", rb,
          "cube/plain", comparison["ratio"], comparison["status"],
          "P1", out["fixed_policies"]["P1_mod3_1"]["status"],
          "P2", out["fixed_policies"]["P2_bitweight"]["status"],
          "CPU seconds", out["model_CPU_seconds"], flush=True)
    return out


def run_shard(index):
    rows, old = read_frozen()
    tests = prec.check_selftests()
    assert tests["passed"]
    row = score_index(index, rows, old)
    output = dict(
        experiment="dark_star_n24_reused_manifest_full_outcome_qpe_exploratory",
        preregistration=PREREG, manifest_sha256=SHA,
        already_labeled_population_not_blind=True,
        index=index, complete=True, rows=[row],
        numerical_method=dict(
            stage_m=list(STAGES), phase_draws_if_not_exhaustive=prec.N_SAMPLES,
            fft_exact_through_m=prec.EXACT_M, head_halfwidth=prec.W,
            omitted_probability_universal_bound=1 / (2 * prec.W - 1),
            total_alpha=ALPHA, simultaneous_family=FAMILY,
            seed_salt=prec.SALT,
            numerical_limitation="nominal IID empirical Bernstein and non-directed floating point",
            shots_per_stage=4,
        ),
        selftests=tests, zero_QPU=True, qpu_jobs_submitted=0,
        free_runtime_used=False, paid_runtime_used=False,
        outcome_scope="ideal model logical CCX only; classical precompute often factors N",
        completed_utc=datetime.now(timezone.utc).isoformat(),
    )
    dst = Path(f"n24_{index:02d}.json")
    dst.write_text(json.dumps(output, indent=2) + "\n")
    print("SAVED original shard", dst, flush=True)


def merge(shards):
    rows, _ = read_frozen()
    receipts = []
    for i in range(N_ROWS):
        path = shards / f"n24-row-{i}" / f"n24_{i:02d}.json"
        d = json.loads(path.read_text())
        assert d["complete"] and d["index"] == i
        assert d["manifest_sha256"] == SHA and d["already_labeled_population_not_blind"]
        assert d["zero_QPU"] and d["qpu_jobs_submitted"] == 0
        assert not d["paid_runtime_used"] and not d["free_runtime_used"]
        assert d["numerical_method"]["simultaneous_family"] == FAMILY
        assert d["numerical_method"]["stage_m"] == list(STAGES)
        assert len(d["rows"]) == 1
        row = d["rows"][0]
        spec = rows[i]
        assert row["N"] == spec["N"] and row["base"] == spec["base"]
        assert row["public_features"] == spec
        assert row["public_classical_ledger"]["classically_factored"]
        for arm in ("plain", "cube"):
            assert len(row[arm]["all_stages"]) == len(STAGES)
            assert [z["m"] for z in row[arm]["all_stages"]] == list(STAGES)
            assert row[arm]["public_CF_precomputation"]["explicitly_classical_factor_recovery"]
        assert row["cube_vs_plain"]["status"] in (
            "cube_model_win", "cube_model_loss", "inconclusive",
            "factor_incapable_or_uncertified", "ratio_unbounded"
        )
        assert row["fixed_policies"] == policy_comparisons(row)
        receipts.append(row)
        print("VERIFIED", i, row["N"], row["cube_vs_plain"]["status"], flush=True)

    summary = dict(
        complete_rows=len(receipts),
        classically_factored_count=sum(x["public_classical_ledger"]["classically_factored"]
                                      for x in receipts),
        cube_vs_plain_statuses=dict(Counter(x["cube_vs_plain"]["status"] for x in receipts)),
        cube_factor_capable=sum(not x["cube"]["exact_factor_incapable"] for x in receipts),
        plain_factor_capable=sum(not x["plain"]["exact_factor_incapable"] for x in receipts),
        public_classical_CF_factor_found=sum(bool(x["plain"]["public_CF_precomputation"]
                                                ["public_factors_found_by_precomputation"] or
                                                x["cube"]["public_CF_precomputation"]
                                                ["public_factors_found_by_precomputation"])
                                             for x in receipts),
        fixed_policies={},
    )
    for policy in ("P1_mod3_1", "P2_bitweight"):
        vals = [x["fixed_policies"][policy] for x in receipts]
        switches = [z for z in vals if not z["select_cube"]]
        wins = sum(z["status"] == "robust_selector_win" for z in switches)
        losses = sum(z["status"] == "robust_selector_loss" for z in switches)
        coverage = sum(z["selected_factor_capable"] for z in vals)
        cube_coverage = summary["cube_factor_capable"]
        threshold = math.ceil(3 * len(switches) / 4)
        summary["fixed_policies"][policy] = dict(
            switched_rows=len(switches), robust_wins=wins,
            robust_losses=losses, other_switched=len(switches)-wins-losses,
            selected_factor_capable=coverage, always_cube_factor_capable=cube_coverage,
            frozen_75_percent_threshold=threshold,
            exploratory_gate_pass=(bool(switches) and wins >= threshold and
                                   losses == 0 and coverage >= cube_coverage),
            status_counts=dict(Counter(z["status"] for z in vals)),
        )
    merged = dict(
        experiment="dark_star_n24_full_qpe_exploratory_original_shards_verified",
        preregistration=PREREG, source_manifest_sha256=SHA,
        already_labeled_population_not_blind=True,
        no_new_sampling_or_qpu=True,
        zero_QPU=True, qpu_jobs_submitted=0, free_runtime_used=False,
        paid_runtime_used=False,
        complete=True,
        model_claim_only=True, summary=summary, rows=receipts,
        confidence_note="99% simultaneous bound only under IID phase model, no certified PRNG/direct rounding",
        completed_utc=datetime.now(timezone.utc).isoformat(),
    )
    target = ROOT / "dark_star_n24_full_qpe_followup_all_16.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, indent=2) + "\n")
    for i in range(N_ROWS):
        src = shards / f"n24-row-{i}" / f"n24_{i:02d}.json"
        dest = ROOT / f"dark_star_n24_full_qpe_followup_index{i:02d}.json"
        dest.write_bytes(src.read_bytes())
    print("ALL 16 ORIGINALLY FROZEN ROWS AUDITED, NO QPU", json.dumps(summary), flush=True)
    print("PRESERVED EXACT ORIGINAL SHARDS + MERGED SUMMARY", target, flush=True)


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--index", type=int, choices=range(N_ROWS))
    group.add_argument("--merge", action="store_true")
    ap.add_argument("--shards", type=Path, default=Path("n24-shards"))
    args = ap.parse_args()
    if args.merge:
        merge(args.shards)
    else:
        run_shard(args.index)


if __name__ == "__main__":
    main()
