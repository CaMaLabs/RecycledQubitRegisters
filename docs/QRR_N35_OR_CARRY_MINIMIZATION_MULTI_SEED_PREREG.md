# FROZEN experiment — phase-exact public comparator OR-carry lowering, 8 paired Fez CPU-native seeds, zero QPU

**Research lead/original program: Chase Lunsford / CaMaLabs.** Preregistered 2026-10-17, **BEFORE** any new implementation compilation/scoring. This is strictly `ibm_fez` target metadata retrieval and **CPU-only** native Qiskit compilation, ZERO real IBM quantum hardware jobs, ZERO IBM Runtime Open/paid quantum minutes, no Sampler/Estimator and NO submitted circuit jobs.

## Scientific controls and historical results

The currently most credible common, independently audited full-residue N35 controlled **single modular multiplication** source is [`hardware/qrr_n35_relative_phase_ripple_carry.py`](../hardware/qrr_n35_relative_phase_ripple_carry.py): a2 native **CZ9263/depth21772**, public cubic8 **CZ9426/depth21933**, on read-only IBM Fez native target with `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, optimization level1, seed8776. Both have 32 logical application qubits and 25 ancillas clean; old original JSONs under `results/ibm_shor35_relative_phase_ripple/` remain unchanged. The old comparator uses coherent `RCCX` and its actual inverse for **temporary carries only**, exact X/CX/CCX semantic target flips, and was proved on all 42672 comparator, 1584 public modadd and 128 full-control/basis cases with correct **complex phase +1**. It operates on ALL 64 six-bit work input states, returning invalid y≥35 untouched, and has no hardcoded true multiplicative order, factors, or precomputed 12-element orbit.

Later [eight-seed active-only latch comparison](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) demonstrated that one favorable seed8776 does **NOT** prove multi-seed robustness: base2 active-only 5/8 joint native CZ/depth wins, cube8 1/8, both below prereg ≥6/8; cubic median regressed. **Do not substitute a convenient active-only or both-latch source as the new baseline**. This experiment compares ONLY original phase-aware-comparator `neither` with the new comparator OR-carry representation. Preserve all earlier successes and failures.

## ONE fixed new comparator-only Boolean source transformation

The old phase-aware comparator computes temporary ripple carry c[i] on public complement threshold `const=(2^n-threshold)`: for each i>0 with public const bit `b_i=1`, `c[i]=x[i] OR c[i-1]` and emits the source sequence
```python
qc.cx(x[i], c[i])
qc.cx(c[i-1], c[i])
qc.append(RCCXGate(), [x[i], c[i-1], c[i]])
```
(the exact RCCX adjoint followed by reverse CX operations in uncomputation). New candidate uses the identical OR identity **`x OR p = p XOR (x AND (NOT p))`** to lower this step to
```python
qc.cx(c[i-1], c[i])
qc.x(c[i-1])
qc.append(RCCXGate(), [x[i], c[i-1], c[i]])
qc.x(c[i-1])
```
and uncomputes in **literal inverse order**: X previous carry, exact `RCCXGate().inverse()`, X previous carry, CX previous carry→current. This replaces **ONE CX** per OR compute and ONE per OR uncompute with two temporary X operations each time, while preserving the same Boolean output and clean carry. As RCCX has relative quantum phases, this is ONLY a valid substitution if direct emitted-gate complex-amplitude source interpretation returns final amplitude **+1+0j** for every tested basis state; do not treat Boolean identity alone as quantum-unitary equivalence. Qiskit's inverse RCCX can be NAMED `rccx`; validate actual `Operator(rccx.inverse())@Operator(rccx)=I` and track the real instruction operators.

Everything else unchanged: `b_i=0` carries, lowest-bit carry, `geq`/lt flag polarity, old `primitive.multi_x`, public threshold trailing-zero stripping, high-to-low prefix constant addition, full two-pass public 6-bit modular multiplier, cached `active` and `enable` latches with **old exact CCX**, semantic swaps, original register layout **32 qubits/25 aux**, original public N=35 a2/cube8. No extra variants, no data-dependent parameter choice, no textbook/RSA factoring claim. The original exact RCCX comparator and original kernel source are kept intact; use a separate new file.

## Frozen test order, paired compiler conditions, metrics

For BOTH public base2 and cube8, all quantum source phase checks MUST pass BEFORE touching IBM backend target metadata:
1. Standalone actual-emitted-gate comparator **42,672/42,672** basis cases PER base; every width1..6, every public threshold t1..(2^width-1), both `geq=True/False`, both external enables 0/1, initial flag0/1 and all x input values. For each test, require **correct predicate XOR**, unchanged inputs/control, every carry/scratch bit reset zero and final complex amplitude exactly **+1**. Confirm comparator source genuinely has new OR branch and actual inverse operator. Independently check OR classical identity on its 4 input combinations as static preprocessing, but do not replace gate proof with that Boolean-only test.
2. **16 distinct publicly generated N35 adder constants** ×(35 enabled valid target inputs+64 arbitrary disabled target inputs)=**1,584 exact-phase direct emitted-gate modadd cases PER base**, all scratch/carry/wrap clean.
3. **128/128** complete emitted full-residue controlled multiplier cases PER base for BOTH the immutable original `neither` and new OR-minimized candidate: all 64 work y × c=0,1, expected `a*y mod35` when enabled/valid and unchanged otherwise, all **25** auxiliary bits returned0, control unchanged, final complex phase **+1**. Both 32 source logical qubits; the source gates must differ with **lower CX and higher X**, but same RCCX and exact CCX (nonzero b=1 branches exercised), no unrecognized gates.
4. ONLY once 1–3 pass: authenticated IBM `ibm_fez` TARGET read, no run/submit/quantum primitives. Two independent CI jobs base2 and cube8. Each job compiles both original and candidate under **exactly eight fixed matched transpiler seeds `[11,37,101,409,8776,12011,20261,45673]`**, fixed native `generate_preset_pass_manager(backend=backend, optimization_level=1, seed_transpiler=seed)` and same read target metadata within job. Compile old first, new second. 8×2×2=**32 original CPU-only native compilations**, max 560s CPU job run, max 13min GitHub job. No seed/layout search, no post-result choosing only good placements, no alternate optimizer.
5. For each pair record exact **native CZ and depth, count_ops, full ISA width, elapsed, absolute hardware gate, individual matched CZ/depth deltas**, and report eight rows including worst regressions. Compare medians of PAIRED deltas and count joint strict CZ/depth wins. The seed **8776 old baseline anchor must EXACTLY reproduce** base2 original CZ9263/depth21772 and cube8 original CZ9426/depth21933; if anchor drifts, report a target/compiler comparability caveat and **do not claim robust**.
6. Independently verify and permanently preserve **original unaltered source-run JSON artifact receipts**. The original positive historical records and failed previous multi-seed must remain intact.

## Frozen pass/fail, no QPU

**Robust engineering PASS requires for BOTH bases**: every exact source quantum-phase and cleanup test passes; every seed pair completes; original target seed8776 historic match; **≥6/8 seed pairs strictly improve BOTH native CZ and native depth**; AND median PAIRED native CZ delta <0 AND median PAIRED depth delta <0. Report whether the *candidate-only* modular-constant OR simplification is harmful on some seeds. No post-result lowering the 6/8 rule or citing an isolated best seed as robustness.

**Immutable QPU feasibility separate:** native CZ≤**800** AND depth≤**2000** for a proposed candidate, unchanged from prior N35 heuristic. Even if passed, this protocol would still forbid real QPU submission without separate explicit authorization and active confirmed Open Plan. An N35 one-controlled-multiplier CPU compilation is NOT a four-bit phase-register QPE/factoring run, practical quantum speedup, RSA-scale cryptanalysis, or hardware-fidelity measurement. Zero QPU Runtime of either type.
