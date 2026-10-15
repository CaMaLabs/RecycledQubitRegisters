#!/usr/bin/env python3
"""Preregistered Dark Star public-policy + classical holdout v2 (ZERO QPU).

Frozen design: docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_PREREG.md
The phase oracle (validation order) is used ONLY to synthesize ideal-QPE bins.
The factor-verification predicate receives exclusively public y,m,a,N.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import dark_star_ptp_shor_audit as dsbase
import dark_star_recycled_scalable_arithmetic_audit as model

ELLS = (3, 5, 7)
MIN_N, MAX_N, PRIME_MIN, PER_GROUP = 131072, 262143, 11, 24
SELECTION_SALT = "QRR-public-policy-classical-v2-pop-20261014-1905"
BASE_SALT = "QRR-public-policy-classical-v2-base-20261014-1905"
BASE_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
B1, B2 = 43, 79
P1_BASES = (2, 3)
STAGE_START, STAGE_STEP, STAGE_SHOTS = 4, 2, 4
REV = "20261014-v2-preregistered-public-policy-classical"
DEFAULT_OUT = Path("results/dark_star_ptp/dark_star_public_policy_classical_v2.json")


def sha_rank(salt, *parts):
    msg = "|".join([salt, *(str(p) for p in parts)]).encode()
    return hashlib.sha256(msg).digest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def chosen_base(n, ell):
    k = int.from_bytes(sha_rank(BASE_SALT, "base", ell, n), "big") % len(BASE_POOL)
    for j in range(len(BASE_POOL)):
        a = BASE_POOL[(k + j) % len(BASE_POOL)]
        if math.gcd(a, n) == 1:
            return a
    raise AssertionError("no public base")


def public_manifest():
    primes = dsbase.sieve_primes(MAX_N)
    # Generate unique squarefree semiprimes p<q with N in a new disjoint interval.
    candidates = {"trigger": {}, "control": {}}
    for pi, p in enumerate(primes):
        if p < PRIME_MIN or p * p >= MAX_N:
            continue
        for q in primes[pi + 1:]:
            n = p * q
            if n > MAX_N:
                break
            if n >= MIN_N:
                for ell in ELLS:
                    if n % ell == 0:
                        continue
                    group = "control" if n % ell == 1 else "trigger"
                    candidates[group].setdefault(ell, []).append((n, p, q))
    manifest, oracle = [], {}
    for ell in ELLS:
        for group in ("trigger", "control"):
            ranked = sorted(
                candidates[group][ell],
                key=lambda item: (sha_rank(SELECTION_SALT, ell, group, item[0]), item[0]),
            )
            assert len(ranked) >= PER_GROUP, (ell, group, len(ranked))
            for n, p, q in ranked[:PER_GROUP]:
                a = chosen_base(n, ell)
                entry = dict(ell=ell, group=group, N=n, base=a,
                             transformed_base=pow(a, ell, n))
                manifest.append(entry)
                oracle[(ell, n)] = (p, q)
    assert len(manifest) == 6 * PER_GROUP
    assert len({(r["ell"], r["N"]) for r in manifest}) == len(manifest)
    return manifest, oracle, hashlib.sha256(canon(manifest).encode()).hexdigest()


def primes_le(n):
    return [p for p in dsbase.sieve_primes(n) if p >= 2]


def mul_equiv(exp):
    # Consistent binary repeated-squaring bookkeeper; not actual CPU seconds.
    e = int(exp)
    return max(0, e.bit_length() - 1) + e.bit_count()


def charge_pow(ledger, exponent):
    ledger["modmul_equiv"] += mul_equiv(exponent)
    ledger["pow_calls"] += 1


def factor_or_none(g, n):
    return int(g) if 1 < g < n and n % g == 0 else None


def public_power2_chain(n, a):
    ledger = Counter()
    x = a % n
    ledger["gcd_calls"] += 1
    d = factor_or_none(math.gcd(a, n), n)
    if d:
        return d, dict(ledger)
    for _ in range(n.bit_length() + 2):
        ledger["gcd_calls"] += 2
        f = factor_or_none(math.gcd(x - 1, n), n) or factor_or_none(
            math.gcd(x + 1, n), n)
        if f:
            return f, dict(ledger)
        if x == 1:
            break
        x = (x * x) % n
        ledger["modmul_equiv"] += 1
    return None, dict(ledger)


def common_classical(n, a):
    ledger = Counter()
    for p in primes_le(B1):
        ledger["trial_remainders"] += 1
        if n % p == 0:
            return {"solved": True, "factor": p, "source": "trial_division", "ledger": dict(ledger)}
    factor, l = public_power2_chain(n, a)
    ledger.update(l)
    if factor:
        return {"solved": True, "factor": factor, "source": "baseline_power2", "ledger": dict(ledger)}
    m = 1
    for p in primes_le(B1):
        pp = p
        while pp * p <= B1:
            pp *= p
        m *= pp
    for base in P1_BASES:
        ledger["gcd_calls"] += 1
        d = factor_or_none(math.gcd(base, n), n)
        if d:
            return {"solved": True, "factor": d, "source": "p1_base_gcd", "ledger": dict(ledger)}
        charge_pow(ledger, m)
        aa = pow(base, m, n)
        ledger["gcd_calls"] += 1
        d = factor_or_none(math.gcd(aa - 1, n), n)
        if d:
            return {"solved": True, "factor": d, "source": "p1_stage1", "ledger": dict(ledger)}
        for p in primes_le(B2):
            if p <= B1:
                continue
            charge_pow(ledger, p)
            ledger["gcd_calls"] += 1
            d = factor_or_none(math.gcd(pow(aa, p, n) - 1, n), n)
            if d:
                return {"solved": True, "factor": d, "source": "p1_stage2", "ledger": dict(ledger)}
    return {"solved": False, "factor": None, "source": "unsolved", "ledger": dict(ledger)}


def public_factor_from_cf(y, bits, a, n):
    """Only public inputs; no factor/order/hidden witness oracle."""
    if y == 0:
        return False
    seen = set()
    for d in model.convergent_denominators(y, 1 << bits):
        d = int(d)
        if d <= 1 or d > n or d in seen:
            continue
        seen.add(d)
        if d % 2:
            continue
        if pow(a, d, n) != 1:
            continue
        x = pow(a, d // 2, n)
        if factor_or_none(math.gcd(x - 1, n), n):
            return True
        if factor_or_none(math.gcd(x + 1, n), n):
            return True
    return False


def stage_success(n, a, r, bits, cache):
    key = (n, a, r, bits)
    if key in cache:
        return cache[key]
    if (1 << bits) < r:
        cache[key] = (0.0, 0.0)
        return cache[key]
    exact, weak = 0.0, 0.0
    match = {}
    for s in range(r):
        y, prob = model.nearest_bin_and_probability(s, r, bits)
        if y not in match:
            # Public verifier evaluated on model-generated phase measurement.
            public_pass = public_factor_from_cf(y, bits, a, n)
            weak_pass = model.fast_recover_from_validation_order(y, bits, r, n)
            if public_pass and not weak_pass:
                raise AssertionError("public valid witness not a multiple of validation order")
            match[y] = (public_pass, weak_pass)
        pp, wp = match[y]
        exact += (prob / r) if pp else 0.0
        weak += (prob / r) if wp else 0.0
    if exact > weak + 1e-10 or exact > 1.00000001 or weak > 1.00000001:
        raise AssertionError("QPE success probability invalid")
    cache[key] = (min(1.0, exact), min(1.0, weak))
    return cache[key]


def expected_quantum(n, a, r, gate_cache, p_cache):
    reach, weak_reach = 1.0, 1.0
    ccx = rounds = cswap = shots = 0.0
    for m in model.stage_schedule(n, STAGE_START, STAGE_STEP):
        # No hidden order enters either the arithmetic gate builder or public verifier.
        p, old_p = stage_success(n, a, r, m, p_cache)
        executed = reach * model.expected_stage_shots(p, STAGE_SHOTS)
        arith = model.stage_arithmetic_count(n, a, m, gate_cache)
        ccx += executed * arith.get("ccx", 0)
        cswap += executed * arith.get("cswap", 0)
        rounds += executed * m
        shots += executed
        reach *= (1.0 - p) ** STAGE_SHOTS
        weak_reach *= (1.0 - old_p) ** STAGE_SHOTS
    success = max(0.0, 1.0 - reach)
    return {
        "expected_ccx": ccx,
        "expected_cswap": cswap,
        "expected_phase_rounds": rounds,
        "expected_circuit_executions": shots,
        "success_probability_by_cap": success,
        "weak_order_only_success_by_cap": max(0.0, 1.0 - weak_reach),
        "expected_ccx_per_success_with_restarts": (ccx / success if success > 1e-14 else None),
    }


def decide_policy(ell, group, name):
    if name == "never":
        return False
    if name == "always":
        return True
    if name == "trigger":
        return group == "trigger"
    if name == "conservative_ell3":
        return ell == 3 and group == "trigger"
    raise ValueError(name)


def one_row(spec, pair, gate_cache, prob_cache):
    n, ell, group = spec["N"], spec["ell"], spec["group"]
    a, b = spec["base"], spec["transformed_base"]
    # Public processing and policy decisions precede every hidden-order call.
    primary = common_classical(n, a)
    other_factor, other_ledger = public_power2_chain(n, b)
    transform_ledger = {"modmul_equiv": mul_equiv(ell), "pow_calls": 1}
    row = {
        **spec, "classical_common": primary,
        "classical_transformed_power2": {
            "factor": other_factor, "solved": bool(other_factor), "ledger": other_ledger
        },
        "classical_transform_cost": transform_ledger,
        "policy_selected_transform": {
            name: decide_policy(ell, group, name)
            for name in ("never", "always", "trigger", "conservative_ell3")
        },
    }
    p, q = pair  # validation-only: AFTER public population/base/policy are fixed
    lam = math.lcm(p - 1, q - 1)
    r0 = model.multiplicative_order_from_lambda(a, n, lam)
    r1 = model.multiplicative_order_from_lambda(b, n, lam)
    witness0 = model.factor_witness(a, r0, n)
    witness1 = model.factor_witness(b, r1, n)
    theorem_ok = r1 == r0 // math.gcd(r0, ell)
    witness_ok = (witness0["factor_success"] == witness1["factor_success"] and
                  (not witness0["factor_success"] or (
                      witness0["x"] == witness1["x"] and
                      witness0["factors"] == witness1["factors"])))
    if not theorem_ok or not witness_ok:
        raise AssertionError(f"odd-power theorem or witness violation: N={n} ell={ell}")
    row["validation_only"] = {
        "p": p, "q": q, "lambda": lam, "baseline_order": r0,
        "transformed_order": r1, "order_reduced": r1 < r0,
        "baseline_factor_capable": bool(witness0["factor_success"]),
        "transformed_factor_capable": bool(witness1["factor_success"]),
        "order_identity_pass": theorem_ok, "witness_preservation_pass": witness_ok,
    }
    row["eligible_paired_quantum"] = (
        not primary["solved"] and not other_factor
        and witness0["factor_success"] and witness1["factor_success"]
    )
    if primary["solved"]:
        row["quantum"] = {}
        row["quantum_required"] = False
        return row
    base_quantum = expected_quantum(n, a, r0, gate_cache, prob_cache)
    transform_quantum = None
    if not other_factor:
        transform_quantum = expected_quantum(n, b, r1, gate_cache, prob_cache)
    row["quantum_required"] = True
    row["quantum"] = {"never": base_quantum, "always": transform_quantum}
    row["policy"] = {}
    for name in ("never", "always", "trigger", "conservative_ell3"):
        transformed = row["policy_selected_transform"][name]
        classical_solved = bool(transformed and other_factor)
        quantum = None if classical_solved else (transform_quantum if transformed else base_quantum)
        row["policy"][name] = {
            "classically_solved_after_transform": classical_solved,
            "uses_transform": transformed,
            "expected_ccx": 0.0 if classical_solved else quantum["expected_ccx"],
            "expected_phase_rounds": 0.0 if classical_solved else quantum["expected_phase_rounds"],
            "factor_success_probability_by_cap": 1.0 if classical_solved else quantum["success_probability_by_cap"],
            "expected_ccx_per_success_with_restarts": (
                0.0 if classical_solved else quantum["expected_ccx_per_success_with_restarts"]
            ),
        }
    return row


def bootstrap_ci(rows, choice, seed):
    if len(rows) < 2:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(2000):
        sample = [rows[rng.randrange(len(rows))] for __ in range(len(rows))]
        denom = sum(r["policy"]["never"]["expected_ccx"] for r in sample)
        num = sum(r["policy"][choice]["expected_ccx"] for r in sample)
        if denom:
            values.append(num / denom)
    if not values:
        return None
    values.sort()
    return [values[int(0.025 * (len(values)-1))], values[int(0.975 * (len(values)-1))]]


def summarize(rows, ell, group):
    pair = [r for r in rows if r["eligible_paired_quantum"]]
    unresolved = [r for r in rows if r["quantum_required"]]
    def ratio(numer, denom):
        return numer / denom if denom else None
    def mean_or_none(x):
        return statistics.mean(x) if x else None
    def median_or_none(x):
        return statistics.median(x) if x else None
    ret = {
        "selected": len(rows), "common_classical_solved": len(rows)-len(unresolved),
        "classical_solve_fraction": (len(rows)-len(unresolved))/len(rows) if rows else None,
        "unresolved": len(unresolved), "eligible_paired": len(pair),
        "eligible_order_reduced": sum(r["validation_only"]["order_reduced"] for r in pair),
        "paired": {}, "policy_all_unresolved": {},
    }
    for choice in ("always", "trigger", "conservative_ell3"):
        bas = sum(r["policy"]["never"]["expected_ccx"] for r in pair)
        cand = sum(r["policy"][choice]["expected_ccx"] for r in pair)
        bs = sum(r["policy"]["never"]["expected_phase_rounds"] for r in pair)
        cs = sum(r["policy"][choice]["expected_phase_rounds"] for r in pair)
        row_ratios = [ratio(r["policy"][choice]["expected_ccx"],
                            r["policy"]["never"]["expected_ccx"]) for r in pair]
        row_ratios = [x for x in row_ratios if x is not None]
        ccx_ratio = ratio(cand, bas)
        phase_ratio = ratio(cs, bs)
        restart_rows = [r for r in pair if all(
            r["policy"][k]["expected_ccx_per_success_with_restarts"] is not None
            for k in ("never", choice))]
        restart_bas = sum(r["policy"]["never"]["expected_ccx_per_success_with_restarts"] for r in restart_rows)
        restart_cand = sum(r["policy"][choice]["expected_ccx_per_success_with_restarts"] for r in restart_rows)
        ret["paired"][choice] = {
            "aggregate_ccx_ratio": ccx_ratio,
            "aggregate_phase_ratio": phase_ratio,
            "ccx_per_phase_ratio": ratio(ccx_ratio, phase_ratio),
            "mean_row_ccx_ratio": mean_or_none(row_ratios),
            "median_row_ccx_ratio": median_or_none(row_ratios),
            "improved": sum(x < 1-1e-12 for x in row_ratios),
            "tied": sum(abs(x-1) <= 1e-12 for x in row_ratios),
            "worsened": sum(x > 1+1e-12 for x in row_ratios),
            "restart_adjusted_aggregate_ratio": ratio(restart_cand, restart_bas),
            "restart_adjusted_rows": len(restart_rows),
            "bootstrap_95pct_aggregate_ratio": bootstrap_ci(
                pair, choice, 202610141905 + 100*ell + (0 if group=="trigger" else 1)
                 + {"always":0,"trigger":10000,"conservative_ell3":20000}[choice]
            ),
        }
        all_den = sum(r["policy"]["never"]["expected_ccx"] for r in unresolved)
        all_num = sum(r["policy"][choice]["expected_ccx"] for r in unresolved)
        ret["policy_all_unresolved"][choice] = {
            "aggregate_expected_ccx_ratio": ratio(all_num, all_den),
            "classical_after_transform_count": sum(
                r["policy"][choice]["classically_solved_after_transform"]
                for r in unresolved),
            "mean_success_by_cap": mean_or_none([
                r["policy"][choice]["factor_success_probability_by_cap"]
                for r in unresolved]),
            "never_mean_success_by_cap": mean_or_none([
                r["policy"]["never"]["factor_success_probability_by_cap"]
                for r in unresolved]),
        }
    ret["mean_common_classical_modmul_equiv"] = mean_or_none(
        [r["classical_common"]["ledger"].get("modmul_equiv",0) for r in rows])
    ret["mean_transform_modmul_equiv"] = mean_or_none(
        [r["classical_transform_cost"]["modmul_equiv"] for r in rows])
    return ret


def self_test():
    assert public_factor_from_cf(round((1<<16)/12), 16, 2, 35)
    assert not public_factor_from_cf(round((1<<16)/2), 16, 34, 35)
    assert common_classical(35, 2)["solved"]
    manifest, oracle, h = public_manifest()
    assert len(manifest) == 144 and len(h) == 64 and len(oracle) == 144
    assert all(MIN_N<=r["N"]<=MAX_N for r in manifest)
    print("V2 SELF-TEST PASS; 144 frozen public rows; manifest_sha256="+h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ell", type=int, choices=ELLS, required=False)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--manifest-only", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    manifest, oracle, manifest_sha = public_manifest()
    print("FROZEN PUBLIC MANIFEST_SHA256", manifest_sha, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out.with_suffix(".public-manifest.json")
    manifest_path.write_text(json.dumps({"sha256":manifest_sha,"rows":manifest},indent=2)+"\n")
    if args.manifest_only:
        return 0
    assert args.ell is not None, "must provide frozen --ell 3, 5, or 7 for parallel shards"
    selected = [r for r in manifest if r["ell"] == args.ell]
    assert len(selected) == 2*PER_GROUP
    out = {
        "experiment":"dark_star_public_policy_classical_v2",
        "script_revision":REV, "zero_qpu":True, "qpu_jobs_submitted":0,
        "manifest_sha256": manifest_sha,
        "preregistration":"docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_PREREG.md",
        "ell":args.ell, "expected_shard_rows":len(selected),
        "started_at_utc":datetime.now(timezone.utc).isoformat(),
        "complete":False, "rows":[], "summaries":{},
    }
    gate_cache, prob_cache = {}, {}
    checkpoint = args.out.with_suffix(".partial.json")
    for i,spec in enumerate(selected,1):
        print(f"[ell={args.ell} {i:02d}/{len(selected)}] N={spec['N']} group={spec['group']}",flush=True)
        row = one_row(spec, oracle[(args.ell,spec["N"])], gate_cache, prob_cache)
        out["rows"].append(row)
        checkpoint.write_text(json.dumps(out,indent=2)+"\n")
    for group in ("trigger","control"):
        arr = [r for r in out["rows"] if r["group"]==group]
        assert len(arr)==PER_GROUP
        out["summaries"][group] = summarize(arr, args.ell, group)
    out["complete"]=True
    out["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print("SHARD COMPLETE",args.ell,"rows",len(out["rows"]),flush=True)
    for k,v in out["summaries"].items():
        print(k, "classical_solved",v["common_classical_solved"],
              "eligible_paired",v["eligible_paired"],
              "trigger/never CCX",v["paired"]["trigger"]["aggregate_ccx_ratio"],flush=True)
    print("NO QPU JOB SUBMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
