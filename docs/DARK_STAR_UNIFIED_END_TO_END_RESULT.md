# Unified Dark Star end-to-end: PTP + classical wheel/kernel/Fermat + odd powers + recycled adaptive Shor (CPU-only)

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-28. **Scope: verified runnable synthetic 8–10-bit demonstration**, NOT an independent QPE holdout, native circuit or real quantum factorization. IBM QPU jobs: **0**; paid IBM Runtime: **0**.

## Verified end-to-end system

[Protocol committed before implementation](DARK_STAR_UNIFIED_END_TO_END_PROTOCOL.md) (freeze commit `4573149614b1903080a6216fd08d8b961979a6e1`).
[Complete Python executable](../integrations/darkstar_hybrid/darkstar_unified.py) and [regression tests](../integrations/darkstar_hybrid/test_darkstar_unified.py).
[First complete successful GitHub Actions](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658837229); [second complete successful run including fixed public odd-power fallback router](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40659074991).

The code is ONE public-first pipeline with optional independent quantum **counterfactual** arms:
1. Compute public 48-root PTP modulo-210 coordinate, generated **24/28** kernel factor-pair row; show mirror/symmetry classes but never drop an actual pair merely due modular symmetry.
2. Check classical public `gcd(a,N)`, `gcd(a±1,N)`, 2/3/5/7 wheel primes, fixed repeated-squaring/GCD, capped ordinary Fermat, residue-filtered Fermat midpoint (M=105 and M=15015), Pollard stage1 B31, bounded Floyd rho, and prime-trial to97. **STOP classically immediately on verified factors.**
3. Separately benchmark full conventional trial, conventional wheel210 trial and actual PTP LFK/kernel factor-pair coordinate reference; complete search baselines are not falsely credited to the quantum path.
4. For simulated residual factorization, pick public base (or explicit user-supplied test base) and **public order of alternative exponents**: conditionally cube if N%3==2, then fallback in fixed sequence to the remaining exponents from (1,3,5,7,105,1155,15015) without using private order to select. Check public odd-power gcd/repeated-squaring factor shortcuts and classify as CLASSICAL when present. All seven arms recorded as counterfactual comparisons even if the classical pipeline already succeeds.
5. The private p,q synthetic test factors appear ONLY in the **ideal-QPE measurement source** and validation; selection and the online public-factor decoder receive only N,a,m,y. Simulated QPE uses an exact geometric-sum discrete probability for up to 65 centered bins/eigenphase (all Q bins when Q<=64), with omitted-tail probability explicitly counted; unmodeled tail never becomes a false factor success. Advance phase precision m=4,6,...2bitlength(N), four shots per stage.
6. Online strict continued fractions, even candidate d, `pow(base,d,N)==1`, and `gcd(pow(base,d/2,N)±1,N)` directly recover and verify factors, then ensure their PTP factor-root pair is in the generated row. No expensive offline O(N) list of all winning denominators; public modular-power/GCD costs recorded.
7. Per **actually attempted model shot**, count generic clean-MCX source CCX/CX/CSWAP from the repository's modular arithmetic source construction; measure wide vs iterative one-phase-recycled modeled peak logical width. *No compiled Qiskit/native gate cost or physical noise/fidelity is measured.* Everything is CPU only.
8. Full output includes each fixed odd exponent's factor shortcuts, simulated success/negative, stage/gate counters, all classical baselines, publicly chosen fallback trace, explicit classical-first/ideal-only boundary, and all four requested wide/recycled/PTP conditional architecture comparisons.

## First three reproducible synthetic end-to-end cases

All three **actually factor classically before the quantum simulator**, so real quantum computational need is **zero**. Quantum figures below are single fixed-seed **counterfactual ideal-model paths** and cannot establish practical speedup, absolute success probabilities or source-CCX-per-factor statistical confidence.

| Toy N (factors) | Classical-first actual result | PTP generated kernel row | Plain simulated QPE (L1) | Public conditional cubing (L3 if N%3==2) |
|---|---|---:|---|---|
| **209=11×19**, base3 | Ordinary Fermat, **1 square test** | 24 pairs | **no factor** in 28 shots; 3,658,744 source CCX | Factor in **10 shots**, 730,594 source CCX; validation r90→30 |
| **713=23×31**, base19 | Ordinary Fermat, **1 square test** | 24 pairs | Factor in **27 shots**, 7,366,012 source CCX | Factor in **18 shots**, 3,778,140 source CCX; validation r330→110 |
| **781=11×71**, base29 | Ordinary Fermat 12-test cap exhausted; PTP 105-midpoint found factor in **4 additional** square tests | 28 pairs | Factor in **18 shots**, 3,898,754 source CCX | **Public N mod3 condition not triggered**; same L1 arm |

**Interpretive controls:**
- N713 has a **single-path modeled** cubic source CCX decrease from 7.37M to3.78M (48.7%) and earlier simulated factor success. This is not independent/expected-value evidence or QPU hardware benefit; N713 factors immediately by ordinary Fermat.
- N209's baseline misses the fixed 28-shot cap while the cubic arm succeeds; **do not** compute a meaningful relative *cost per successful factor* from an unsuccessful baseline.
- N781 demonstrates that the public mod-3 selector **misses** an L7 order-reduction opportunity: the independently recorded `L7` arm has validation-only order70→10 and simulated factor recovery in8 shots/1,154,116 source CCX, but our predeclared selector uses L1. Selecting L7 *because its true order later proved smaller* would be hidden-order leakage; the public fallback sequence and all seven ablations preserve the distinction.
- The N781 PTP midpoint only did 4 exact squares after the ordinary Fermat stage already spent12; that is **16 combined** checks compared with a potential plain Fermat full search of14, and wheel-210 also finds N781 in5 division tests. The integration does **not** demonstrate overall classical-factor speedup, despite the PTP stage's useful filtering.
- The public L5, L105, L1155 and/or L15015 transformations in these small instances sometimes uncover factors from **public gcd/power2 shortcuts**; those are classical finds, never quantum wins. These transforms overlap Pollard p−1 preprocessing.

## Concrete archived originals

- [209 raw end-to-end JSON](../results/dark_star_unified/unified_demo_N209.json)
- [713 raw end-to-end JSON](../results/dark_star_unified/unified_demo_N713.json)
- [781 raw end-to-end JSON](../results/dark_star_unified/unified_demo_N781.json)

The CI verifies complete factor reconstruction and public PTP root containment, all seven fixed odd-power arms, true-order identity and witness parity in small cases, the distinction between classical-first and conditional ideal-only runs, exact head normalization and honest tails, 48 PTP roots and 24/28 pairs, non-use of unsafe symmetry factor pruning, matched wide/recycled source CCX, zero QPU. Source-level wide vs recycled logical width is not a physical-QPU claim.

## Reproduce

From repository root:

```bash
python3 -m unittest integrations.darkstar_hybrid.test_darkstar_unified -v
python3 -m integrations.darkstar_hybrid.darkstar_unified --p 11 --q 19 --base 3 --output results/dark_star_unified/unified_demo_N209.json
python3 -m integrations.darkstar_hybrid.darkstar_unified --p 23 --q 31 --base 19 --output results/dark_star_unified/unified_demo_N713.json
python3 -m integrations.darkstar_hybrid.darkstar_unified --p 11 --q 71 --base 29 --output results/dark_star_unified/unified_demo_N781.json
```

## What is **not** combined by assertion

- PTP mirror symmetry is NOT used to delete factor candidates: previously falsified for fixed-N factorization.
- PTP residues are not secretly a guaranteed order oracle. Baseline/postprocessing cannot reject valid Shor candidate denominators without proof.
- Large-exponent order truncation alone is not a demonstrated quantum resource gain; tests record classical shortcuts and negative cases.
- The **full expected cost** of realistic noise-tolerant QPE, on-device measurement/reset/feedforward, native gates, error correction, and QPU runtime remains unimplemented here. Head-only ideal-QPE results give *lower credits* for success, not a faithful complete sampled hardware distribution.
- All three tiny Ns have classical solutions; the simulator's p/q input is deliberately only a truth source. This is an **integrated, unit-tested algorithm and transparent research harness**, not a general RSA/ML-KEM break or new asymptotic Shor improvement.
- The fixed recent N25 cubic negative findings and the earlier positive conditional findings **remain separate**. The newly integrated examples are not a new N25 or larger-bit holdout.

**Next scientific gate:** precommit a fresh public-only moderately larger semiprime population after a bounded classical pipeline, keep only genuinely unsolved cases for estimating practical quantum need without suppressing classical-solved controls, and compare the exact same public input across plain/wheel/PTP/multi-power QPE with a complete QPE tail sampler and native-circuit viability constraints. Avoid any paid or real QPU run without explicit authorization.
