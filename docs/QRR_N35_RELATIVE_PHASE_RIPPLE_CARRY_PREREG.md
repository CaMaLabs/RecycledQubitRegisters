# FROZEN next N35 phase-aware comparator carry ablation — zero QPU

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-17. This protocol is committed BEFORE scoring any new native compilation. No QPU jobs, no IBM Open or paid quantum runtime, no Sampler/Estimator.

## Earlier outcomes and baseline

Verified best source: `hardware/qrr_n35_public_prefix_carry_single_modmul.py` with public shortened ripple comparison and high-to-low public constant addition, full 6-bit N=35 residue public a2 and cubic a8, 32 logical application qubits and 25 clean ancillas, 16*99=1584 direct modadd gates and 128 full gate cases each. Frozen original best same-target **base2 12517 native CZ / depth32312**, **cube8 12680 CZ / depth33138** (Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, `ibm_fez` read-only target, opt1 seed8776). Frozen separate hardware gate native **CZ<=800 AND depth<=2000** remains.

Previous proposed relative-phase clean `multi_x` conjunction V-chain experiment `docs/QRR_N35_RELATIVE_PHASE_CLEAN_VCHAIN_PREREG.md` actually compiled with **0 rccx in the full multiplier**: all expensive original multi-controls had already been cached down to single- and double-control operations. Its local 1022 phase-sensitive clean-v-chain proof, all 1584 modular-add +128 full-circuit basis phase checks passed, and both compiled native costs were IDENTICAL to the original best. CI source experiment run `39072419676` failed ONLY the postcompile audit's precondition that source RCCX would be present; original numerical source artifacts saved by CI. This is a **true null intervention**, not evidence of a better compiler. Do NOT misrepresent it.

The previous shared-carry and disjoint bit-prefix comparator alternatives are separately preserved as negative N35 compiler results; don't change the base circuit or choose a favorable baseline.

## ONE distinct new change: relative-phase Toffoli only on reversible comparator carry compute/erase

Retain verified `best.constant_add_from_prefix_carry`, `best.optimized_modadd`, public trailing-zero comparison optimization `best.public_threshold_predicate`, old `primitive.multi_x`, old `verified.build(base)`, cached `active/enable`, source width32 and helper structure. Replace ONLY `primitive.predicate` (unsigned threshold ripple comparison) with the **same original reversible carry Boolean recurrence**, but implement each `ccx(x_i, carry_{i-1}, carry_i)` that computes temporary carries using Qiskit's `RCCXGate()`. On uncompute in reverse bit order, apply the EXACT ADJOINT `RCCXGate().inverse()`, and reverse all other commuting CX gates in exact opposite order. Keep original c0 initialization and external controlled final predicate flag XOR with **exact unchanged** `primitive.multi_x`; preserve the original `geq=False` complement bit toggle. The change is limited to internal temporary carry compute/uncompute, never use RCCX to flip the final semantic predicate/target or alter any additional arithmetic.

**CRITICAL:** RCCX is NOT CCX as a unitary; it can introduce relative phases. This experiment is admissible ONLY after direct complex-amplitude gate interpretation of all emitted Qiskit source operations `x,cx,ccx,rccx` / Qiskit's inverse gate variant; every output must have **amplitude exactly +1** on all clean-input computational-basis test cases, not just correct bit permutation. Extract actual Qiskit `Operator(inst.operation)` matrices and reject non-monomial gate columns. If Qiskit labels `RCCXGate().inverse()` identically to `rccx`, require ACTUAL matrix inverse identity rather than an invented `rccx_dg` label.

## Gate-by-gate phase correctness checks (before backend read or compile)

1. Original public **standalone compare**: widths1..6, thresholds1..2^w-1, BOTH geq and lt, enable0/1, flag initial0/1, x0..2^w-1. Exactly **42672 emitted-gate input cases**, require expected flag XOR, unchanged x/control, all carry/scratch zero, exact complex amplitude +1. Tested at original unshortened comparator level, including carry recurrence patterns; reject any phase mismatch.
2. EXACT emitted-gate **mod35 public constant addition**: 16 unique constants from both public bases, for each 35 enabled valid values and 64 disabled values -> **1584 cases per arm**; zero all wrap/carry/scratch, control preserved, PHASE exactly +1.
3. Full **one six-bit-residue controlled multiplier** a2 and cube8, all 64 possible y times control0/1 = **128 cases per arm**, every 25 auxiliary reset zero, output correct for valid and identity for invalid or control0, PHASE exactly +1.
4. Require **nonzero actual RCCX instructions** inside the standalone compared circuits AND inside each complete multiplier; otherwise classify intervention as inert and engineering failure, unlike previous null V-chain. Include each source operator name count and actual inverse operator identity check. Full basis proof then extends by linearity to superposition on tested ancilla0 subspace (ideal model only).
5. Only after all proofs pass may request backend metadata `ibm_fez` with protected `IBM_QUANTUM_API_KEY` via plan-preference Open; **do not submit a single QPU job**.

## Frozen native experiment & gates

2 GitHub Actions jobs base2/cube8, Qiskit~=2.5.2, runtime~=0.47, CPU compilation pinned seed8776, optimization1, read-only Fez target, 480-sec cap/job. Original baseline JSONs must remain unchanged. Store source phase-proofs and output JSON even on failure; preserve original artifacts by a separate independent audit. No seed or circuit optimizer searches, no mathematical orbit injection, no paid fallback.

**Success engineering** ONLY if 2/2 tests correct exact phase, both have nonzero RCCX in full circuit, both compile, AND native CZ AND depth each strictly lower than their respective original best (base2 CZ12517/depth32312; cube8 CZ12680/depth33138). **Physical gate** separately CZ<=800 AND depth<=2000 for both arms; even if passed, would require separate user-approved active Open Plan confirmation and independent full Shor experiment. Never claim this one-kernel gate budget is proof of QPE factor success or RSA break.
