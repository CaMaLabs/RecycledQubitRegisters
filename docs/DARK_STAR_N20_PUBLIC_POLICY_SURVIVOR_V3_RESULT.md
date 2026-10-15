# 20-bit Dark Star public-policy classical-survivor v3 — verified result

**Date:** 2026-10-14 (Pacific; Actions 2026-10-15 UTC). **Research lead:** Chase Lunsford / CaMaLabs. Zero IBM Runtime/QPU submissions. No hardware fidelity, clock-time, fault-tolerant physical-qubit or RSA-2048 claims.

## Provenance, freeze and experimental scope

This is an entirely new, disjoint 20-bit semiprime population, distinct from the 17/18-bit selected scouts and holdouts. All earlier successful **and negative** results remain valid within their respective designs.

- [Pre-registered design](DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_PREREG.md), committed **before hidden-order/QPE/resource scoring** at `71c84b5d0eda809f1c39c75ad62052f2bb0e38a9`.
- [Frozen public manifest](../results/dark_star_ptp/dark_star_n20_public_survivors_v3_manifest.json), committed in [manifest-freeze Actions 38677771046](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677771046) before the quantum-model workflow.
- SHA-256 over canonical selected public manifest: `a952fa4b57496136b29df7a3aca54a4361d4ec6ed5e0ee76c796602d5e840782`.
- [Scoring + six-shard integrity merge Actions 38677893149](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677893149) **SUCCESS**, six out of six computational shards plus strict manifest-hash/row-consistency validation and non-forced safe commit of raw receipts.
- [Full merged result](../results/dark_star_ptp/dark_star_n20_v3_full_holdout.json) and six `results/dark_star_ptp/dark_star_n20_v3_ell{3,5,7}_{trigger,control}.json` raw files, all committed, complete.
- [Runner](../hardware/dark_star_n20_public_survivor_v3.py) and [strict merger](../hardware/analyze_dark_star_n20_public_survivor_v3.py).

Frozen semiprimes `524288 <= N <= 1048575` (20-bit), `p<q`, both prime, `p>=11`. Six panels: ell=3,5,7 crossed with public trigger/control N mod ell. Public-N SHA256 rank, deterministic coprime base pool, **public-only** gcd/power-of-two GCD/Pollard-p−1 B31 preprocessing, and first **12 classical survivors per panel** with panel-wise 400-candidate screen ceiling. Later panels exclude prior selected N, guaranteeing **72 distinct N**. The hidden factors and orders are validation-only and cannot determine public eligibility, base or transform policy.

**Public screening milestone:** **293** synthetic semiprime candidates screened, **221** factored classically by the *bounded frozen public filter* (**75.43%**); **72 distinct public-classical survivors** carried into model scoring. The complete 293-row public screening ledger was retained in the manifest; no classically solved case was quietly discarded.

| Panel | Public candidates screened | Factored by frozen public filter | Survivors modeled |
|---|---:|---:|---:|
| ell3 trigger | 55 | 43 | 12 |
| ell3 control | 55 | 43 | 12 |
| ell5 trigger | 41 | 29 | 12 |
| ell5 control | 37 | 25 | 12 |
| ell7 trigger | 51 | 39 | 12 |
| ell7 control | 54 | 42 | 12 |
| **Total** | **293** | **221** | **72** |

## Frozen comparison and *numerical approximation*

Compare fully public policies on each surviving `N,a`:

- `plain` — no transform;
- `always3` — always use `a³ mod N`;
- `cube_trigger` — cube only when `N mod 3==2`;
- `ladder` — first applicable exponent 3→5→7 based on the public residue, else no transform;
- `cheap4` — minimum four-phase-bit public generic arithmetic CCX proxy, ties in fixed exponent order.

A proposed continued-fraction denominator is accepted **only with a public nontrivial factor** from even d, `pow(a,d,N)==1`, `gcd(a^(d/2) ± 1,N)`. The order is used only to simulate ideal phase values and check the known odd-power identity. The modeled resource counter is the repository's generic polynomial reversible arithmetic **logical CCX**, with staged QPE four shots per precision 4,6,...,40 bits, preserving the 63 coherent arithmetic qubits.

**Do not call this exact full QPE:** to keep 20-bit population modeling feasible, the estimator was *pre-registered BEFORE outcomes* to exhaustively enumerate validation eigenphases for `r<=4096`, and otherwise use **4096 seeded uniform eigenphase numerators per stage**, shared across policies. This is a **nearest-bin-only ideal-QPE approximation**, not the exact all-bin distribution. A worst-case Hoeffding 95% absolute per-stage probability bound is approximately **±0.02122** when sampled; that is *not* a 95% bound for the final weighted CCX ratios after nonlinear stopping. The row-bootstrap intervals below measure across-case dispersion, **not phase-sampling error**. Conclusions near parity require independent numerical convergence checks.

## Frozen primary trigger endpoints — ladder vs plain

Metric: sum of `expected logical CCX / probability of factor-producing success by cap` for **both-positive comparable cases** only, divided by the matched plain sum. Ratio below one indicates modeled expected CCX savings **per successfully factor-producing staged session with hypothetical independent restarts**. Success-zero/noncomparable rows are counted separately, not hidden; total per-attempt ratios use **all 12 survivors**.

| Public ell-stratification | Comparable / 12 survivors | Ladder/plain modeled CCX-per-success ratio | Improv./tie/worse | 2000-row-bootstrap 95% CI | All-12 per-attempt CCX ratio |
|---:|---:|---:|---|---|---:|
| **ell3 trigger** | 9/12 | **0.832899** (16.71% less) | 7/0/2 | [0.7723, 0.9061] | 0.900575 |
| **ell5 trigger** | 10/12 | **0.799052** (20.09% less) | 8/0/2 | [0.7443, 0.8702] | 0.865116 |
| **ell7 trigger** | 9/12 | **0.806628** (19.34% less) | 7/0/2 | [0.7443, 0.8825] | 0.885604 |

Across all three trigger panels, the ladder retains modeled factor-production coverage equal to plain (9/12, 10/12, 9/12 respectively). On comparable cases, improved rows form a bare strict majority in every trigger panel, and the aggregate ratio is below one. Thus **the frozen trigger-vs-plain directional gate passes** under the pre-registered **finite-phase-sample ideal model**.

The *ell labels here identify how N was stratified*, **NOT which exponent the ladder used**. An ell7-trigger row can be transformed by the cube (ell3), and an ell5-trigger row can also use the cube. This study **does not reverse** the earlier failures of the standalone ell5 residue-enrichment selector or ell7 transform.

## Crucial control: ladder versus simple unconditional cube

The earlier n18 multi-choice study showed a cube-equivalent ladder on trigger panels. The v3 preregistration therefore required testing ladder **against always3**, not only against plain.

| Public panel | Both success | Ladder / always3 modeled CCX per success | Improve/tie/worse | Row-bootstrap 95% CI |
|---|---:|---:|---|---|
| ell3 trigger | 9 | **1.000000** | 0/9/0 | [1.0000, 1.0000] |
| ell5 trigger | 10 | 0.994597 | 2/7/1 | [0.9822, 1.0008] |
| ell7 trigger | 9 | 0.965400 | 2/5/2 | [0.8755, 1.0465] |

Formally, the frozen broader gate—directional trigger superiority to plain, equal success coverage, one panel slightly beating always3, and no trigger panel worse than always3—**passes as written**. **However, the stronger claim that multi-exponent selection reliably beats plain cubing is NOT established**: ell3 is exactly identical, and ell5/ell7 bootstrap intervals include 1. The apparent differences are a few small cases and may be affected by eigenphase sampling uncertainty. Do not describe this as a large independent ell5 or ell7 gain.

## Control strata: no universal pattern

| Public panel | Both success | Ladder/plain ratio | Improve/tie/worse | 95% row-bootstrap CI |
|---|---:|---:|---|---|
| ell3 control | 7/12 | 0.905899 | 2/0/5 | [0.7773, 1.0159] |
| ell5 control | 10/12 | 0.921312 | 4/1/5 | [0.8393, 0.9945] |
| ell7 control | 9/12 | 0.878261 | 6/2/1 | [0.8024, 0.9539] |

The ell3 control's **5/7 worse** cases are a direct warning against equating aggregate improvements with robust per-row benefits. Controls are not zero-opportunity placebos; they are controls only for each specific `N mod ell` residue criterion.

## Mechanism, width and claim boundary

Where lower CCX appears, the observed per-attempt ratios (0.9006/0.8651/0.8856 for three trigger panels) track reduced sequential phase rounds (0.8896/0.8542/0.8737), not a general cheap-modular-multiplier advantage. One-qubit phase recycling separately reduces peak simultaneous **logical** width:

- coherent arithmetic workspace **63** qubits, unchanged;
- `wide` with 40 phase qubits **103** total;
- `recycled` with one phase qubit **64** total;
- **39 logical qubits saved / 37.86% lower simultaneous width**.

The narrower research milestone is **positive, conditional ideal-model signal for the public ladder relative to unchanged base among 20-bit semiprimes surviving a cheap classical screen**. The broader general selector advantage **over unconditional cube** remains unproved. These numbers are *not* measured QPU speed/fidelity, fault-tolerant physical resources, exact full-bin QPE, full quantum/classical factoring wall-clock comparison, an asymptotic improvement to Shor, or an RSA-2048 break. Neither the known odd-power identity nor iterative phase recycling is presented as wholly new mathematics.

## Next independent falsification

Before updating a public claim about multi-exponent selection, freeze **independent phase-sampling seeds / higher phase budget** on the **same already locked N** (this is numerical-convergence validation, not new population replication), then replicate with **new disjoint N** if direction survives. Report whether the tiny ladder-vs-always3 differences remain after varying numerical estimator seed and whether a real policy can beat an always-cube classical/quantum baseline once the cheap public checks and model success coverage are included. Keep zero-QPU and preserve earlier negative results.
