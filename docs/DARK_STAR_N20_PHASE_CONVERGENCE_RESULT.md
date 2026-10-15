# Numerical convergence result — independent 8192-phase check of frozen n20 v3

Date: 2026-10-14 Pacific (Actions 2026-10-15 UTC). Research lead Chase Lunsford / CaMaLabs.

## Experiment provenance and scope

- **Pre-registered BEFORE rerun:** `docs/DARK_STAR_N20_PHASE_CONVERGENCE_PREREG.md`, commit `7db0fb9ca685aa24480997081dae51e9d74c8138`.
- **Unmodified original 4096-phase result:** `docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_RESULT.md`, source Actions [38677893149](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677893149).
- **Independent 8192-phase runner:** `hardware/dark_star_n20_phase_convergence.py`.
- **Completed numerical replicate:** [Actions run 38678433078](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38678433078), six computational jobs **SUCCESS**; strict six-panel artifact verifier + safe GitHub commit **SUCCESS**.
- **Unchanged pre-outcome public N/base manifest:** SHA256 `a952fa4b57496136b29df7a3aca54a4361d4ec6ed5e0ee76c796602d5e840782`.
- **All six complete committed replicate receipts:** `results/dark_star_ptp/dark_star_n20_phase_validation_ell{3,5,7}_{trigger,control}.json`. All 72 originally selected classical-survivor N retained; no private-order resampling.

Only the model's finite phase-eigenvalue sampling is changed: 4096 draws using original seed vs **8192 new independent seeded draws** per stage for r above the cap, exhaustive r enumeration for smaller r. The factor-producing public CF/GCD predicate, matched polynomial arithmetic CCX counting, 4/6/.../40-bit stages, four ideal-QPE shots/stage, and public no-transform/cube/ladder/cheap policies are frozen. The same N, base, factor witness and oracle validation metadata are retained. No QPU, IBM Runtime or paid plan used.

## Trigger-group numerical result

Aggregate ratio = sum of modeled expected CCX **per successful factor-producing staged session with independent restarts**, on the same matched both-positive cases.

| Public-N trigger stratum | ladder/plain original 4096 | ladder/plain independent 8192 | absolute drift | ladder/always3 original | ladder/always3 independent |
|---:|---:|---:|---:|---:|---:|
| ell3 trigger | 0.832899 | **0.837287** | +0.004388 | 1.000000 | **1.000000** |
| ell5 trigger | 0.799052 | **0.799469** | +0.000418 | 0.994597 | **0.995238** |
| ell7 trigger | 0.806628 | **0.806123** | −0.000505 | 0.965400 | **0.965520** |

All three trigger ladder/plain comparisons keep the original **same paired coverage and improving/worsening tallies**: ell3 7/0/2; ell5 8/0/2; ell7 7/0/2. None exceeds the pre-registered 0.03 absolute ratio-drift alarm. These are meaningful numerical reproducibility receipts for the **conditional ideal-model directional effect versus no transform**.

Against the simpler **unconditional cube**, ell3 remains **exactly identical** (0/9/0 improving/tied/worsening). Ell7 is also directionally stable but only 2 improving, 5 tying, 2 worsening individual comparable rows. Ell5 is **not fully stable at row level**:

- original: ladder/always-cube 0.994597, **2 improvements / 7 ties / 1 worsening**;
- new: 0.995238, **1 improvement / 7 ties / 2 worsenings**.

Thus one tiny individual advantage reversed under the different seeded phase estimator, even though the aggregated ratio stayed slightly below one. This is evidence of **near-parity numerical sensitivity**, and the claim of reliable incremental multi-exponent superiority over always3 **remains UNESTABLISHED**. Existing row bootstrap intervals for ell5/ell7 cube comparisons already included parity.

## Frozen control-group replication

| Public-N control stratum | ladder/plain original | ladder/plain independent | ladder/always3 original | ladder/always3 independent |
|---:|---:|---:|---:|---:|
| ell3 control | 0.905899 | **0.907226** | 0.936420 | **0.937670** |
| ell5 control | 0.921312 | **0.920674** | 1.052022 | **1.052058** |
| ell7 control | 0.878261 | **0.877723** | 0.932937 | **0.933364** |

These six-panel means/aggregate ratios move by no more than ~0.0044 in absolute terms across the two independently seeded calculations. This is **numerical corroboration**, not a new held-out N replication, and two seeds do not establish rigorous confidence bounds for the nonlinear stopped-QPE cost ratio.

## Interpretation and limitation

**Durable milestone:** the pre-registered 20-bit classical survivor study can be reproduced on identical 72 public-selected N with a different, higher-resolution random-phase estimator. The main 16–20% conditional modeled CCX-per-success directional ladder/plain savings in the three trigger strata are largely invariant to the seed/sample-size change.

**Critical separation:** 'ell5 trigger' and 'ell7 trigger' are **N-residue strata**, not evidence that choosing exponent 5 or 7 beats cube. The ladder prioritizes exponent 3 whenever available, and does **not** establish extra reliable value over **always-cube**. Do not overwrite earlier independent negatives for residue-conditioned ell5/ell7 or ignore zero-success cases.

**Numerical caveat:** the 8192-sample worst-case Hoeffding 95% error bound on an individual sampled per-stage success probability is about **±0.0150**, not an interval for the aggregate CCX ratio. Both runs use the same approximate nearest-bin-only ideal-QPE simulator, **not exact full-bin quantum phase measurements**. The case bootstrap and independent sample stability do not capture actual QPU calibration/fidelity/time.

**Independent width statement unchanged:** 20-bit generic arithmetic occupies 63 coherent logical qubits. Wide peak 103 vs phase-recycled peak 64 logical qubits (37.86% width saving); this is independent of Dark Star and not an estimate of fault-tolerant physical qubits.

The next new-population falsification should make **always-cube** the primary baseline, consider classical processing effort and success coverage, preserve exact public factor verification, and preregister any sampling/precision budget before N inspection. Zero-QPU default, no paid IBM Runtime.
