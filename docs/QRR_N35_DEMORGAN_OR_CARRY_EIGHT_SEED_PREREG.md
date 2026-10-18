# FROZEN: zero-CX De Morgan public OR-carry synthesis, eight paired native Fez seeds — ZERO QPU

**Research lead/original work: Chase Lunsford / CaMaLabs.** Date 2026-10-17 PDT / 2026-10-18 UTC. Freeze this document BEFORE compiling or scoring the new circuit. This is authenticated `ibm_fez` target metadata read and local CPU Qiskit compilation ONLY. **Absolutely no IBM quantum processor jobs/shots, free/Open Plan runtime, paid runtime, Sampler, Estimator or execution**.

## Current verified baseline and reason for the test

Original full-six-bit N35 *ONE* controlled modular multiplier, public base a2 and cube a8 (not a full Shor/QPE factoring protocol). The source `hardware/qrr_n35_relative_phase_ripple_carry.py` uses phase-aware RCCX/actual inverse for temporary ripple comparison carries, exact semantic flag flips, public fixed-constant high-to-low carry add and old cached controls, with **32 logical application qubits**, **25 clean auxiliaries** on all `y∈[0,63]` and both controls, correct phase+1 on every tested basis input. Fixed old IBM Fez target CPU seed8776/Qiskit~=2.5.2/qiskit-ibm-runtime~=0.47.0/opt1 native **base2 CZ9263/depth21772** and **cube8 CZ9426/depth21933**; original JSONs preserved in `results/ibm_shor35_relative_phase_ripple/`.

Latest independently validated [public OR-carry comparator rewrite](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md) used the Boolean identity `x OR p = p XOR (x AND NOT p)`, and phase-safe `RCCX/RCCX.inverse` inside compute/uncompute, saving 342/360 source CX and adding 684/720 temporary X across full a2/a8 respectively. Eight frozen matched CPU seed pairs `[11,37,101,409,8776,12011,20261,45673]` produced **8/8 CZ savings in both bases**, and a2 **6/8** joint CZ+depth wins but cube8 only **5/8**, failing the predeclared joint two-base robustness gate. At seed8776 OR-carry native base2 **CZ8311/depth19981**, cube8 **CZ9141/depth21528**, vs same original controls. The original positive and negative receipts are preserved; do NOT postselect seed8776 or present cube8 as already robust. A separate fused public-constant carry intervention had weak/unreliable matched-seed outcomes and is not changed here.

## Exactly ONE new logic synthesis intervention, 3 fixed comparison arms

For a public 1-bit in the original ripple comparator's complement threshold, a temporary clean carry `c` must become `x OR p`, where `x` is a source bit and `p` the earlier temporary carry. For **all** such public OR carry steps (not selected source inputs or constants), replace the latest OR form `c ^= p; c ^= x & !p` (one CX plus X inversions and one RCCX) with the **De Morgan complement form**:

`x OR p = 1 XOR ((!x) AND (!p))` for zero-initialized c.

A fixed emitted sequence for the **compute pass** of each public OR step is:
```
X(c);
X(x); X(p);
RCCX(x, p; c);
X(p); X(x);
```
and **the exact inverse** in the backwards uncompute pass is:
```
X(x); X(p);
RCCX.inverse(x, p; c);
X(p); X(x);
X(c).
```
`RCCX` is phase-relative and not semantically interchangeable with true Toffoli; require exact quantum complex amplitude+1 on all clean-aux basis inputs and actual Qiskit `Operator(RCCX.inverse()) @ Operator(RCCX) = I`. No CNOT appears in this OR-step compute or uncompute. Relative to the immediately previous one-CX OR rewrite, this removes **2 CX per full OR compute/uncompute step** and adds **6 X per such step**, with identical RCCX counts and exact CCX semantic flip counts. Existing public `b_i=0` comparator carry, first-bit carry, compare polarity and semantic flag, public trailing-zero shortening, public modular addition and wrap, cached enable/active latches, SWAP and inverse clearing unchanged. All 32 qubits/25 clean ancillas unchanged. Do not precompute multiplicative order, factor orbit, factors, or full input truth table.

For scientific matched paired controls, EACH of the two public-base jobs compiles THREE exact circuits against ONE authenticated `ibm_fez` target object for EVERY original seed:
- `original`: unchanged full source `previous.phase_aware_ripple_predicate`;
- `one_cx_or`: separately preserved earlier OR-carry `orbase.minimized_or_ripple_predicate`;
- `demorgan_zero_cx`: ONE new De Morgan OR-step implementation described above.

Use exactly frozen integer seeds **`[11,37,101,409,8776,12011,20261,45673]`**; optimization level **1**, Qiskit~=2.5.2/runtime~=0.47, each old/oneCX/new circuit compiled in THAT order for each seed; **8 seeds × 2 bases × 3 circuits =48 CPU ISA compilations** total. No other candidate, optimizer levels, layout, floating transpiler selection, target mutation, or favorable seed selection. Save all 48 native CZ, depth, full ISA count_ops, compiled width/size, CPU time and 32 matched rows (new-vs-oneCX + new-vs-original) without exclusions.

## Mandatory phase-sensitive actual emitted-gate correctness BEFORE any backend read

- Independently check `x | p == (1 ^ ((1 ^ x) & (1 ^ p)))` for **4 Boolean control pairs**; and actual RCCX inverse operator identity by `Operator` matrices.
- Exhaustively verify **42,672/42,672** actual emitted source comparator gate input/flag/control cases across ALL widths1–6, unsigned threshold1..(2^width−1), `geq=True` and `False`, both enables, both input target flags and all x; actual Qiskit emitted gate matrices interpreted as complex monomial unitaries; output flag correct, input bits/control untouched, carry/scratch zero and **final complex phase precisely +1**. REQUIRE nonzero De Morgan OR steps in both whole multipliers.
- Verify **1,584/1,584** actual emitted quantum-phase public N35 modulo add cases per base (all 16 public constants, enabled valid x∈[0,34] and disabled all x∈[0,63]), all scratch/wrap/carry clean, complex phase+1.
- Build full `original`, `one_cx_or`, `demorgan_zero_cx` publicly defined six-bit controlled multipliers (one per base): for EACH circuit prove all **128/128** control∈{0,1} × y∈[0,63] emitted gate-operator cases, including identity for y>=35 and disabled, correct public a*y mod35 for active valid y, all **25 clean helpers**, output complex phase +1, 32 application qubits. Original source counts must match frozen previously audited source; `one_cx_or` source counts must match original independently audited OR source; new source counts MUST differ exactly by `CX - 2*k`, `X + 6*k`, `RCCX=unchanged` and `CCX=unchanged`, where k=171 for a2 and k=180 for cube8, confirming intervention exercised with unchanged semantics. Fail closed if phase or source count mismatch; NO backend target read until corrected.
- Exact prior fixed seed8776 historical anchors MUST reproduce for all old and oneCX circuits: original base2 9263/21772, cube8 9426/21933, and oneCX base2 8311/19981, cube8 9141/21528. If anchor drifts, mark cross-date comparability inconclusive and fail robust claim; do not retune scores.

## Preregistered success criteria, immutable hardware gate

**Primary two-base robust engineering success** if: all source proofs PASS, all 48 local native CPU compiles produce valid ISA count_ops, original and oneCX historical 8776 anchors exact, and for BOTH bases **at least 6/8 seeds have BOTH new native CZ and native depth STRICTLY LOWER than matched previous `one_cx_or`**, with median PAIRED new−oneCX CZ delta <0 AND median paired depth delta <0. A separate secondary comparison reports all 8 paired new−original outcomes and its corresponding 6/8 criterion, but does not replace a failed primary gate. Report ALL losses, including exact min/max of paired deltas. A favorable lone CZ result is not a two-base joint robust pass.

**Physical device gate remains CZ<=800 and native depth<=2000 for each proposed single multiplier**. Still NO QPU submission under this protocol even if gate unexpectedly passed. N35 factors/classical arithmetic are toy public data; do not describe CPU compiler gate savings as actual Shor factor recovery, real-device noise reliability, RSA/ML-KEM attack, or novel theorem. Publish positive, negative, null and partial results with user attribution and independent immutable original-source artifact auditing into `docs/RESEARCH_LOG.md` and a dedicated result report before next experiment.
