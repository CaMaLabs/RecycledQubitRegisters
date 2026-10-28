#!/usr/bin/env python3
"""Unified Dark Star public PTP/classical-first + odd-power + recycled QPE.

A transparent, self-generated SMALL semiprime research prototype.  Never runs
a real QPU or IBM Runtime. Synthetic p/q enter ONLY the ideal QPE oracle and
final validation. Public decisions and online CF/GCD verifier use N/a/y/m only.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_v2 as ds
from simulation.ptp_hybrid import core, kernel, symmetry
from hardware import dark_star_recycled_scalable_arithmetic_audit as gates

ODD_EXPONENTS = (1, 3, 5, 7, 105, 1155, 15015)
PUBLIC_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
PREVIEW_MAX_BITS = 26
W = 32


def pair(g, n):
    if 1 < g < n and n % g == 0:
        return [min(g, n // g), max(g, n // g)]
    return None


def public_base(n, requested=None):
    """No private p/q or order input. A noncoprime base yields a public factor."""
    if requested is not None:
        a = int(requested)
        if not 1 < a < n:
            raise ValueError("public base must satisfy 1<a<N")
        return a
    digest = hashlib.sha256(f"QRR-UNIFIED-20261028|{n}".encode()).digest()
    start = int.from_bytes(digest, "big") % len(PUBLIC_POOL)
    for j in range(len(PUBLIC_POOL)):
        a = PUBLIC_POOL[(start+j) % len(PUBLIC_POOL)]
        if a < n and math.gcd(a, n) == 1:
            return a
    raise ValueError("No coprime public base in fixed pool")


def ptp_public_metadata(n):
    """Safe residue and pair labels. Never reject a factor using mirror symmetry."""
    factored_wheel = core.small_base_factor(n)
    if not core.is_ptp_candidate(n):
        return dict(M=210, wheel_prime_factor=factored_wheel,
            kernel_root=None, candidate_kernel_pairs=0,
            naive_diagonal_symmetry_pruning_enabled=False,
            note="base wheel prime divides N; PTP-unit pair table not applicable")
    p = core.candidate_factor_pairs(n)
    return dict(M=210, wheel_prime_factor=None,
        kernel_root=core.root_for_integer(n), candidate_kernel_pairs=len(p),
        kernel_pairs=[list(x) for x in p],
        diagonal_symmetry_root_pairs=len({min(x, symmetry.diagonal_pair(x)) for x in p}),
        naive_diagonal_symmetry_pruning_enabled=False)


def proper_factor_public(n, a):
    for number, source in ((a, "gcd(base,N)"), (a-1, "gcd(base-1,N)"),
                           (a+1, "gcd(base+1,N)")):
        f = pair(math.gcd(number, n), n)
        if f:
            return dict(factors=f, source=source)
    return None


def public_power2_shortcut(n, a, steps=None):
    """Fixed-budget public Pollard-style square chain; no secret order."""
    x = a % n
    for k in range(steps if steps is not None else n.bit_length()+2):
        for sign in (-1, 1):
            factors = pair(math.gcd(x+sign, n), n)
            if factors:
                return dict(factors=factors, step=k, sign=sign)
        x = x*x % n
    return None


def pminusone_bounded(n, bound=31):
    x = 2
    ops = 0
    for p in ds.primes_up_to(bound):
        pk = p
        while pk*p <= bound:
            pk *= p
        x = pow(x, pk, n)
        ops += 1
    return dict(factors=pair(math.gcd(x-1, n), n),
                B=bound, pow_calls=ops, gcd_calls=1)


def rho_bounded(n, iterations=64):
    steps = gcds = 0
    for seed in (2, 3):
        x = y = seed % n
        for _ in range(iterations):
            x = (x*x+1) % n
            y = (y*y+1) % n
            y = (y*y+1) % n
            steps += 3
            gcds += 1
            g = math.gcd(abs(x-y), n)
            if pair(g, n):
                return dict(factors=pair(g, n), modular_squares=steps,
                            gcd_calls=gcds, seed=seed)
            if g == n:
                break
    return dict(factors=None, modular_squares=steps, gcd_calls=gcds)


def limited_prime_trial(n, bound=97):
    tested = 0
    for p in ds.primes_up_to(bound):
        tested += 1
        if n % p == 0:
            return dict(factors=pair(p, n), divisibility_tests=tested)
    return dict(factors=None, divisibility_tests=tested)


def public_classical_preflight(n, a, fermat_tests=12):
    """Fixed public-only priority stages, stop on first proper factor."""
    stages = []
    def done(name, result, **kw):
        found = result.get("factors")
        stages.append(dict(name=name, factors=found, **kw))
        return found

    for name, candidate in (("base_gcd", proper_factor_public(n,a)),
                            ("wheel_small_factor",
                             dict(factors=pair(core.small_base_factor(n) or 1,n)))):
        f = done(name, candidate or {}, detail=candidate)
        if f:
            return dict(factors=f, method=name, stages=stages, classically_solved=True)

    chain = public_power2_shortcut(n, a)
    f = done("public_power2_gcd", chain or {}, detail=chain)
    if f:
        return dict(factors=f, method="public_power2_gcd", stages=stages, classically_solved=True)

    for method, modulus in (("ordinary_fermat", None),
                            ("ptp_midpoint_105", 105),
                            ("ptp_midpoint_15015", 15015)):
        if modulus is not None:
            g = pair(math.gcd(n, modulus), n)
            if g:
                f = done(f"{method}_wheel_gcd", dict(factors=g), candidate_square_tests=0)
                return dict(factors=f, method=f"{method}_wheel_gcd", stages=stages, classically_solved=True)
        try:
            if modulus is None:
                z = ds.fermat_factor(n, max_square_tests=fermat_tests)
            else:
                z = ds.darkstar_fermat_factor(n, midpoint_modulus=modulus,
                                              max_square_tests=fermat_tests)
            f = done(method, dict(factors=[z.p, z.q]),
                     square_tests=z.square_tests, midpoint_modulus=modulus,
                     setup_seconds=z.setup_seconds, search_seconds=z.search_seconds)
        except RuntimeError:
            f = done(method, {}, square_tests_budget_exhausted=fermat_tests,
                     midpoint_modulus=modulus)
        if f:
            return dict(factors=f, method=method, stages=stages, classically_solved=True)

    for name, z in (("Pollard_p_minus_one_B31", pminusone_bounded(n)),
                    ("Floyd_rho_64", rho_bounded(n)),
                    ("trial_prime_97", limited_prime_trial(n))):
        f = done(name, z, details=z)
        if f:
            return dict(factors=f, method=name, stages=stages, classically_solved=True)
    return dict(factors=None, method="public_budgets_exhausted",
                stages=stages, classically_solved=False)


def classical_reference_benchmarks(n, limit=1 << PREVIEW_MAX_BITS):
    """Run complete factoring baselines for small synthetic N, not free QPU credit."""
    if n > limit:
        return dict(skipped="complete classical benchmarks exceed precommitted toy cap")
    plain = kernel.trial_division_factor(n).to_dict()
    wheel = kernel.wheel210_factor(n).to_dict()
    lfk = kernel.lfk_factor(n).to_dict()
    return dict(trial=plain, conventional_wheel210=wheel, ptp_LFK_kernel=lfk,
        note="full classical references; if solved, no practical quantum need exists")


def ptp_validate_recovered(n, factors):
    p, q = factors
    if p*q != n:
        return False
    if core.small_base_factor(n) is not None:
        return True
    actual = tuple(sorted((core.root_for_integer(p), core.root_for_integer(q))))
    return actual in core.candidate_factor_pairs(n)


def online_public_cf(n, base, m, y):
    """Online Shor CF denominator tests. NO private prime factors or true order."""
    stats = Counter()
    Q = 1 << m
    if y <= 0 or y >= Q:
        return dict(factors=None, candidate_order=None, denominator=None,
                    ledger=dict(stats), ptp_validated=None)
    x, den = y, Q
    prevprev, prev = 1, 0
    while den:
        q, rem = divmod(x, den)
        d = q*prev + prevprev
        if d > n:
            break
        stats["convergents_considered"] += 1
        if 1 < d <= n and d % 2 == 0:
            stats["even_denominators_checked"] += 1
            stats["modular_pow_calls"] += 1
            if pow(base, d, n) == 1:
                stats["modular_pow_calls"] += 1
                root = pow(base, d//2, n)
                for sign in (-1, 1):
                    stats["gcd_calls"] += 1
                    f = pair(math.gcd(root+sign, n), n)
                    if f:
                        valid = ptp_validate_recovered(n, f)
                        if not valid:
                            raise AssertionError("PTP rejected a mathematically valid gcd factor")
                        return dict(factors=f, candidate_order=d, denominator=d,
                                    ledger=dict(stats), ptp_validated=True)
        prevprev, prev = prev, d
        x, den = den, rem
    return dict(factors=None, candidate_order=None, denominator=None,
                ledger=dict(stats), ptp_validated=None)


def ideal_head_measurement(true_order, m, rng):
    """One ideal QPE outcome from 65 centered bins or full Q <=64.
    Events outside head are UNMODELED, counted, and never credited success.
    Only the isolated simulator gets true_order.
    """
    r = true_order
    s = rng.randrange(r)
    Q = 1 << m
    numerator = s*Q
    center, rem = divmod(numerator, r)
    if rem*2 >= r:
        center += 1
    offsets = (range(-Q//2, Q//2) if Q <= 65 else range(-W, W+1))
    mass = 0.
    u = rng.random()
    found = None
    bins_seen = 0
    for j in offsets:
        t = numerator - (center+j)*r
        if t == 0:
            p = 1.
        else:
            num = math.sin(math.pi*t/r)
            den = Q * math.sin(math.pi*t/(Q*r))
            p = (num/den)**2
        if not math.isfinite(p) or p < 0:
            raise AssertionError("Invalid QPE probability")
        mass += p
        bins_seen += 1
        if found is None and u < mass:
            found = (center+j) % Q
    if not -1e-8 <= mass <= 1+1e-8:
        raise AssertionError(f"Unnormalized head mass {mass}")
    tail = max(0., 1.-mass)
    if Q <= 65:
        assert tail < 1e-7, (Q,tail)
    else:
        assert tail <= 1./63+1e-6, (Q,tail)
    return dict(y=found, unmodeled_tail_event=found is None,
                theoretical_tail_mass=tail, head_mass=mass,
                evaluated_bins=bins_seen)


def sim_order_from_private_validation(p, q, base):
    """Private factor oracle ONLY for simulated ideal eigenphase generator."""
    N = p*q
    lam = math.lcm(p-1, q-1)
    return gates.multiplicative_order_from_lambda(base, N, lam)


def run_quantum_counterfactual(n, p, q, a, exponent, seed, shots_per_stage=4, gate_cache=None):
    """A full public reconstruction from ideal simulated measurements.
    p/q never enter preconditioning, online CF, gate construction or factor checks.
    """
    base = pow(a, exponent, n)
    guard = proper_factor_public(n, base)
    if guard is None:
        guard = public_power2_shortcut(n, base)
    label = f"L{exponent}"
    if guard:
        return dict(label=label, exponent=exponent, base=base,
            classically_shortcut=True, shortcut_factors=guard["factors"],
            model_attempted=False, success=False, factors=None, shots=0,
            note="public classical gcd/power2 shortcut; no quantum evidence")
    order = sim_order_from_private_validation(p, q, base)
    original_order = sim_order_from_private_validation(p, q, a)
    assert order == original_order // math.gcd(original_order,exponent)
    rng = random.Random(int.from_bytes(hashlib.sha256(
        f"UNIFIED-DARKSTAR-IDEAL|{seed}|{n}".encode()).digest(),"big"))
    # Same seeded random stream on each arm, but not a proof of paired QPE outcomes.
    stages = gates.stage_schedule(n, 4, 2)
    counters = Counter()
    gate_cache = {} if gate_cache is None else gate_cache
    per_stage=[]
    outcome = None
    for m in stages:
        stage_gate = gates.stage_arithmetic_count(n, base, m, gate_cache)
        stage_row = dict(m=m, shots_attempted=0, successful=False, source_CCX_per_shot=stage_gate["ccx"])
        for _ in range(shots_per_stage):
            counters["shots"] += 1
            counters["phase_rounds"] += m
            counters["source_CCX"] += stage_gate.get("ccx",0)
            counters["source_CX"] += stage_gate.get("cx",0)
            counters["source_CSWAP"] += stage_gate.get("cswap",0)
            stage_row["shots_attempted"] += 1
            reading = ideal_head_measurement(order, m, rng)
            counters["sampled_bin_evaluations"] += reading["evaluated_bins"]
            if reading["unmodeled_tail_event"]:
                counters["unmodeled_tail_events"] += 1
                continue
            check = online_public_cf(n, base, m, reading["y"])
            for k,v in check["ledger"].items():
                counters["public_CF_"+k] += v
            if check["factors"]:
                outcome=check
                stage_row["successful"]=True
                break
        per_stage.append(stage_row)
        if outcome:
            break
    width = gates.arithmetic_width(n)
    visited = per_stage[-1]["m"] if per_stage else 0
    # Both architectures share identical ideal phase distributions and arithmetic.
    arch = dict(wide_peak_logical=width["arithmetic_qubits_excluding_phase"]+visited,
                recycled_peak_logical=width["arithmetic_qubits_excluding_phase"]+1,
                arithmetic_workspace_logical=width["arithmetic_qubits_excluding_phase"],
                logical_phase_bits_wide=visited, logical_phase_bits_recycled=1,
                physical_hardware_metrics_measured=False)
    return dict(label=label, exponent=exponent, base=base,
        classically_shortcut=False, shortcut_factors=None,
        validation_only_order=order,
        validation_only_original_order=original_order,
        model_attempted=True, success=outcome is not None,
        factors=outcome["factors"] if outcome else None,
        verified_denominator=outcome["denominator"] if outcome else None,
        shots=counters["shots"], stop_phase_bits=visited,
        counterfactual_source_counts=dict(counters),
        logical_architectures=arch,
        stage_receipts=per_stage,
        head_only_success_lower_bound_method=True,
        tail_outcomes_not_falsely_credited=True)


def run_synthetic_case(p, q, base=None, seed=8776, fermat_tests=12):
    """Run actual classical-first and deliberately *counterfactual* quantum study."""
    if p == q or p < 2 or q < 2 or not ds.is_probable_prime(p) or not ds.is_probable_prime(q):
        raise ValueError("Use two distinct synthetic primes")
    n=p*q
    if n.bit_length()>PREVIEW_MAX_BITS:
        raise ValueError("CPU prototype intentionally restricted to <=26-bit synthetic semiprimes")
    a=public_base(n,base)
    public_ptp=ptp_public_metadata(n)
    classical=public_classical_preflight(n,a,fermat_tests)
    baselines=classical_reference_benchmarks(n)
    if classical["factors"]:
        assert classical["factors"]==[min(p,q),max(p,q)]
    for row in baselines.values():
        if isinstance(row,dict) and row.get("factors"):
            assert row["factors"]==[min(p,q),max(p,q)]
    arms = {}
    shared_arithmetic_cache = {}
    for exp in ODD_EXPONENTS:
        z=run_quantum_counterfactual(n,p,q,a,exp,seed,gate_cache=shared_arithmetic_cache)
        arms[z["label"]]=z
        if z["factors"]:
            assert z["factors"] == [min(p,q),max(p,q)]
    chosen_ell=3 if n%3==2 else 1
    choice=arms[f"L{chosen_ell}"]
    baseline=arms["L1"]
    classical_factor=classical["factors"]

    # PUBLIC-ORDER FALLBACK ROUTER: the choice and search priority are
    # determined entirely by N (not validation orders or observed successes).
    # A real hybrid would execute one arm at a time and retry only on failure.
    # Here the science harness independently scores all arms as counterfactuals;
    # the router reads only public shortcut or CF/GCD-recovered factor events.
    public_priority=[chosen_ell]+[e for e in ODD_EXPONENTS if e!=chosen_ell]
    fallback_trace=[]
    routed_factors=classical_factor
    routed_method="classical:"+classical["method"] if classical_factor else None
    if not classical_factor:
        for ell in public_priority:
            arm=arms[f"L{ell}"]
            if arm["classically_shortcut"]:
                routed_factors=arm["shortcut_factors"]
                routed_method=f"classical:public_odd_power_{ell}_gcd"
                fallback_trace.append(dict(exponent=ell,kind="classical_shortcut",
                                           factors=routed_factors))
                break
            fallback_trace.append(dict(exponent=ell,kind="ideal_QPE_simulation",
                                       factors=arm["factors"],shots=arm["shots"]))
            if arm["success"]:
                routed_factors=arm["factors"]
                routed_method=f"simulated_ideal_QPE_ell{ell}"
                break
    actual_result=dict(factors=routed_factors,
        success=bool(routed_factors),
        method=routed_method or "no_factor_within_cpu_model_budgets",
        publicly_fixed_odd_power_fallback_priority=public_priority,
        routed_quantum_or_classical_fallback_trace=fallback_trace,
        truly_requires_quantum_after_public_preflight=not bool(classical_factor),
        note=("Quantum branch was counterfactual; classical preflight already solved N."
              if classical_factor else "Remaining branch is IDEAL simulator, not a physical QPU."))
    def four_way(z,kind):
        if z.get("classically_shortcut"):
            return dict(architecture=kind, classical_shortcut=True,
                        success_in_simulator=None, factor_source="public classical shortcut")
        width=z["logical_architectures"]
        return dict(architecture=kind, success_in_simulator=z["success"],
            source_CCX=z["counterfactual_source_counts"]["source_CCX"],
            shots=z["shots"], stop_phase_bits=z["stop_phase_bits"],
            peak_logical_qubits=width[f"{kind}_peak_logical"],
            note="Same ideal QPE shots; wide vs recycled changes modeled logical width not source modular arithmetic CCX")
    four=dict(standard_plain_wide=four_way(baseline,"wide"),
              standard_plain_recycled=four_way(baseline,"recycled"),
              PTP_conditional_wide=four_way(choice,"wide"),
              PTP_conditional_recycled=four_way(choice,"recycled"))
    ptp_check = ptp_validate_recovered(n, [min(p,q),max(p,q)])
    assert ptp_check
    return dict(experiment="unified_dark_star_end_to_end_CPU_prototype",
        research_lead="Chase Lunsford / CaMaLabs", N=n,
        simulator_only_private_factors=[min(p,q),max(p,q)],
        public_base=a, public_PTPTables=public_ptp,
        public_conditional_odd_exponent=chosen_ell,
        public_classical_preflight=classical,
        classical_full_reference_baselines=baselines,
        actual_classical_first_outcome=actual_result,
        all_fixed_exponent_ablation_arms=arms, four_way_comparison=four,
        validated_PTProot_pair_after_real_factors=ptp_check,
        safety=dict(is_synthetic_toy=True, is_ideal_counterfactual=True,
                    uses_QPU=False, IBM_runtime_jobs=0, paid_runtime=False,
                    did_not_use_hidden_factors_for_public_decisions=True,
                    did_not_enable_naive_symmetry_pruning=True,
                    no_full_CF_factor_certificate_precomputation=True),
        limitations="No native transpiled/routed two-qubit gates, no hardware-fidelity prediction; classical benchmarks full-solve tiny N; head-only QPE misses unmodeled tails. No asymptotic/practical factoring advantage.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p",type=int,default=11)
    parser.add_argument("--q",type=int,default=19)
    parser.add_argument("--base",type=int,default=3)
    parser.add_argument("--seed",type=int,default=8776)
    parser.add_argument("--fermat-tests",type=int,default=12)
    parser.add_argument("--output",type=Path,
                        default=Path("results/dark_star_unified/unified_demo_N209.json"))
    args=parser.parse_args()
    z=run_synthetic_case(args.p,args.q,args.base,args.seed,args.fermat_tests)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(z,indent=2)+"\n")
    print("UNIFIED DARK STAR", "N",z["N"],
          "public base",z["public_base"],"chosen ell",z["public_conditional_odd_exponent"])
    print("Classical-first",z["actual_classical_first_outcome"]["method"],
          "factors",z["actual_classical_first_outcome"]["factors"])
    for k,v in z["all_fixed_exponent_ablation_arms"].items():
        print(k, "public shortcut" if v["classically_shortcut"] else
              ("factor" if v["success"] else "unresolved"),
              "shots",v["shots"])
    print("Whole-path receipt",args.output,"ZERO QPU",flush=True)


if __name__=="__main__":
    main()
