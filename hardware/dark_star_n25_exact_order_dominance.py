#!/usr/bin/env python3
"""Deterministic post-hoc conditional Dark Star N25 structural audit. No IBM/SDK."""
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("results/dark_star_ptp")
SRC = ROOT / "dark_star_n25_online_model_all_8.json"
DEST = ROOT / "dark_star_n25_exact_order_dominance.json"
EXPECTED_SHA = "66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
STAGES = list(range(4, 51, 2))


def gcd_factor_for_denominator(n, a, d):
    """Return (accepted, verified factor or None), using only N,a,d."""
    if d <= 1 or d > n or d & 1:
        return False, None
    if pow(a, d, n) != 1:
        return False, None
    half = pow(a, d // 2, n)
    for delta in (-1, 1):
        g = math.gcd(half + delta, n)
        if 1 < g < n:
            return True, g
    return False, None


def online_cf(n, a, y, m):
    """Independent public-only version of the archived online CF acceptance logic."""
    qden = 1 << m
    if y == 0:
        return False
    x, rem = y, qden
    prevprev, prev = 1, 0
    while rem:
        quot, nextrem = divmod(x, rem)
        d = quot * prev + prevprev
        if d > n:
            break
        if gcd_factor_for_denominator(n, a, d)[0]:
            return True
        prevprev, prev = prev, d
        x, rem = rem, nextrem
    return False


def small_order(a, n):
    if math.gcd(a, n) != 1:
        return None
    x = 1
    for r in range(1, n + 1):
        x = x * a % n
        if x == 1:
            return r
    raise AssertionError("multiplicative order not found")


def exhaustive_small_null():
    checked = 0
    cases = 0
    nontrivial = 0
    for n in (15, 21, 35, 77, 143, 209):
        for a in range(2, min(n, 18)):
            r = small_order(a, n)
            if r is None or r % 3 == 0:
                continue
            b = pow(a, 3, n)
            assert small_order(b, n) == r
            if b != a:
                nontrivial += 1
            cases += 1
            for m in (4, 6, 8):
                for y in range(1 << m):
                    assert online_cf(n, a, y, m) == online_cf(n, b, y, m), (n, a, y, m)
                    checked += 1
    assert cases >= 10 and nontrivial >= 4 and checked >= 4000
    return dict(cases=cases, nontrivial_cubes=nontrivial, exhaustive_measurement_comparisons=checked)


def target_null(n, a, b, r):
    seed = int.from_bytes(hashlib.sha256(("QRR-N25-EXACT-DOMINANCE-20261025|" + str(n)).encode()).digest(), "big")
    rng = random.Random(seed)
    ds = [2, 3, 4, 5, 6, 8, 10, 12, r, r + 1, 2 * r, 3 * r, r // 2, (r // 2) + 1]
    ds.extend(rng.randrange(2, n + 1) for _ in range(128))
    checked = 0
    producing = 0
    for d in ds:
        if not 1 < d <= n:
            continue
        left = gcd_factor_for_denominator(n, a, d)
        right = gcd_factor_for_denominator(n, b, d)
        assert left == right, (n, a, b, d, left, right)
        producing += int(left[0])
        checked += 1
    assert checked >= 100
    checked_y = 0
    for m in (4, 6, 10, 25, 50):
        Q = 1 << m
        values = range(Q) if m == 4 else (rng.randrange(Q) for _ in range(40))
        for y in values:
            assert online_cf(n, a, y, m) == online_cf(n, b, y, m), (n, m, y)
            checked_y += 1
    return dict(public_denominators_checked=checked, sampled_measurements_checked=checked_y,
                producing_denominator_controls=producing)


def certified_factor_incapable(n, a, r):
    """Proof-enabling exact witness condition, no order used in public selection."""
    assert pow(a, r, n) == 1
    if r & 1:
        # Every even d divisible by odd r is a multiple of 2r.
        return True, "odd_order_even_d_implies_half_is_multiple_of_r"
    z = pow(a, r // 2, n)
    assert z * z % n == 1
    trivial_root = z in (1, n - 1)
    return trivial_root, "trivial_square_root_for_all_even_order_multiples" if trivial_root else "nontrivial_square_root"


def main():
    src = json.loads(SRC.read_text())
    assert src["complete"] and src["summary"]["total"] == 8 and len(src["rows"]) == 8
    assert src["source_manifest_sha256"] == EXPECTED_SHA
    assert src["zero_QPU"] and src["qpu_jobs_submitted"] == 0 and not src["paid_runtime_used"]
    assert src["summary"]["bounded_win"] == 0 and src["summary"]["bounded_loss"] == 0
    cases = []
    seen = set()
    for index, x in enumerate(src["rows"]):
        n, a, b = x["N"], x["base"], x["cube"]
        assert 1 << 24 <= n < 1 << 25 and n not in seen
        seen.add(n)
        assert math.gcd(a, n) == 1 and b == pow(a, 3, n)
        r, r3 = x["validation_only"]["order_plain"], x["validation_only"]["order_cube"]
        assert r > 0 and r3 == r // math.gcd(r, 3)
        assert pow(a, r, n) == pow(b, r3, n) == 1
        same = r == r3
        p = x["model_plain"]["structural_modular_arithmetic_per_stage"]
        c = x["model_cube"]["structural_modular_arithmetic_per_stage"]
        assert len(p) == len(c) == len(STAGES)
        signs, rat = [], []
        for m, pstep, cstep in zip(STAGES, p, c):
            assert pstep["m"] == cstep["m"] == m
            cp, cc = pstep["ccx"], cstep["ccx"]
            assert type(cp) is int and type(cc) is int and cp > 0 and cc >= 0
            signs.append((cc > cp) - (cc < cp))
            rat.append(cc / cp)
        if same:
            tests = target_null(n, a, b, r)
        else:
            tests = None
        incapable, reason = certified_factor_incapable(n, a, r)
        incapable_b, reason_b = certified_factor_incapable(n, b, r3)
        assert incapable == incapable_b
        assert incapable == (not x["validation_only"]["factor_capable"])
        same_order_higher_at_all = same and all(s > 0 for s in signs)
        same_order_nonlower = same and all(s >= 0 for s in signs)
        if incapable:
            label = "exact_factor_incapable_for_both_bases"
        elif same_order_higher_at_all:
            label = "exact_cube_strictly_worse_source_CCX"
        elif same_order_nonlower and signs[0] > 0:
            label = "exact_cube_strictly_worse_source_CCX"
        elif same_order_nonlower:
            label = "exact_cube_cannot_reduce_source_CCX"
        elif same:
            label = "same_order_but_stage_costs_cross_not_certified"
        else:
            label = "order_reduction_no_exact_cost_verdict"
        if label == "exact_cube_strictly_worse_source_CCX":
            assert not incapable and same_order_nonlower and signs[0] > 0
        ratio_lower = min(rat) if same_order_higher_at_all else (1 if same_order_nonlower else None)
        cases.append(dict(index=index, N=n, base=a, cube=b,
            exact_orders=dict(plain=r, cube=r3, equal=same),
            arithmetic_source_only=True, factor_incapable_for_both_exact=incapable,
            factor_incapability_reason=reason if incapable else None,
            per_stage_ccx_cube_over_plain=dict(min=min(rat), max=max(rat),
                cube_larger=sum(s > 0 for s in signs), tied=sum(s == 0 for s in signs),
                cube_smaller=sum(s < 0 for s in signs), all_24_ratios=rat),
            coupled_attempted_run_cost_ratio_certified_lower_bound=ratio_lower,
            exact_conditional_verdict=label,
            original_model_status=x["cube_vs_plain"]["status"],
            original_model_ratio_interval=x["cube_vs_plain"]["ratio"],
            classically_solved_under_frozen_B47_rho64=x["public_classical_after_B31"]["classically_solved"],
            numerical_null_checks=tests))
        print("CHECKED", index, n, "r_equal", same, "incapable", incapable,
              "cube_costs_bigger", sum(s > 0 for s in signs), "/24", "verdict", label, flush=True)
    assert len(cases) == 8 and len(seen) == 8
    small = exhaustive_small_null()
    counts = {key: sum(x["exact_conditional_verdict"] == key for x in cases) for key in sorted(
        {x["exact_conditional_verdict"] for x in cases})}
    out = dict(experiment="dark_star_n25_exact_same_order_structural_falsification",
        analysis="post_hoc_secondary_mechanistic_not_blinded_n25_population",
        protocol="docs/DARK_STAR_N25_EXACT_ORDER_DOMINANCE_PROTOCOL.md",
        original_results=str(SRC), original_manifest_sha256=EXPECTED_SHA,
        original_primary_gate_unmodified=src["summary"],
        theorem="When gcd(3,ord(a))=1, QPE output and online CF/GCD acceptance are identical for a and a^3. Stage-wise CCX dominance implies pathwise staged attempted-run cost dominance.",
        result_count=len(cases), verdict_counts=counts, small_exhaustive_test=small,
        cases=cases, zero_QPU=True, qpu_jobs_submitted=0, paid_runtime_used=False,
        caveat="Exact only within ideal QPE + archived source modular arithmetic structural CCX model; no compiled native device circuit, no actual factoring advantage. A source-CCX attempted-session lower bound is not a hardware runtime or statistical confidence interval.",
        analyzed_utc=datetime.now(timezone.utc).isoformat())
    DEST.write_text(json.dumps(out, indent=2) + "\n")
    print("PASS all eight source CCX rows, all small exhaustive CF checks, zero QPU")
    print("COUNTS", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
