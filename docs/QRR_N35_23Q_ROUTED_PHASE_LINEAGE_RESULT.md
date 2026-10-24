# VERIFIED COMPILER ROUTING MILESTONE — one true recycled N35 phase logical qubit traced through explicit routed SWAPs into final Fez ISA in 12/12 cases; ZERO QPU

**Originating research lead:** Chase Lunsford / CaMaLabs. **Research date:** October 24, 2026 Pacific. **No quantum processor execution, IBM free/Open Plan or paid Runtime, hardware shots, Sampler or Estimator.** These are deterministic Qiskit **CPU compiler** routing/native ISA observations against authenticated **read-only** IBM Fez backend metadata, NOT real chip measurements or a firmware scheduling certificate. Public N35 is classically trivial, and public cube a³=8 yields gcd(8−1,35)=7 immediately.

## Historical source and carefully preserved scientific milestones

The [original genuinely recycled one-phase Qiskit source](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) contains a **single reused logical phase qubit** repeatedly measured/reset, six coherent work qubits, actual semiclassical inverse-QFT classical conditional gates, and public modular-power arithmetic for base a=2 and its cube8 at phase precisions b4/6/8. Its independent ideal result passed 768/768 actual arithmetic emitted-operator basis cases PER BASE and 336 independent adaptive-vs-wide phase probability comparisons PER BASE. It is a real dynamic quantum SOURCE, not a 4/6/8-wire simulated stand-in; however no N35 real QPU device run has ever been authorized.

The [native dynamic Fez CPU ISA result](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEZ_ISA_RESULT.md) accepted all six previously original 32-source-qubit dynamics, retaining `measure=b`, `reset=b−1` and `if_else=b(b−1)/2`, and separately the [actual classical branch quantum Operator proof](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md) checked **98/98 original compiled native `RZ(theta)` feedback bodies** against source `P(theta)` up to branch-global phase permitted only because prior control is **already measured classical**. It previously could NOT certify one fixed hardware phase wire, since reset/measure/feedback appear on different physical addresses. This was not an arithmetic error or evidence one source logical qubit got duplicated.

The [latest real source-width improvement](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md) removed nine **actually UNUSED** source `scratch` qubits without changing a single remaining emitted instruction, source phase/work bit or conditional phase branch, proving **32→23 total source quantum bits** while preserving the genuine one recycled phase qubit. Original independent 48 matched full native CPU ISA compiles and 784/784 conditional body equivalence checks passed; physical gate robustness was NOT obtained. Its original results remain untouched in `results/ibm_shor35_true_recycled_idle_scratch_pruning/`. Native circuits display 156 backend-width physical wires, NOT 23 measured hardware sites.

## Frozen new question — follow physical SWAP-token lineage without changing source physics

[Precommitted preregistration](QRR_N35_23Q_ROUTED_PHASE_LINEAGE_PREREG.md), initial git **`b9cab305393405e3f0d8bb9d41f37ea47100ffc3`**, froze TWO public bases2/8 × THREE phase precisions b4/b6/b8 × TWO compiler seeds 509/8776=**12 experiments**, `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, read-only `ibm_fez` target, optimization1. **Absolutely no arithmetic modifications, new register optimizations, oracle/order shortcuts, altered classical feedforward, QPU calls or favorable seed search**.

[New original source `hardware/qrr_n35_23q_routed_phase_lineage.py`](../hardware/qrr_n35_23q_routed_phase_lineage.py) reconstructs original publicly validated source with `qrr_n35_true_recycled_dynamic_fez_isa.original_structure_exact` and `qrr_n35_true_recycled_prune_idle_scratch.reduction_with_exact_instruction_identity`. Before backend read, it checks the previous six immutable source structures and proofs, recreating exactly the SAME phase1/work6/other16-aux **23-source-qubit** dynamic circuits and unchanged b classical bits.

For EACH unchanged source+seed, it performs TWO independent views of the CPU compiler, using the SAME backend target metadata and frozen seed:

1. **Intermediate routing snapshot** after Qiskit's actual `init`, `layout`, and `routing` stages, BEFORE `translation`/native optimization. Identify source `recycled_phase[0]` as a Qiskit virtual bit in actual `initial_layout.get_virtual_bits()`. Do not guess a physical address from a subsequent measurement. Track an initial logical phase-state token by explicitly walking **every routed SWAP** in circuit order; record each SWAP touching the moving phase token with actual from/to physical addresses, and every routed `measure`/`reset`/`if_else` event's physical address and previous-measured classical control. Require all dynamic phase events act at exactly the SWAP-updated phase token, original event name/count/order and each prior classical control; missing layout or unexpected event => INCONCLUSIVE with an explicit counterexample.
2. **Final full Fez native ISA compiler view**: measure/reset/if_else compiled physical event addresses, b classical destination bits, all native CZ and reported top-level depth, precise dynamic count and all earlier-measurement control indices. Independently verify all native classically conditional true-block **actual Qiskit 2×2 `Operator` matrices** match source `PhaseGate` up to a permitted classically conditioned scalar global phase. Compare EVERY ordered native phase-related event and physical qubit address against the routed intermediate event; if final translation moved an event, report inconclusive, not fabricated continuity.

**Result obtained in a CPU *compiler model*, not hardware:** This is positive evidence for a coherent ONE LOGICAL recycled phase-wire TOKEN correctly moved by actual routed SWAP gates and addressed by final native dynamic operations. It does **not** certify that all phases physically happen at a SINGLE fixed physical site, that the device can meet midcircuit measurement/reset/conditional latency requirements, that CZ count approximates hardware fidelity, or that any full N35 factoring works on a processor.

## Exact successful 12/12 route and final-native experiments

[Original successful two-base full staged-route + native-ISA source trial **40144331011**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40144331011) **2/2 GitHub Actions jobs SUCCESS**; Qiskit CPU metadata-only, no device runtime. Each public base passes 6/6 staged SWAP-token reconstructions, **6/6 final native physical event matches**, **98/98 native classically conditional 2×2 operator checks**, and 6/6 unchanged true source 23q clones. **12/12** routed→native and **196/196** native conditional bodies across both bases.

The table shows `stage phase SWAPs` = actual explicit *intermediate routing-stage* SWAP operations that involve the tracked phase token. `native CZ / depth` are actual **final native CPU compiler metrics**, not gate counts on a physical chip. `phase sites` lists exact physical addresses referenced by native phase-related measure/reset/conditional operations; multiple addresses are legitimate routed logical phase movement, not multiple source phase bits.

| Public base | Phase bits | Seed | Phase-state SWAPs (intermediate) | Native phase-related physical addresses | Native CZ | Qiskit top-level native depth |
|---|---:|---:|---:|---|---:|---:|
| a2 | 4 | 509 | **39** | 83,85,88,89,90 | 29,353 | 65,641 |
| a2 | 4 | 8776 | **28** | 144,146,147 | 29,223 | 68,106 |
| a2 | 6 | 509 | **49** | 118,128,129,130 | 44,038 | 101,597 |
| a2 | 6 | 8776 | **136** | 103,105,116,122,126 | 44,313 | 102,275 |
| a2 | 8 | 509 | **48** | 106,117,125,127 | 59,690 | 137,015 |
| a2 | 8 | 8776 | **74** | 102,104,116,121,122,123,124 | 59,730 | 138,953 |
| cube8 | 4 | 509 | **8** | 85,86 | 14,857 | 34,038 |
| cube8 | 4 | 8776 | **34** | 85,87,91,93 | 15,036 | 34,595 |
| cube8 | 6 | 509 | **8** | 85,86 | 14,857 | 34,038 |
| cube8 | 6 | 8776 | **34** | 85,87,91,93 | 15,036 | 34,597 |
| cube8 | 8 | 509 | **8** | 85,86 | 14,857 | 34,038 |
| cube8 | 8 | 8776 | **34** | 85,87,91,93 | 15,036 | 34,599 |

All six **seed8776** 23q compiled native resource anchors match EXACTLY their original immutable 23q source-pruning results. In cube8 b4/b6/b8 the arithmetic CZ is the same because public modular powers become trivial identity in later stages; the increased classical events can affect depth by 2/4, and native top-level `depth()` is NOT QPU reset/feedforward wall-clock schedule. No multiplicative order, factor table or prime decomposition was hardcoded into source quantum gates.

The actual routed intermediate circuits contain **3,422–13,973 total SWAP operations** across the tested public cases, but just **8–136 phase-token-moving SWAP events**; these are the precise counts used in the new proof, not a claim that physically scheduled hardware performs those explicit SWAP instructions unmodified. Native translation decomposes routing into the target's native gates, but **all checked ordered phase-related native physical addresses** were preserved across the routing→ISA boundary in this test. The compiler wire mapping is auditable even though a fixed physical phase site is not present.

### Frozen independent preservation, including reconstruction of original SWAP token positions

[Independent untouched original-artifact audit+preservation CI **40144473764**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40144473764) **SUCCESS**. It downloaded exactly two original source-run JSONs, **without compiling again**, verified original source width and nine idle scratch, old archived 23q native seed8776 anchors, 12 strict routed→native dynamic event sequences/physical addresses, 12 exact native CZ/depth tuples and per-stage source dynamic measurement/condition counts, and **RECONSTRUCTED every recorded phase-token SWAP progression** from the original physical SWAP event-index/from/to list interleaved with routed measure/reset/if_else events. Every one matched the original source token start, compiled measurement events and final token location. It independently verified the 196 original native branch-operator success receipts, all 12 final mappings and 12 hardware gate failures, then committed the original unmodified JSON bytes:

- [Full original six-row base2 routed-phase lineage, individual phase SWAP/event trace, native compilation](../results/ibm_shor35_true_recycled_phase_route_lineage/qrr_n35_23q_routed_phase_lineage_base2.json)
- [Full original six-row cube8 routed-phase lineage, individual phase SWAP/event trace, native compilation](../results/ibm_shor35_true_recycled_phase_route_lineage/qrr_n35_23q_routed_phase_lineage_base8.json)

All earlier independent N15 real Open Plan hardware pilot, N35 source quantum-phase proofs, static arithmetic ablations, dynamic original 32q source and actual 23q source-width proof, prior Fez target CPU ISA and conditional PhaseGate operator checks remain untouched.

## Three distinct outcome gates (do not conflate)

**1. Tracing the ONE LOGICAL phase state through the COMPILER'S SWAP mapping: PASS 12/12.** The prior uncertainty about whether multiple native phase-operation physical addresses could be explained by routing is resolved for these fixed compiler instances. All SWAP-token and final native dynamic addresses agree, and earlier measured classical bit conditions and all 196 conditional feedback body matrices independently match Qiskit source.

**2. Using ONE FIXED physical hardware qubit for every phase measure/reset/feedback: NOT OBSERVED (0/12).** Compiled phase events use 2 to 7 physical locations depending on seed and precision. This result must not be called "23 physical qubits used" or a demonstrated physical fixed-site reset/reuse. Source has one *logical* phase wire and 23 source qubits; native device register still shows 156 wires, and physical states may be routed through more sites over the circuit.

**3. Real device feasibility: FAIL 12/12** against frozen strict native **CZ≤800 AND top-level compiled depth≤2000**, including smallest cube8 native CZ14,857/depth34,038. No real QPU jobs, Open/free or paid runtime or physical quantum behavior measured, and no full N35 hardware factor recovery, new theorem, RSA-scale attack, cryptanalytic win or real-time control latency proof.

## Research implications / next strict gate

We can now separate a true compiler-routing explanation from a physical single-site promise. If the longer-term research requirement is physical single-site phase recycling, a **new frozen placement constraint** must explicitly require all dynamic phase-related operations on one physical address while preserving exact native classical feedback semantics, and then compare resource cost and success across **both bases and all b**. If not, the logical one-recycled-phase protocol is already represented correctly and tracing SWAPs may be sufficient at the source/ISA level, but actual hardware timing remains unresolved.

More important for N35 physical feasibility is still an **order-of-magnitude arithmetic gate-cost reduction** (or smaller physically credible new toy hardware task). Native CPU metrics alone do not show device fidelity and cannot justify QPU use under the original frozen 800CZ/2000-depth gate. Future QPU proposals need separate explicit user approval, confirmed active Open Plan, and a genuinely feasible full public circuit.
