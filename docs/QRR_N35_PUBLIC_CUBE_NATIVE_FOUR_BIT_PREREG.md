# FROZEN: N=35 public cube vs unchanged base on IBM Fez native target, ZERO-QPU feasibility experiment

2026-10-16 Pacific. Lead: Chase Lunsford / CaMaLabs. Freeze this protocol **before evaluating any new native target compilation results**.

## Hypothesis, previous evidence and strict scope

Prior real IBM Fez Open-Plan N=15 controlled-modular-multiplication QPE succeeded (recycled 49/64 vs wide 38/64), but the N=15 base 2 has r=4 and cubing leaves its order unchanged, so that hardware result did **not** test Dark Star odd-power preconditioning. This study tests the first genuine cubic order reduction using the existing public-only **N=35,a=2,b=2^3 mod35=8**. The known classical identity gives multiplicative order **12→4** (validation labels AFTER the public base-selection policy), with equal Shor half-order witness: `2^6 mod35=8^2 mod35=29` and proper factors `gcd(29-1,35)=7`, `gcd(29+1,35)=5`. These factors are **classically trivial**. No claim of algorithmic discovery, theorem, real factoring advantage or hardware performance.

Use **full six-qubit 2^6 residue computational basis permutations**, `hardware/ibm_shor35_generic_permutation_direct_transposition.py`, wrapped by existing `hardware/ibm_shor35_public_odd_power_preflight.py`. The circuit construction uses only N, public base and QPE bit index, with **no true order, private factors or orbit encoding** in its choice of multipliers/permutation. The entire 64 computational basis input permutation is semantically validated, including N-invalid states to ensure unitarity. This path is NOT scalable asymptotically: it synthesizes a full residue permutation, not genuine arithmetic-efficient generic Shor multiplication.

## Frozen compiled comparison

IBM backend target: `ibm_fez` (actual target snapshot at runtime) with Qiskit pinned `qiskit~=2.5.2` and `qiskit-ibm-runtime~=0.47.0`. One public static seed a=2, one public cube b=8, two **separate independent** QPE architecture compilation jobs `recycled` and `wide`, and `phase_bits=4` in each. EXACT same transpiler settings across base arms: **profile `1_clean_kg24`, optimization level 2, seed 8776**. This is a fixed diagnostic, not a seed search. Existing public implementation `ibm_shor35_public_odd_power_preflight.py` invocation per architecture:

`python -u hardware/ibm_shor35_public_odd_power_preflight.py --backend ibm_fez --seed-base 2 --exponent 3 --phase-bits 4 --kind <recycled|wide> --profile 1_clean_kg24 --optimization-level 2 --seeds 8776 --outdir results/ibm_shor35_generic_permutation`

This existing program enumerates all complete semantic-round validations, creates only circuits and uses Qiskit **transpiler**. It explicitly **never creates a Sampler or submits a QPU job**; backend service/read-target connection does not imply QPU execution. GitHub secret `IBM_QUANTUM_API_KEY` is supplied as an encrypted environment value, never logged. No paid runtime, no QPU attempts, no credit usage. No automatic hardware follow-up is authorized.

The program's original full result receipt is copied (not selectively modified) to frozen paths:
`results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_recycled.json`,
`results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_wide.json`.
Each must contain exactly two rows `baseline` and `preconditioned`, no missing or failed compile rows. If a job fails/timeouts, retain original logs, mark feasibility indeterminate, and DO NOT silently change optimization or substitute compiled orbit source.

## Preregistered gates and reporting

Per architecture compare semantic `pass`, declared 4 phase bits, 12→4 validation order; full native two-qubit CZ count and depth, compiled native size, compile seconds and original logical qubit counts. Real hardware feasibility gate (not proof of actual factoring): **BOTH base arms** must have `CZ<=800` and `native compiled depth<=2000`, using same strict small-run cap established in real N15 hardware preflight; all four rows must compile successfully, supported dynamic measurement/reset must exist for recycled and circuit width fit backend. The bound is a **conservative heuristic**, not a calibrated fidelity certificate. If any fail or compile timeout, **do not submit a QPU job**. No hardware-level cube performance can be inferred from compiler counts alone; a 3× order reduction does not necessarily lower fixed-precision transpiled arithmetic gate counts.

The new results (including failures) must be preserved in `docs/RESEARCH_LOG.md` and independent [result document]. The more optimized **compiled-order/orbit-affine** circuit in `ibm_shor35_affine_matched.py` is NOT the same as full-register public order-independent arithmetic; any follow-on that swaps in the affine encoding must label it an oracle-designed compiled demonstration and must be separately frozen. As before, distinguish already-classically-factored N35 from real quantum utility.

**Scientific gate**: evaluate actual native feasibility and choose whether to ask the user for a separate tiny Open-Plan only physical run or do another compiler redesign; NOT to submit hardware automatically on a pass.
