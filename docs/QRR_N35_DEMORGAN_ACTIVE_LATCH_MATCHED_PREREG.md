# FROZEN — De Morgan zero-CX N35 comparator with active-only RCCX cached latch, 8 matched seeds, ZERO QPU

**Research lead / original program:** Chase Lunsford / CaMaLabs. October 17 Pacific / October 18 UTC 2026. Frozen before any new native compilation or independent result, no hardware jobs permitted. Both public bases N35, a2 and cube8; CPU Qiskit compilation to READ-ONLY IBM Fez hardware target only, no Open/free or paid QPU runtime, no Sampler or Estimator, no future QPU job.

## Frozen verified prior and motivation

The current strongest **phase-exact and cross-seed robust** public N35 six-bit full-residue **single controlled multiplier** is [`QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md`](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md), original archived JSONs `results/ibm_shor35_demorgan_zero_cx_or/qrr_n35_demorgan_zero_cx_base{2,8}.json`. It passes the full exact complex quantum phase+1 test, has application width32 and all 25 initially/returned-clean auxiliary bits, and outperforms its older original and one-CX OR controls in BOTH native CZ and depth **8/8 fixed seeds PER PUBLIC BASE**. Frozen opt1 seed8776 native Fez CPU targets: **base2 CZ7993/depth18604**, **cube8 CZ8758/depth20575**; full source gate distribution base2 CX349/RCCX596/X1738/CCX160, cube8 CX357/RCCX616/X1828/CCX162. Hardware gate preflight immutable CZ<=800 and depth<=2000; both fail by order of magnitude, ZERO QPU.

Earlier `active_only` cached control lattice RCCX experiment on the *older comparator*, [`QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md`](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md), failed strict paired two-base robustness (base2 5/8 joint improvements, cubic base8 1/8). **This new interaction is NOT known to succeed and MUST NOT be promoted from a favorable seed.**

A newly completed separate [source-X-inverted OR comparator robustness trial](QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_RESULT.md) passed 8/8 and6/8 vs the older original, but did not displace De Morgan. The present De Morgan+active experiment is a *distinct second-stage* fixed candidate, not another OR polarity search.

## EXACT ONE COMPONENT, unchanged clean public arithmetic

Build OLD `DeMorgan` via `qrr_n35_relative_phase_ripple_carry.verified.build(base)` after setting shared `primitive.predicate = qrr_n35_demorgan_zero_cx_or_multiseed.demorgan_ripple_predicate`. Build ONE candidate with this *same comparator*, same cached enable and exact prefix-carry public modular additions, **but switch only the two active cache latch compute+uncompute operations** `active=phase AND valid` from original exact CCX to exact Qiskit `RCCXGate()` and `RCCXGate().inverse()`. Keep all 24 enable latch CCX and ALL exact semantic target flips unchanged. No other circuit change, no extra helper register, no source order/orbit table, no hidden prime factors. Use previously tested `qrr_n35_relative_phase_latch_families.build_variant(base,"active_only")` constructor after the comparator patch; it modifies precisely these 2 active CCXs.

**Source gate counts must be identical to DeMorgan except RCCX+2/CCX−2 and unmodified CX/X:** base2 comparator-only `{cx349,rccx596,x1738,ccx160}` vs candidate `{cx349,rccx598,x1738,ccx158}`, cube8 original `{cx357,rccx616,x1828,ccx162}` vs candidate `{cx357,rccx618,x1828,ccx160}`. Both width32 with 25 auxiliaries. Output correct for all 64 y with both 0/1 phase controls; identity for y>=35 or external control0, all quantum output amplitudes EXACT +1 complex on initially zero helpers. RCCX inverse operator identity must be checked (do not assume gate name is dagger; Qiskit might call inverse `rccx`).

## Exact frozen gate proof BEFORE compiler/target access

Use actual emitted Qiskit `Operator(inst.operation)` monomial phase-aware interpreter, not a Boolean shadow simulator:

1. 4/4 public De Morgan OR identity cases and actual RCCX/adjoint operator identity; 8/8 local `active` relative-phase cache latch controlled-probe unitary cases, both initial probe bits, controls, clean latch, exact phase+1.
2. 42,672/42,672 actual-gate public-width1..6 De Morgan comparator cases for all public thresholds, sign polarity, external enable and initial output flag, exact amplitude +1 and temporary workspace zero.
3. 1,584/1,584 actual-gate 16 public constant modular-add cases per base, all valid active and 64 disabled inputs, exact +1 phase, wrap/carry/scratch clean.
4. 128/128 original AND 128/128 active-only full source controlled multipliers per base (all six-bit y and control c), exact coherent amplitude +1, correct public output / invalid identity, all 25 helpers clean, source counts exactly +2RCCX−2CCX and no other gate changes.
5. Only after 1–4 pass, read IBM Fez hardware target metadata from the protected API key and CPU compile; NO submission of quantum jobs.

## FIXED 8 matched seeds, outcome gates and original receipt preservation

Exactly **eight fixed Qiskit seeds** `[11,37,101,409,8776,12011,20261,45673]`, same Qiskit~=2.5.2 / qiskit-ibm-runtime~=0.47.0, transpiler optimization1, same backend target object and circuit widths, original comparator-only then candidate `active_only` in each seed, eight pairs per public base×2 designs×2 bases=**32 CPU-native compilations**. Preserve per seed full native count_ops/CZ/depth/ISA width/size/elapsed and paired changes `candidate-original`, medians/min/max, CZ-only/depth-only/joint improvements. No tuning or choosing a favorable seed.

Frozen historical 8776 baseline anchor **must exactly reproduce** base2 DeMorgan CZ7993/depth18604 and cube8 CZ8758/depth20575. If anchor differs, classify cross-run comparison INCONCLUSIVE, do not claim robust pass.

**Engineering pass ONLY IF BOTH public bases** phase prove, have +2RCCX source gate confirmed, all 8 paired seeds compile, original seed8776 exact anchor, **≥6/8 seeds with BOTH strictly lower native CZ and depth than the matched DeMorgan base design**, and **median paired CZ delta <0 and median paired depth delta<0** per base. Failure or regression still archived, do not weaken.

**Separate hardware gate CZ≤800 AND depth≤2000** for both bases; every real QPU device submission is explicitly prohibited in this experiment regardless of outcomes. This is one controlled N35 modular multiplier, not full QPE, real N35 factor recovery, RSA-scale cryptanalysis or a theorem. Independently audit/preserve original unchanged artifact JSON after experiment, retaining all previous wins and failures.
