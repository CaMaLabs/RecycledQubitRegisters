# VERIFIED — N=35 cached-enable control arithmetic: 33% fewer native CZ, 29–31% shorter depth, but hardware gate FAILS

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-16 Pacific / October 17 UTC. **Experiment:** one honest public-only controlled full 6-bit modulo-35 multiplication per base, **NOT four-round QPE, NOT an IBM QPU measurement**, and **ZERO QPU jobs/charges**.

## Prior milestones and frozen test

The project's real IBM Fez Shor N=15 Open Plan milestone successfully recovered 3×5 using recycled/wide phase registers, but it **does not test the Dark Star cube transform** (order of base2 mod15 is 4). The full-register permutation native N35, base2→cube8, m=4 experiment cut CZ/depth around 61%, but ALL arms exceeded the frozen IBM free-device heuristic <=800 CZ and <=2000 native depth. The first general-algorithm controlled-QFT-adder N35 arithmetic was even worse (0.86–1.73 million CZ). The next explicitly reversible X/CX/CCX [N35 single-multiplier baseline](QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_RESULT.md) had ideal noiseless gate-level verification **128/128 inputs, every helper zero** for both bases, but compiled to 27,929 CZ/depth 59,947 for base2 and 29,822 CZ/depth 63,922 for cube8. This one-multiplier experiment cannot directly be compared as a factoring success test.

The present improved kernel was explicitly preregistered in [`QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md`](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md), **commit `bffed30fb4c7db1a5b6c92437c06b94ebf9b81a7`**, before the new compilation. It freezes two public bases 2 and 8, IBM Fez **native target compiler only**, Qiskit~=2.5.2 + qiskit-ibm-runtime~=0.47, optimization level 1, transpiler seed8776, all X/CX/CCX gates, exhaustive 128-case actual gate interpretation, no order input, no orbit encoding, no secret prime/factors, no changes to the earlier source or original result receipts, and the unchanged 800 CZ/2000 depth feasibility boundary. A 480s compiler cap per arm was frozen.

## Exactly one optimizer intervention: compute and clean shared enable controls

Original code `hardware/qrr_n35_single_modmul_ripple_toffoli.py` included the three-element control vector `[phase, valid, source_bit]` **repeatedly** on each arithmetic add, and repeated `[phase, valid]` for six coherent work/acc swaps. The present [`hardware/qrr_n35_latched_controls_single_modmul.py`](../hardware/qrr_n35_latched_controls_single_modmul.py) **imports and reuses the old gate-proved `predicate`, `modadd`, `multi_x` and `controlled_swap` functions WITHOUT modifying their mathematics or decompositions**, but computes:

- A clean **`active = phase & valid`** once, with CCX, and uncomputes it at the end of the coherent multiplication.
- For each of six forward and six inverse accumulator additions, a clean **`enable = active & work[i]`** via CCX, then supplies a **single control qubit** `[enable]` to the unchanged modular constant adder, and immediately uncomputes enable. The controlled work/acc SWAP reuses `[active]`.
- The same public `valid = [y<35]` full-residue predicate ensures identity on invalid 6-bit y≥35, and every 25 auxiliary bits (6 accumulator, wrap flag, valid flag, 6 carry, 9 v-chain scratch, **active and enable**) return to zero. No private multiplicative order or orbit is used for circuit construction, and the control is unmodified.

The change makes the circuit *two application qubits wider* (30→32) and reduces repeated high-control gates. Unlike an optimized array of predetermined modular orbit states, this is still a public full-residue reversible arithmetic construction, although not optimized to fault-tolerant cryptographic scale.

## Provenance of raw source results and independent audit

[Original two-run GitHub Actions **39005624438**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005624438) **2/2 SUCCESS**, each CPU job independently read current `ibm_fez` native hardware target metadata, built public-base circuit, interpreted every actual emitted X/CX/CCX operation for every 64 residue inputs×2 controls and compiled with fixed seed. The `IBM_QUANTUM_API_KEY` repository secret was used only to authenticate a backend **read**, not a QPU Sampler/Estimator or any QPU submission. Both jobs reported **all 128/128 basis states correct with all 25 aux qubits cleaned**; IBM Fez native target compiler succeeded. **Do not confuse live target read / ISA compilation with executing on a real QPU.**

[Original-result independent audit/preservation CI **39005699941**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005699941) **SUCCESS**: downloaded original source-run artifacts, checked program/source version, public baselines using previous committed JSON instead of hardcoding just claims, 128 emitted-gate proofs, 25 clean ancillas, only x/cx/ccx source, exact CZ/depth and hardware gate, and committed original unchanged receipt JSON to:
- [public base 2 original](../results/ibm_shor35_ripple_cached_controls/qrr_n35_cached_enable_single_mul_base2.json).
- [public cubic base 8 original](../results/ibm_shor35_ripple_cached_controls/qrr_n35_cached_enable_single_mul_base8.json).

Original gate-level proof is on computational basis |control, y, aux=0>. Since the circuit is exactly X/CX/CCX, linear unitary extension makes it correct on coherent superpositions of those allowed inputs as well (ideal gate model); this does **not** predict actual NISQ fidelity, fault tolerance, conditional QPE phase readout, or factor recovery.

## Frozen original arithmetic and IBM Fez *compiler* results

| Metric — ONE controlled modular multiplier | Original base2 | Cached base2 | Original cube8 | Cached cube8 |
|---|---:|---:|---:|---:|
| Exhaustive ideal emitted-gate cases | 128/128 | **128/128** | 128/128 | **128/128** |
| All auxiliaries reset clean | 23 | **25** | 23 | **25** |
| Logical circuit qubits | 30 | **32** | 30 | **32** |
| Total source primitive X/CX/CCX gates | **1964** | **1536** | **2062** | **1578** |
| **Native CZ on IBM Fez target** | **27929** | **18719** | **29822** | **19912** |
| **Native compiled depth** | **59947** | **42335** | **63922** | **44381** |
| Frozen CZ<=800 and depth<=2000 | FAIL | **FAIL** | FAIL | **FAIL** |
| IBM QPU jobs | 0 | **0** | 0 | **0** |

**New engineering win:** With the same fixed target, compiler optimization and seed, cached enable controls reduce native CZ **base2 27929→18719 (−32.98%)** and **cube8 29822→19912 (−33.23%)**, and native depth **base2 59947→42335 (−29.38%)**, **cube8 63922→44381 (−30.57%)**. Primitive source gates also drop ~21.8% (base2) and ~23.5% (cube8). Two extra coherent helper qubits trade for substantial native two-qubit savings. The strict **engineering gate PASS**: two independent correct kernels, both CZ and depth strictly lower than their own frozen prior baseline.

**CRITICAL HARDWARE FAILURE (unchanged):** 18,719 CZ and depth 42,335 (smallest arm) are still about 23.40× and 21.17× the frozen heuristic cutoff 800 CZ /2000 depth. Base8 is slightly larger per **single multiplier**, just as before; cubing does not make each constant multiplier intrinsically cheaper. Do not use these results to claim a favorable total-factor-per-success ratio, a complete Shor circuit, new mathematically superior factoring method, hardware quantum advantage, or a feasible real device run. These were CPU native compilations using authenticated backend target metadata, **no QPU execution, no free or paid runtime**.

## Next engineering gate

The remaining cost is dominated by high-fan-in clean CCX v-chains and repeated public constant compare/wrap/correction. A stronger, distinct optimization should try **constant-specific prefix carry simplification**, or an in-place reversible ripple-carry *constant* adder with fewer high-control operations; freeze a separate comparison, use the same independent 128 basis-gate proof for each base, and report negative results. Since even the single optimized multiplier fails hardware feasibility, **DO NOT assemble or submit a real 4-bit public cube-vs-plain device workload yet**. Need eventually measure whole factoring protocol and account for classical factoring/checking cost. Preserve all favorable intermediate compiler results alongside the unchanged real QPU N15 win and N35 negatives.
