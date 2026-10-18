# VERIFIED NEGATIVE ROBUSTNESS — N35 phase-exact active-only latch: 5/8 paired wins base2 and 1/8 cubic base8, frozen 6/8 gate FAIL, zero QPU

**Research lead / originating program: Chase Lunsford / CaMaLabs.** Experiment October 17, 2026 PDT (original native compiler artifact timestamps October 17 UTC). The work compiled two six-bit N35 controlled **single** modular multipliers against read-only IBM Fez native target metadata using a CPU; it did **NOT** run QPU shots, measure physical device fidelity, execute full Shor quantum phase estimation, consume free or paid IBM Runtime, or demonstrate cryptographic advantage.

## Why this experiment, with prior wins intact

The previous verified [relative-phase temporary carry comparator result](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) reduced the full-residue controlled-multiplier CPU native Fez target cost to **base2 CZ9263/depth21772** and **cube8 CZ9426/depth21933**, 32 logical source qubits, 25 returned-clean helpers, with complete exact +1 quantum-phase tests. The later [phase-correct isolated latch family study](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_RESULT.md) found the **active-only** change (RCCX and exact inverse for the single cached active=phase&valid latch pair) yielded *in that one fixed seed8776*: base2 **CZ9042/depth21541**, cubic base8 **CZ9156/depth21820**. Both single-seed arms had strict CZ/depth savings but real-QPU native feasibility failed (frozen original **CZ≤800 AND depth≤2000** even for ONE controlled multiplier). The older enable-only change worsened cubic depth at seed8776; the combined-latch candidate also had mixed base8 outcomes. All predecessor original JSON receipts remain unchanged.

The new scientific question is NOT whether that matched single-seed improvement exists—it does—but whether this is robust to Qiskit transpiler seed/placement variations. The [new preregistration](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_PREREG.md), pre-scoring git commit **`0836b38892e0069a718ec0e47d3a3567f3db29a0`**, freezes the 8 EXACT seeds `[11,37,101,409,8776,12011,20261,45673]`, SAME two existing source circuits, **two independent public bases**, exact unchanged backend/native target, Qiskit~=2.5.2/runtime~=0.47.0, optimization1, and no post-result selection. For each seed it compiles `neither` and `active_only` as a **matched pair** using identical parameters and backend object. **32 actual native CPU compilations = 8 seeds × 2 bases × 2 circuits.** Not a study of QPU shot noise or fluctuating calibration.

Frozen **robustness criterion** required BOTH bases to show **≥6/8 seeds with BOTH strictly lower CZ AND lower depth**, median *paired* CZ and depth improvements, exact historical seed8776 reproduction and complete phase correctness. No weakening to "some seeds" after seeing the outcome. A separate immutable N35 hardware gate remains CZ≤800 AND depth≤2000 with NO QPU submission in any case.

## Exact emitted-gate quantum-phase verification (before backend access)

[Source `hardware/qrr_n35_active_only_multi_seed.py`](../hardware/qrr_n35_active_only_multi_seed.py) imports the previously gate-proven phase-aware N35 comparator and constructs the two unmodified frozen versions: `neither` from `previous.verified.build(base)`, and `active_only` from `family.build_variant(base, "active_only")`. The *only* difference between their source quantum operations is the 2 cached-active CCX replaced by 2 RCCX (forward and actual inverse). A whole Qiskit-source emitted-gate unitary interpreter uses `Operator(inst.operation)` monomial matrices and accumulates actual complex amplitude. It does not assume relative-phase RCCX behaves like ordinary CCX; it requires output quantum amplitude **+1** for each basis case, correct full residue controlled multiplication and every helper zero. Before reading backend metadata, PER BASE:

- **8/8** local RCCX, semantic probe, exact inverse-latch phase cases, all helpers zero and complex phase +1;
- **42,672/42,672** exhaustive public unsigned comparator emitted-gate complex phase cases, thresholds width1..6, both conditions/control/initial flag;
- **1,584/1,584** mod35 modular additions from 16 independent public constants×(35 valid enabled +64 any disabled inputs), correct phase +1, aux reset;
- **128/128 `neither` full multiplier** and **128/128 `active_only` full multiplier** (all six-bit y values and both external controls), correct identity on invalid y and control0, 25/25 aux zero, final complex phase +1;
- Both source widths **32 logical qubits**; actual source gate differences **only RCCX +2 and CCX −2** with same CX and X counts. This proves ideal source unitary behavior for clean-input subspace and is seed-invariant; transpiler seed changes compile/layer/placement, not original source semantics.

These phase-sensitive checks all passed for both base jobs, which then *each* compiled all eight fixed seed pairs against one authenticated read-only IBM Fez target. The secret was used only to read backend target metadata; no actual quantum job methods were used.

## All eight matched seed results, without hiding regressions

Tables below display **native CZ and depth** per design, and paired deltas **active−neither**. Negative delta is better (less resource) and positive delta is worse. **Do not compare unmatched seeds**.

| Seed | Base2 neither CZ / depth | Base2 active-only CZ / depth | Paired ΔCZ | Paired Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,774 / 20,129 | 8,620 / 20,367 | −154 | +238 | NO |
| 37 | 8,856 / 20,523 | 8,457 / 19,862 | −399 | −661 | **YES** |
| 101 | 9,125 / 21,276 | 8,909 / 20,483 | −216 | −793 | **YES** |
| 409 | 8,953 / 20,627 | 9,056 / 20,682 | +103 | +55 | NO |
| 8,776 | 9,263 / 21,772 | 9,042 / 21,541 | −221 | −231 | **YES** |
| 12,011 | 9,034 / 20,977 | 9,132 / 20,525 | +98 | −452 | NO |
| 20,261 | 9,255 / 21,719 | 8,928 / 20,988 | −327 | −731 | **YES** |
| 45,673 | 9,288 / 21,476 | 8,989 / 20,846 | −299 | −630 | **YES** |

Base2 **5/8 both-resource wins**, **6/8 CZ-only wins**, **6/8 depth-only wins**, median *paired* **ΔCZ −218.5**, median **Δdepth −541**. Paired CZ range −399 to +103; paired depth −793 to +238. Base2 shows a favorable *central tendency*, but **FAILS** prereg ≥6/8 **joint** CZ+depth wins. No post-hoc "6/8 for each separate metric" substitution is allowed.

| Seed | Cubic base8 neither CZ / depth | Cubic base8 active-only CZ / depth | Paired ΔCZ | Paired Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,908 / 21,194 | 9,289 / 21,547 | +381 | +353 | NO |
| 37 | 9,290 / 21,648 | 9,445 / 22,380 | +155 | +732 | NO |
| 101 | 9,232 / 21,288 | 9,064 / 21,676 | −168 | +388 | NO |
| 409 | 9,281 / 21,510 | 9,339 / 21,850 | +58 | +340 | NO |
| 8,776 | 9,426 / 21,933 | 9,156 / 21,820 | −270 | −113 | **YES** |
| 12,011 | 9,279 / 22,085 | 9,297 / 21,815 | +18 | −270 | NO |
| 20,261 | 9,176 / 21,398 | 9,510 / 22,333 | +334 | +935 | NO |
| 45,673 | 9,178 / 21,952 | 9,352 / 21,901 | +174 | −51 | NO |

Cubic a8 **1/8 both-resource wins**, **2/8 CZ-only wins**, **3/8 depth-only wins**, median paired **ΔCZ +106.5**, median **Δdepth +346.5**. Paired CZ range −270 to +381; depth range −270 to +935. The active-only change's median **regresses in BOTH resources** on cubic8. The originally celebrated 8776 gain is correctly reproduced and is the **single joint win** in this eight-seed sample—not a general placement-robust gain.

Importantly, seed8776 EXACTLY reproduces the prior original cached native costs for BOTH variants and both bases (base2 original9263/21772 and active9042/21541; base8 original9426/21933 and active9156/21820). Thus no observed historical anchor drift in the fixed seed target compilation, though different real backend calibrations and later compiler versions could produce other results.

## CI truth, provenance, and independently preserved ORIGINAL results

Original [source run **39080813622**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080813622) generated **all 32 authentic target-CPU compiler outputs** and all exact emitted source phase proofs, correctly saved `status=COMPILE_SUCCESS` original JSONs, and uploaded original two artifacts. **The workflow finished with GitHub overall status FAILURE solely because the POSTCOMPILATION audit Python accidentally indexed `device_feasible_active_only` when the source original receipt correctly named it `device_feasible_active`.** Both source/science compile-and-proof steps had SUCCESS. This was a *schema-key error in the downstream audit*, NOT a phase proof failure, Qiskit compiler exception, experimental protocol deviation or unreported QPU job. We did NOT rerun or change the mathematical work, selected seeds or generated values to conceal the failure. The original run's failed CI conclusion must remain visible and documented.

A **separate** [independent exact original-artifact audit and permanent preservation CI **39080960758**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080960758) **SUCCESS**. It downloaded the two originally uploaded JSON artifacts from the source run **without recompiling**. Independently checked all 32 exact raw CZ/depth values against original job logs, actual 8+42672+1584+128+128 unitary proof receipts per base, two original baseline receipts and source gates, all eight frozen seeds with no exclusions, native CZ count-op consistency, exact original 8776 anchor, median/min/max and strict joint win counts, all QPU=0 indicators and failed physical gates. It committed the **unaltered raw original JSON bytes** to:

- [Original base2 matched eight-seed receipt](../results/ibm_shor35_active_only_multi_seed/qrr_n35_active_only_multiseed_base2.json).
- [Original cubic base8 matched eight-seed receipt](../results/ibm_shor35_active_only_multi_seed/qrr_n35_active_only_multiseed_base8.json).

The original negative result and original red CI remain preserved as independent provenance; the subsequent audit-key repair and verified full green rerun do **not** replace those receipts or alter the scientific verdict.

## Completed workflow repair and independent 32/32 rerun verification (2026-10-17)

The original experiment's **postcompilation audit** accessed `r[f'device_feasible_{tag}']` with `tag=active_only`, but the correctly saved source result calls the field `device_feasible_active`. This CI-only issue was repaired by [commit `d9cfe355`](https://github.com/CaMaLabs/RecycledQubitRegisters/commit/d9cfe355e9c54f0f55298edf7f93395af1097a28), mapping `active_only` to `device_feasible_active` and `neither` to `device_feasible_neither`. No gates, seeds, native backend, transpiler configuration, source-phase tests, acceptance gates or original data were changed.

[**Corrected full source workflow 39084396945**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084396945): **both base jobs SUCCESS**, including **all 32 matched native Fez CPU compilations and both postcompilation audits**, without any real QPU submission. [**Independent green-run original-artifact comparison 39084519756**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084519756): **SUCCESS**. It retrieved the new original JSONs without recompilation, checked **all 32 CZ/depth values, full compiled ISA operation count dictionaries and sizes, target widths**, and matched full emitted-gate complex-phase proof receipts, eight fixed seeds, exact seed8776 historical anchor, medians and robustness decisions against the *previously archived* red-audit experiment. Every original versus new numerical compiler result was **identical**. Differences in CPU walltime and timestamps are intentionally not compared.

Both unmodified **green rerun source JSONs** are archived separately under [`results/ibm_shor35_active_only_multi_seed_green_rerun_39084396945/`](../results/ibm_shor35_active_only_multi_seed_green_rerun_39084396945/), with [SHA-256 and every-seed reconciliation manifest](../results/ibm_shor35_active_only_multi_seed_green_rerun_39084396945/rerun_vs_prior_independent_audit.json). Original first-run results remain unchanged. The original 39080813622 CI historical failure remains visible; the corrected **39084396945 workflow and separate 39084519756 audit are both green**.

**Scientific verdict unchanged:** active-only improves both CZ/depth for base2 **5/8** seeds and cube8 **1/8** seeds, failing the predeclared ≥6/8 robustness gate at both bases. All compiled native circuits still fail CZ≤800/depth≤2000 hardware preflight. **Zero real QPU jobs, free Open runtime or paid runtime consumed.**

## Interpretation — what this result establishes and what it does not

**Frozen robust engineering gate: FAIL for BOTH bases.** Base2's favorable median is useful but 5/8 joint wins misses the strict prereg 6/8; cubic8's median and most seeds are explicitly worse. The two-base claim "active-only is generally robust" is NOT supported; retain the original comparator-only `neither` source as the **common reference**, while also preserving the earlier correct 8776 active-only improvement and all per-seed receipts as conditional engineering findings. Compiler seed changes can select different routing and synthesized gate layouts; **this is not hardware shot-to-shot variation, an independent random-device performance distribution or a proof against RCCX as an operator-level method**. With only eight selected seeds on one Fez target snapshot/one Qiskit SDK version, no universal gate-cost claim is warranted.

**Separate immutable hardware gate: FAIL for every one of the 32 compiled circuits.** CZ counts remain thousands (min observed 8,457) and depth tens of thousands (min observed 19,862 for active-only base2), over the fixed preflight 800 CZ / 2000 depth even for ONE controlled multiplier. **ZERO QPU jobs, free IBM Runtime or paid runtime used.** No complete four-phase QPE, no real N35 factors from a QPU, no cryptographic quantum advantage, and no measurable physical quantum-fidelity result.

**Next best experimental question:** stop treating single favorable seeds as evidence of robust architecture-level performance. Investigate targeted lower-complexity arithmetic/Toffoli networks with phase-exact full-residue semantics and a preregistered **paired multi-seed** benchmark from the outset; consider assessing best native layouts for an *entire* four-round algorithm only after a genuine controlled-modmul resource reduction approaching practical QPU requirements. Preserve all original N15 real Open Plan phase-recycling results separately, with attribution to CaMaLabs.
