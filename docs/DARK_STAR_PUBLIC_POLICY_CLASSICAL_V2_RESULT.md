# Dark Star v2 — public-policy, classical-first falsification result

Date: 2026-10-14  
Research lead: Chase Lunsford / CaMaLabs  
Status: **COMPLETE** — 144/144 preregistered rows, three independent ell shards, no IBM/QPU submission.

## Provenance

- Frozen-before-scoring protocol: `docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_PREREG.md`, commit `24d0e4e1dc088741ffa891c4bf81174b8e3a1234`.
- Executor: `hardware/dark_star_public_policy_classical_v2.py`; population combiner: `hardware/analyze_dark_star_public_policy_classical_v2.py`.
- Original computational run (three successful shards, verified merge, failed **Git push only** due to concurrent main update): [38669629155](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669629155).
- Independent artifact-recovery/fast-forward workflow (success, no force push): [38669941950](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669941950).
- Final canonical JSON: `results/dark_star_ptp/dark_star_public_policy_classical_v2.json`.
- Frozen public manifest SHA-256:
  `ffc2b217f0ed2faddf33f04f08e06ab4813d30220054faa4768a64547de3d29c`
- Assertions verified: all 144 public-selected rows, exactly 24 per ell/group, matching manifest order and hash, zero odd-power order-identity violations, zero witness-preservation violations, and `zero_qpu: true`, `qpu_jobs_submitted: 0`.

This is an independent fresh **18-bit** population, N=131072..262143, disjoint from v1. Each row uses one of three fixed ell values and the preregistered public SHA-rotated coprime base. There is no post-outcome reselection.

## Main new outcome: classical preprocessing consumes the population

Of **144 selected rows**, bounded trial division (primes <=43), public power-of-two/GCD checks, and the frozen Pollard p-1 B1=43/B2=79 stage1+stage2 procedure classically factor **114** before quantum work. Thus **79.17%** of the 144 selected *ell-specific rows* are already classically solved at this toy size; only **30** require further modeling, of which **23** meet the stricter paired factor-witness/quantum-guard conditions.

| ell | group | selected | solved by common public classical checks | unsolved | paired eligible |
|---:|---|---:|---:|---:|---:|
| 3 | trigger | 24 | 17 | 7 | 5 |
| 3 | control | 24 | 19 | 5 | 5 |
| 5 | trigger | 24 | 21 | 3 | 2 |
| 5 | control | 24 | 18 | 6 | 5 |
| 7 | trigger | 24 | 19 | 5 | 3 |
| 7 | control | 24 | 20 | 4 | 3 |

Rows are `(N,ell)` experiment entries, not necessarily 144 different integers N. These classical success rates reflect the **small 18-bit sample and frozen classical budget**, not predictions for RSA-scale factoring.

## Frozen primary eligible-pair comparison

All values are transformed / untransformed ratios of **expected logical arithmetic CCX** under the same scalable clean-ancilla polynomial gate counter. Below 1 means fewer expected CCX. The numerator and denominator are summed *within* each eligible group. Reported bootstrap intervals are 2000 frozen-seed resamples (95% percentile), with small-sample limitations.

| ell | group | eligible | aggregate CCX T/B | modeled CCX reduction | improved / tied / worsened | 95% bootstrap CI |
|---:|---|---:|---:|---:|---:|---|
| 3 | trigger | 5 | **0.900389** | **9.96%** | **2 / 0 / 3** | [0.7806, 1.0124] |
| 3 | control | 5 | 0.939784 | 6.02% | 2 / 0 / 3 | [0.7861, 1.0159] |
| 5 | trigger | 2 | 0.881745 | 11.83% | 1 / 0 / 1 | [0.7125, 1.0127] |
| 5 | control | 5 | **0.819095** | **18.09%** | 3 / 0 / 2 | [0.6520, 0.9579] |
| 7 | trigger | 3 | **1.013418** | **1.34% higher cost** | **0 / 0 / 3** | [1.0091, 1.0170] |
| 7 | control | 3 | 1.008471 | 0.85% higher cost | 0 / 0 / 3 | [1.0008, 1.0186] |

**Interpretation:**
- **ell=3** again has a favorable trigger-vs-control *aggregate direction*. But the 95% bootstrap CI includes ratio=1 and a majority of eligible trigger rows **worsen**. This is NOT a robust per-row policy improvement.
- **ell=5** fails the prespecified trigger-enrichment comparison again (0.8817 > control 0.8191); the trigger estimate depends on only **two** paired rows. The direction of overall savings does not rescue that frozen failure.
- **ell=7** is a negative replication on this population: no eligible trigger row improves, and changed modular constants make arithmetic slightly more expensive despite no phase-round reduction.
- Bootstrap CIs with n=2,3,5 are descriptive and should not be treated as strong inferential evidence.

## Mechanism isolation and stricter public verification

This study changed the stopping-success condition. It no longer credits any continued-fraction denominator merely for being a hidden-order multiple: the decision is **public** `pow(a,d,N)==1`, an even d, and a nontrivial factor from `gcd(a^(d/2) +/- 1,N)`. Hidden factors/orders are only for ideal-QPE phase-generation and audit. The earlier hidden-order-only score remains a diagnostic, not a success claim.

| ell | group | phase-round T/B | CCX-per-executed-round T/B | CCX T/B |
|---:|---|---:|---:|---:|
| 3 | trigger | 0.893353 | **1.007876** | 0.900389 |
| 3 | control | 0.927497 | **1.013247** | 0.939784 |
| 5 | trigger | 0.861299 | **1.023739** | 0.881745 |
| 5 | control | 0.810616 | **1.010460** | 0.819095 |
| 7 | trigger | 1.000000 | **1.013418** | 1.013418 |
| 7 | control | 1.000000 | **1.008471** | 1.008471 |

Where savings appear, their cause remains earlier stopping. Transformed arithmetic is **not cheaper per executed phase round** in any subgroup.

## Public policies over all 30 common-classical-unsolved entries

These are separate from the paired-eligible table; the denominator sums modeled quantum arithmetic across all 30 rows that the common classical prefilter did not factor. A transformed classical shortcut is credited as **zero quantum cost** but its public preprocessing ledger is recorded; therefore these numbers are **not** a pure quantum advantage.

| public policy | aggregate modeled CCX vs never-transform |
|---|---:|
| always-transform | 0.954642 (4.54% lower) |
| trigger-only | 0.985584 (1.44% lower) |
| conservative ell=3 | 0.990161 (0.98% lower) |
| never-transform | 1.000000 (reference) |

The classical ledger records trial remainders, gcd operations, square-and-multiply equivalents, extra odd-power transform and transformed-base public checks. Classical operations and logical quantum CCX are different units and **cannot simply be added**. The per-row JSON also records modeled factor-success-by-cap to prevent a cheaper *unsuccessful* policy from masquerading as an advantage. The population-level quantum CCX ratios are conditional metrics, not total factoring wall-clock comparisons.

## Independent recycling-width result (not multiplied into Dark Star)

Each selected N has 18 work bits. The existing clean-ancilla generic arithmetic model uses:
- work register: 18; accumulator: 19; reduction flag: 1; clean MCX scratch: 19;
- **57** coherent arithmetic qubits irrespective of phase architecture;
- wide phase cap 36: **93** simultaneous logical qubits;
- recycled phase register 1: **58** simultaneous logical qubits;
- phase-register recycling alone: **35 qubits / 37.63% less peak logical width**.

No Dark Star exponent is credited with reducing those 57 coherent arithmetic qubits. These are generic logical resource counts, not physical fault-tolerant resources or exact Nighthawk/Phoenix data.

## Caveats and next falsification

The 18-bit population is **too easy for the fixed classical-preprocessing budget**; only 23 paired quantum-eligible rows survive, leaving underpowered subgroup inference. This is not a failed implementation: it is a scientifically useful stronger null/cautionary result. The original v1 17-bit scout/holdout and its optimized-placement compiler milestones remain separately valid for their stated questions.

Prioritize:
1. A larger 20–24-bit held-out range to retain more quantum-eligible rows under the same **bounded classical budget**, with a frozen ceiling and performance-aware exact nearest-bin scoring (not weaker stopping).
2. Separate the **public policy deployment** issue (selection of ell itself) from the per-ell controlled experiments; do not assume the oracle determines the right ell.
3. Compare success-adjusted work, public classical effort and quantum-width constraints on the same complete policy; do not claim overall quantum value from a favorable eligible-only CCX ratio.
4. Keep zero-QPU by default, never authorize IBM paid runtime or an ambiguous plan.

**Claim boundary:** no measured QPU speedup/fidelity, scalable deployed factoring, RSA-2048 break, altered Shor asymptotics, or general superiority of transformed bases is established.
