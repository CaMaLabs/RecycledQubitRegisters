# VERIFIED MIXED — N35 genuine 32q one-phase-recycled Qiskit dynamic source compiles against IBM Fez CPU ISA at 4/6/8 bits, hardware feasibility still FAILS

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Date October 21, 2026 Pacific** (source GitHub Actions logs dated October 22 UTC). **ZERO real IBM quantum-device jobs, shots, free Open or paid quantum Runtime**, no Sampler/Estimator/quantum hardware call. This is read-only IBM Fez TARGET metadata and CPU Qiskit compilation, not on-device firmware/runtime certification or observed shot fidelity.

## Earlier actual and ideal milestones remain independently preserved

The previous [actual original Qiskit 32-quantum-qubit one-recycled-phase feedforward source](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) constructed **all 6** N=35 public-base `a=2,a³=8` × phase precision `b=4,6,8` dynamic Qiskit circuits. Each has exactly **one logical phase qubit reused**, **six unmeasured coherent work qubits**, **25 returned-clean arithmetic helpers**; hence **32 source quantum qubits** across all b, with **b classical output bits**. It genuinely emits mid-circuit phase measurement, subsequent reset of the same source logical qubit and classical `if_test` feedforward rotations, not a 4/6/8-wide register mislabeled as recycling. Six distinct public `pow(a,2^j,35)` modular-power stage sources passed **768 true emitted complex-Operator basis cases PER BASE**, all ancilla bits zero and final quantum complex amplitude +1. Independent conditional branch simulations matched **672/672** wide inverse-QFT ideal k-outcome probabilities across both bases and all b with ≈1e−17 max discrepancies. Previous original had NEVER been natively compiled; source ideal results are not QPU hardware results.

The [earlier 35-qubit FOUR-WIDE QFT/readout Fez ISA CPU experiment](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md) had verified 8/8 paired native compiler sign-selected improvements at both public bases but massive preflight **CZ≤800 AND depth≤2000** failure. The genuinely live IBM Fez Open Plan N15 phase-recycling toy demonstration is a separate archived real-QPU milestone, NOT N35 and NOT proof of cubic speedup. Public N35 cube base8 already has trivial classical factor7 from `gcd(8−1,35)`.

## Frozen new test, original intact source, exact backend instruction information

[Precommitted source protocol](QRR_N35_TRUE_RECYCLED_PHASE_DYNAMIC_FEZ_ISA_PREREG.md), original preregistration commit `b5d457abf9423a81040bfedf0e1102c342a2eb8f`, BEFORE score collection, authorized exactly SIX read-only `ibm_fez` native CPU compiler tests on the ORIGINAL source with `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, transpiler `optimization_level=1`, `seed_transpiler=8776`, no source branch rewriting/semantic fallback/seed search, NO hardware jobs.

[New source `hardware/qrr_n35_true_recycled_dynamic_fez_isa.py`](../hardware/qrr_n35_true_recycled_dynamic_fez_isa.py) BEFORE any backend read:
- Reconstructed exactly the original six distinct source dynamic circuits using original `configure_original_public_arithmetic`, `build_dynamic_source` and `inspect_dynamic_source`. Required every original stage public-power schedule, exact original source Qiskit instruction histogram and classical-bit output conventions to equal the unmodified **original audited receipts**, original **768** actual stage-phase proofs and **336 ideal outcome probabilities PER BASE**, all matching. This is a historical artifact/source-integrity check, NOT re-running 768 stage-unitary cases in the new test.
- Authenticated **READ ONLY** `ibm_fez` target metadata. Actual `backend.target.operation_names` included **`if_else`, `measure`, `reset`, `cz`, `rz`, `sx`, `x`**, etc., while `h` and `p` were **not native** target instructions. Both public base jobs observed Fez target width **156 physical-device qubits** (compiled ISA circuits may be padded to the backend device width; this is NOT the original source 32 logical-qubit width nor a validated number of simultaneously active physical qubits).
- CPU-transpiled all b4,b6,b8 actual original Qiskit control-flow circuits with one fixed seed. **ALL SIX compilation attempts ACCEPTED**, preserving exact original **b measurements, b−1 phase resets, b(b−1)/2 `if_else` conditional instructions** and b classical result bits.
- The original native output **replaced each controlled source `P(theta)` with native `RZ(theta)`** inside a classically conditioned `if_else` body. The FIRST experiment's deliberately conservative semantic test demanded a literal `P` and therefore correctly marked ALL SIX `COMPILED_UNCERTIFIED_DYNAMIC_SEMANTICS`. A distinct [later conditional quantum-Operator check](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md) resolves those specific branch phases UP TO a classical-history global phase, but independently flags physical phase-wire migration and no actual hardware execution. Do not retroactively rewrite this initial cautious result.

## Honest complete six-arm CPU ISA compiler results

These are **compiled native `cz` and Qiskit circuit `depth()`**, not device operations, wall-clock quantum circuit run times, scheduled reset/feedback latencies or device fidelity. `if_else` bodies may not be fully reflected in the top-level `depth()`, so do not interpret equality at cube8 b4,b6,b8 as truly equal quantum processor latency.

| Public base | Phase precision | Source qubits / classical bits | Native CZ | Compiled Qiskit depth | `if_else` retained | Measure / reset | CPU compile |
|---|---:|---:|---:|---:|---:|---:|---|
| a=2 | 4 | 32 / 4 | **29,813** | **69,008** | 6 | 4 / 3 | **ACCEPTED** |
| a=2 | 6 | 32 / 6 | **43,613** | **99,325** | 15 | 6 / 5 | **ACCEPTED** |
| a=2 | 8 | 32 / 8 | **59,446** | **138,604** | 28 | 8 / 7 | **ACCEPTED** |
| a³=8 | 4 | 32 / 4 | **14,499** | **34,259** | 6 | 4 / 3 | **ACCEPTED** |
| a³=8 | 6 | 32 / 6 | **14,499** | **34,259** | 15 | 6 / 5 | **ACCEPTED** |
| a³=8 | 8 | 32 / 8 | **14,499** | **34,259** | 28 | 8 / 7 | **ACCEPTED** |

The cube8 4/6/8 CZ and top-level depth happen to be identical because higher public power stages are trivial identity and the additional measurements/one-qubit classical feedforward require no extra two-qubit CZ gates under these compiler results. But **no real-time on-device latencies** were tested and Qiskit reported `depth()` is not a device control system timing schedule. No artificial period/orbit oracle was substituted.

**Immutable hardware feasibility FAILS ALL SIX**: the lowest **14,499 CZ / 34,259 depth** cube8 variant exceeds frozen 800CZ/2000depth by ≈**18.12× and 17.13×**, and base2 4/6/8 cost even more. The 32-source-qubit recycling width does NOT reduce the N35 arithmetic cost nearly enough for the originally specified real-QPU hardware gate. No free or paid quantum backend execution was attempted.

## Original run, independent original raw artifact preservation and conservative semantics

[Original exact-source two-base six-compilation CI **39729198098**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729198098) **2/2 jobs SUCCESS**. No credential leaked, no Sampler/Estimator/backend.run, no QPU jobs.

[Independent original JSON provenance and full cost/capability audit CI **39729456702**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729456702) **SUCCESS**; it downloaded the original two source-run artifacts **without recompiling or changing data**, required all original 768-per-base +336-per-base source receipts, all six exact native cost/depth values, dynamic condition/reset/measure counts, target declared capabilities, original b×classical bit pairing, compiler uncertainty for P→RZ, frozen CZ/depth failure and zero hardware jobs. Committed untouched raw receipts:

- [Original source base2 Fez dynamic ISA result](../results/ibm_shor35_true_recycled_dynamic_fez_isa/qrr_n35_dynamic_isa_base2.json).
- [Original source cube8 Fez dynamic ISA result](../results/ibm_shor35_true_recycled_dynamic_fez_isa/qrr_n35_dynamic_isa_base8.json).

## Interpretation and next falsifiable gate

**Genuine progress:** a source-level 32-qubit genuinely recycled phase circuit now *is* accepted by a hardware-target native Qiskit CPU compiler with control-flow, measurement, reset and classical feedback instructions retained. This is stronger than ideal-only mathematical compatibility, but **it is not yet a verified complete real-time hardware executable quantum program or physical-factor success**.

**Remaining engineering issue:** compiler transforms conditional `P` to `RZ`; independently check the actual 2×2 conditional-body matrices and classical bit/value/angle ordering, allowing only a branch-global phase because earlier controls are measured classical bits. Then assess actual physical phase wire routing / feedforward compatibility rather than assuming a 32-source logical-qubit circuit executes on exactly one fixed physical phase site. That distinct follow-on audit was performed and is separately archived. Nothing in these CPU results authorizes a quantum hardware shot or relaxes physical CZ/depth gates.
