#!/usr/bin/env python3
"""Exact 96-shot prefix-cost theorem on already published N25 same-order arms. ZERO QPU."""
from __future__ import annotations
import json
import math
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path("results/dark_star_ptp")
ORIGINAL = ROOT / "dark_star_n25_online_model_all_8.json"
PREVIOUS = ROOT / "dark_star_n25_exact_order_dominance.json"
OUTPUT = ROOT / "dark_star_n25_prefix_dominance.json"
SHA = "66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
STAGES = tuple(range(4, 51, 2))
SHOTS_PER_STAGE = 4


def main():
    orig = json.loads(ORIGINAL.read_text())
    prev = json.loads(PREVIOUS.read_text())
    assert orig["complete"] and orig["source_manifest_sha256"] == SHA
    assert prev["original_manifest_sha256"] == SHA
    assert orig["summary"]["total"] == prev["result_count"] == 8
    assert len(orig["rows"]) == len(prev["cases"]) == 8
    assert orig["zero_QPU"] and prev["zero_QPU"]
    assert orig["qpu_jobs_submitted"] == prev["qpu_jobs_submitted"] == 0
    assert not orig["paid_runtime_used"] and not prev["paid_runtime_used"]
    assert orig["summary"]["bounded_win"] == orig["summary"]["bounded_loss"] == 0
    rows = []
    unique = set()
    for i, (x, old) in enumerate(zip(orig["rows"], prev["cases"])):
        n, a, b = x["N"], x["base"], x["cube"]
        assert n not in unique
        unique.add(n)
        assert old["index"] == i and old["N"] == n and old["base"] == a
        assert b == pow(a, 3, n)
        r, r3 = x["validation_only"]["order_plain"], x["validation_only"]["order_cube"]
        assert r3 == r // math.gcd(r, 3)
        assert old["exact_orders"] == dict(plain=r, cube=r3, equal=(r == r3))
        assert old["original_model_status"] == x["cube_vs_plain"]["status"]
        same = r == r3
        capable = x["validation_only"]["factor_capable"]
        assert old["factor_incapable_for_both_exact"] is (not capable)
        p = x["model_plain"]["structural_modular_arithmetic_per_stage"]
        c = x["model_cube"]["structural_modular_arithmetic_per_stage"]
        assert len(p) == len(c) == len(STAGES)
        for m, left, right in zip(STAGES, p, c):
            assert left["m"] == right["m"] == m
            assert type(left["ccx"]) is int and type(right["ccx"]) is int
            assert left["ccx"] > 0 and right["ccx"] >= 0
        if not same:
            rows.append(dict(index=i, N=n, base=a, order_plain=r, order_cube=r3,
                factor_capable=capable, same_order=False,
                verdict="not_applicable_order_reduced",
                shot_prefixes_evaluated=0, min_ratio=None,
                original_n25_status=x["cube_vs_plain"]["status"],
                previous_secondary_verdict=old["exact_conditional_verdict"]))
            print("ROW", i, n, "order-reduced; not applicable")
            continue

        cp = cc = 0
        quotients = []
        differences = []
        prefix_rows = []
        for m, left, right in zip(STAGES, p, c):
            for shot in range(1, SHOTS_PER_STAGE + 1):
                cp += left["ccx"]
                cc += right["ccx"]
                z = Fraction(cc, cp)
                quotients.append(z)
                differences.append(cc - cp)
                prefix_rows.append(dict(stop_after_shot=len(prefix_rows)+1,
                    m=m, shot_within_stage=shot,
                    cumulative_plain_CCX=cp,
                    cumulative_cube_CCX=cc,
                    cube_minus_plain_CCX=cc-cp,
                    cube_over_plain_ratio=float(z)))
        assert len(quotients) == len(differences) == len(prefix_rows) == 96
        bound = min(quotients)
        min_k = quotients.index(bound) + 1
        failure_positions = [k for k, d in enumerate(differences, 1) if d <= 0]
        all_strict = len(failure_positions) == 0
        assert all_strict == (bound > 1)
        verdict = ("factor_incapable_no_per_success_ratio" if not capable else
            ("exact_cube_strictly_worse_by_every_shot_prefix" if all_strict else
             "prefix_dominance_not_certified"))
        row = dict(index=i, N=n, base=a, order_plain=r, order_cube=r3,
            factor_capable=capable, same_order=True,
            stop_model="any 1..96 attempted shots, 4 per stage",
            shot_prefixes_evaluated=96,
            every_prefix_cube_more_expensive=all_strict,
            min_ratio=float(bound),
            exact_min_ratio_fraction=[bound.numerator, bound.denominator],
            min_ratio_stopping_shot=min_k,
            min_ratio_stopping_stage=prefix_rows[min_k-1]["m"],
            max_ratio=float(max(quotients)),
            lowest_absolute_extra_CCX=min(differences),
            lowest_extra_CCX_shot=differences.index(min(differences))+1,
            number_nonpositive_prefixes=len(failure_positions),
            first_nonpositive_prefix_shot=failure_positions[0] if failure_positions else None,
            original_n25_status=x["cube_vs_plain"]["status"],
            previous_secondary_verdict=old["exact_conditional_verdict"],
            verdict=verdict,
            every_possible_stopping_shot_cost=prefix_rows)
        rows.append(row)
        print("ROW", i, n, "capable", capable, "all 96 prefix worse", all_strict,
              "min ratio", float(bound), "min at shot", min_k, "not strict", len(failure_positions), flush=True)

    assert len(rows) == len(unique) == 8
    same_rows = [x for x in rows if x["same_order"]]
    assert len(same_rows) == sum(x["exact_orders"]["equal"] for x in prev["cases"])
    statuses = dict(Counter(x["verdict"] for x in rows))
    out = dict(experiment="dark_star_n25_96_shot_prefix_cost_theorem",
        analysis_scope="secondary_post_hoc_already_published_n25_rows",
        protocol="docs/DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_PROTOCOL.md",
        original_result=str(ORIGINAL), original_audit=str(PREVIOUS),
        manifest_sha256=SHA, original_preregistered_gate_unchanged=orig["summary"],
        proof="When order unchanged, ideal QPE+public CF/GCD acceptance and stopping times are identical; per-shot cumulative source CCX strict inequality for each of 96 possible stopping positions implies pathwise and expected source CCX disadvantage, and per-success disadvantage if probability of success > 0.",
        summary=dict(total=8, same_order_rows=len(same_rows),
            certified_strict_loss_factor_capable=sum(x["verdict"]=="exact_cube_strictly_worse_by_every_shot_prefix" for x in rows),
            incapable_same_order=sum(x["verdict"]=="factor_incapable_no_per_success_ratio" for x in rows),
            changed_order_not_applicable=sum(x["verdict"]=="not_applicable_order_reduced" for x in rows),
            same_order_uncertified=sum(x["verdict"]=="prefix_dominance_not_certified" for x in rows),
            verdict_counts=statuses),
        cases=rows,
        zero_QPU=True, qpu_jobs_submitted=0, paid_runtime_used=False,
        caveat="Post-hoc exact within source level structural CCX model and ideal QPE, not native compiled hardware or end-to-end cryptanalysis; original preregistered ratio intervals/statuses remain intact.",
        analyzed_utc=datetime.now(timezone.utc).isoformat())
    OUTPUT.write_text(json.dumps(out, indent=2) + "\n")
    print("PASS 8 rows, 96 valid stopping prefixes per same-order row, no QPU", json.dumps(statuses, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
