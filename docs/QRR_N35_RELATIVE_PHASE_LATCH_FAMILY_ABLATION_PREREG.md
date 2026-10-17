# PRE-REGISTERED four-arm N35 active-only vs enable-only RCCX latch family ablation (ZERO QPU)

**Research lead: Chase Lunsford / CaMaLabs.** Date 2026-10-17. This fixed protocol is committed BEFORE new execution and original result receipts; all metrics and negative findings must be preserved unchanged. Absolutely ZERO IBM QPU submissions, free/premium quantum runtime, Sampler/Estimator or device shots.

## Why this ablation, and frozen verified controls

The [phase-exact comparator carry source result](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) remains **baseline** for any genuinely two-base improvement: ONE full-six-bit controlled public N35 multiplier, a2 native CZ **9263**, depth **21772**, cube a8 CZ **9426**, depth **21933**, 32 logical qubits (25 clean ancillas). Read-only current `ibm_fez` target, Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, optimization level1 transpiler seed8776. Prior [both active+enable RCCX combined](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_RESULT.md) was rigorously phase-correct and changed 26 actual source standard CCX into RCCX; a2 CZ **8542** depth **19819** improved, cube a8 CZ **9328** improved but depth **22005** WORSENED from21933. Thus joint engineering gate FAIL, despite favorable base2; no device feasibility and no N35 real-QPU work.

Preregister exactly four NEW public whole-multiplier arms, two bases b∈{2,8} × variants:

- **`active_only`:** replace ONLY the ONE long-lived clean `active=phase AND valid` CCX compute and inverse uncompute with `RCCXGate()` and `RCCXGate().inverse()` (2 RCCX total). All 12 `enable=active AND work[i]` temporary source latches use unchanged original exact CCX/CCX (24 CCX). Original phase-exact comparator carry RCCX remains present.
- **`enable_only`:** retain original exact `active` CCX/CCX pair (2 CCX), but replace ONLY the 12 temporary `enable` latch CCX compute/inverse pairs (24 CCX) by Qiskit's RCCX/actual inverse (24 RCCX). Keep original exact semantic controlled swaps.
- The independent **`neither`** baseline has 0 cached RCCX and verified a2 source RCCX596/CCX160, cube8 RCCX616/CCX162.
- The previously verified **`both`** combined result has a2 RCCX622/CCX134, cube8 RCCX642/CCX136 (CZ8542/9328, depth19819/22005). Do not change/rerun its original receipts or use the weaker cubic depth as a selective baseline.

**Expected source exact gate distribution, must assert in full circuit to prove intervention exercised:**
`active_only` a2 {CX1033,RCCX598,X28,CCX158}, cube8 {CX1077,RCCX618,X28,CCX160}.
`enable_only` a2 {CX1033,RCCX620,X28,CCX136}, cube8 {CX1077,RCCX640,X28,CCX138}.
No change to modulo35 arithmetic, prefix-carry adder, shortened ripple comparator temporary RCCX, public validity, work/acc swap, source phase/ancilla register layout, base choice, factors, known order, orbit or full basis permutation. All whole circuits 32 logical qubits, 25 initially/returned zero auxiliary qubits. Qiskit actual inverse operator, not gate-name assumptions.

## Hard exact phase correctness gate *before* backend read/native scoring

Reuse the independently written Qiskit `Operator` matrix-based direct emitted X/CX/CCX/RCCX gate monomial complex amplitude interpreter. All gates must be actual monomial unitaries; full final state outputs must have **exact complex amplitude +1** on each required clean-input basis state, not merely correct classical truth table. Tests for EVERY four original arms:

1. Local phase-aware `RCCX(c0,c1,latch)` then controlled exact CX semantic probe, then `RCCX.inverse()`, 4 input control patterns×probe0/1=**8 basis cases**, latch0→0, phase+1, check actual matrices inverse identity. The local proof is run even for `active_only`/ `enable_only` and ensures source RCCX gate soundness.
2. Unchanged all-threshold public exact comparator **42,672/42,672** emitted gate-basis phase cases across widths1..6, all public thresholds, geq/lt, control values, initial flag0/1; all scratch/carry clean and phase+1.
3. Unchanged 16 public modulo35 constants×99 enabled/disabled inputs=**1,584/1,584** emitted-gate cases, +1 complex phase, helper clean.
4. Full ONE controlled b multiplier for all y0..63×phase c0/1=**128/128** direct emitted-gate input cases; exact public `b*y mod35` for enabled valid work, identity on disabled and y>=35, unchanged phase control and **all 25 helpers returned zero** with complex +1. Assert exact variant-specific RCCX/CX/CCX/X distribution above. FAIL CLOSED on any phase mismatch, dirty ancilla, wrong output, or intervention not actually used.
5. Only after (1)-(4) pass may authenticated READ-ONLY `ibm_fez` backend target metadata be obtained; NO QPU device run.

Fixed four GitHub Actions jobs, opt level1 seed8776, Qiskit~=2.5.2/runtime~=0.47, 480sec CPU cap/job, no retry with tuning alternative, no GPU/device shots. Compare each new arm native CZ/depth to its OWN public base original verified `neither` baseline 9263/21772 or9426/21933; report separate differences vs previously archived `both` without postselection.

**Frozen engineering interpretation:** `active_only` or `enable_only` is a **two-arm winning family** only if **BOTH base2 and cube8** exact phase gates pass, compile, and have **strictly LOWER** native CZ AND depth than original neither baseline; if either fails, that family FAILS. If both pass, report both, but do not use timing from unmeasured seeds as robust NISQ fidelity. The entire four-job batch must finish and be archived; if any job invalidates semantics, consider the proposed family unsupported. **Immutable physical gate:** CZ≤800 AND depth≤2000 for BOTH public bases is mandatory before any future QPU proposal; no quantum runtime permitted in this experiment regardless of compilation. Not a four-round Shor or RSA cryptanalysis result.
