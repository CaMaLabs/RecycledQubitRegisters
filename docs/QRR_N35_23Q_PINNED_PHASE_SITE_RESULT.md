# VERIFIED NEGATIVE — N35 23q genuine recycled phase pin initial Fez site85: 12/12 source-phase starts pinned and SWAP lineage certified, but 0/12 fixed physical site; ZERO QPU

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Experiment date:** October 24, 2026 Pacific; GitHub Actions timestamps October 25 UTC. **Scientific scope:** original TRUE one-LOGICAL-phase-qubit-recycled dynamic Qiskit N35 controlled-multiplier/semiclassical inverse-QFT circuits, **23 quantum source wires** after proven nine idle scratch removed, public bases2 and cube8 and b4/6/8 classical outputs. **NO actual IBM Fez quantum processor jobs, IBM Open/free or paid Runtime, hardware shots or midcircuit timing measured.** Compilation against AUTHENTIC read-only Fez target data on CPU only. N35 is classically trivial; public cube8 already permits trivial gcd(8−1,35)=7.

## Why this matters and immutable history

The previous real IBM Fez **N15** Open Plan phase-recycling demonstration is an independent small-QPU result; it was NOT a public cubic-order-saving N35 demonstration. Our separately preregistered [N35 true adaptive one-phase source](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) actually constructs source quantum measure/reset/if_else gates with one reused phase logical wire and six work wires; its prior ideal branch probabilities match the WIDE IQFT for b4/6/8, **672 across both bases**, and full stage source operators were proven correct. Later [READ-ONLY native dynamic ISA compilation and branch phase operator verification](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md) showed target compiler accepts the feedback gates and all **98/98** native classically conditional quantum PhaseGate↔RZ bodies are equivalent up to measured-classical-branch-global phase, but no QPU runtime.

The [23q source pruning study](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md) showed exactly **nine never-touched scratch source wires** could be removed, 32→23, without changing any original source quantum operation, quantum output or classic feedback. Native CZ/depth did NOT robustly improve, and source23 ≠ a certificate of just 23 physical sites occupied.

Immediately before this run, the [independently verified Qiskit actual routed phase-token lineage](QRR_N35_23Q_ROUTED_PHASE_LINEAGE_RESULT.md) traced the original one logical phase state through explicit compiler-inserted SWAPs for **12/12** public base×b×seed cases and into the final Fez ISA dynamic events, with **196/196 actual native branch operator proofs**. It resolved the phase-wire mapping question in these compiler instances, but native phase operations occupied 2–7 **physical device sites**, never a single fixed site, and all N35 native CZ/depth metrics failed our immutable physical feasibility gate **CZ≤800 AND depth≤2000**. All original numerical source receipts remain immutable.

## Predeclared new one-site start layout and honest pre-native interface repair

The NEW [preregistered protocol](QRR_N35_23Q_PINNED_PHASE_SITE_PREREG.md), initial commit **`ab00c3a9bc03596ec784bb6b833f41fe5612cc40`** before any new native compilation, fixes Fez **initial phase start physical site85**, two public bases `2,8`, three classical phase widths `4,6,8`, two seeds `509,8776`, optimization1, Qiskit~=2.5.2 and qiskit-ibm-runtime~=0.47.0. No public factors/orbits/orders injected, no base/seed/site search. Objective: distinguish merely pinning **initial placement** from maintaining the phase on a fixed PHYSICAL site throughout compiler routing, source feedback correctness, and resource costs.

**First original source CI [40145027852](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145027852) FAILED a Qiskit initial_layout harness interface**: passing a sparse `{original_phase_bit:85}` did NOT map the remaining 22 actual source wires and the Qiskit layout/routing stage raised `KeyError: work[0] does not exist in the Layout` for all12 cases. It correctly recorded unsupported rows BEFORE any native compilation/scoring or QPU, and we **did not** claim that as a compiler performance result.

A [documented amended preregistration](QRR_N35_23Q_PINNED_PHASE_SITE_PREREG.md) and source repair commit **`4560d77163236a76af67042935a212abe9173dfd`** were made BEFORE the successful native experiment: obtain the original unmodified Qiskit **init+layout stage**, extract complete original source23 virtual-qubit→physical assignments, and swap ONLY original `recycled_phase[0]` start with original source occupant of physical85 (if present), else move phase to85 leaving original phase site vacant; preserve all other source assignments. Supply the complete 23-Qubit source `initial_layout` in source-qubit order. This corrects a Qiskit API-interface problem, **not** phase source arithmetic, actual quantum gate schedule, frozen site85, seed list, physical gate threshold, native optimizer or final phase success criteria. Routed compiler may still add SWAPs, and we never claim initial-layout pinning constrains them.

[Experiment source `hardware/qrr_n35_23q_pinned_phase_site.py`](../hardware/qrr_n35_23q_pinned_phase_site.py) reuses unchanged [source reconstruction](../hardware/qrr_n35_true_recycled_prune_idle_scratch.py), [old staged routing token tracker](../hardware/qrr_n35_23q_routed_phase_lineage.py), and independently proven [native conditional quantum Operator matrix tests](../hardware/qrr_n35_native_dynamic_feedback_phase_audit.py). The original b4/6/8 source structure/remaining quantum and classical operations are checked BEFORE target access; no new branch-ideal outcome simulations are misrepresented as freshly run. Every frozen source retains `phase1,work6,remaining16 auxiliaries`, `measure=b`, `reset=b-1`, `if_else=b(b-1)/2`.

## Verified 12 pinned native-compiler cases — phase starts at 85 but moves

The fixed experiment [original two-job successful read-only CPU staged-route+native trial **40145166136**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145166136) **2/2 SUCCESS**, all **12/12 source phase initially site85** and **12/12 logical phase-token SWAP lineage check PASS** across routed intermediate state and final native ISA dynamic measure/reset/if_else addresses. All **196** real source-vs-native conditional quantum PhaseGate→RZ Operator comparisons pass (per public base, b4 has 6 and b6 has 15 and b8 has 28 per seed; 49×2 seeds×2 bases=196). Classical control bits used only prior measurements, original reset/measurement/event order preserved. Each Qiskit final native ISA compiled device-width view remains 156 wires, a compiler target width not the required source23 nor proof of 156 simultaneous physical quantum states.

**NUMBERS:** Each line is one unmodified SOURCE with the one pinned start layout. Old baseline is the **archived prior unpinned CPU compiler output**, *not a same-run newly compiled control*. ΔCZ/depth = pinned minus archived. A negative Δdepth only means fewer top-level Qiskit layers, not shorter measured device feedback latency. `Phase sites` are final ISA addresses for ALL measure/reset/if_else events; `Phase-moving SWAPs` are explicit source phase token movements in Qiskit's routed intermediate stage.

| Public base | Classical bits b | Seed | Old unpinned CZ/depth | New pinned CZ/depth | ΔCZ / Δdepth | Phase token SWAPs | Native dynamic phase sites |
|---|---:|---:|---:|---:|---:|---:|---|
| a2 | 4 | 509 | 29,353 / 65,641 | **29,375 / 67,210** | +22 / +1,569 | 30 | 67,69,78 |
| a2 | 4 | 8776 | 29,223 / 68,106 | **29,477 / 67,531** | +254 / −575 | 17 | 10,29,38,49 |
| a2 | 6 | 509 | 44,038 / 101,597 | **44,229 / 102,970** | +191 / +1,373 | 19 | 98,106,109,110,111 |
| a2 | 6 | 8776 | 44,313 / 102,275 | **45,075 / 103,270** | +762 / +995 | 77 | 69,78,86,88 |
| a2 | 8 | 509 | 59,690 / 137,015 | **61,539 / 141,149** | +1,849 / +4,134 | 89 | 47,58,65,67,70,71,86,89 |
| a2 | 8 | 8776 | 59,730 / 138,953 | **60,645 / 138,584** | +915 / −369 | 77 | 65,66,84,89 |
| cube8 | 4 | 509 | 14,857 / 34,038 | **14,907 / 34,385** | +50 / +347 | 8 | 85,97,107 |
| cube8 | 4 | 8776 | 15,036 / 34,595 | **15,816 / 35,767** | +780 / +1,172 | 33 | 20,22,85 |
| cube8 | 6 | 509 | 14,857 / 34,038 | **14,907 / 34,385** | +50 / +347 | 8 | 85,97,107 |
| cube8 | 6 | 8776 | 15,036 / 34,597 | **15,816 / 35,767** | +780 / +1,170 | 33 | 20,22,85 |
| cube8 | 8 | 509 | 14,857 / 34,038 | **14,907 / 34,386** | +50 / +348 | 8 | 85,97,107 |
| cube8 | 8 | 8776 | 15,036 / 34,599 | **15,816 / 35,767** | +780 / +1,168 | 33 | 20,22,85 |

**Primary fixed-site outcome: NEGATIVE.** Every source phase was successfully pinned at **start85** yet Qiskit routed it through **8–89 SWAPs affecting the phase token** and all 12 final dynamic event sequences used **3–8 unique physical sites, not one**. The predeclared strict physical-site condition needs the entire phase token never to move, `phase_token_swap_ops==0`, and ALL feedback, reset and measure at site85, while preserving original quantum feedback operators. **0/12 strict no-phase-swap fixed site PASS** and **0/12 dynamic-event-only at85**. The one logical phase state remains coherently traced through SWAP routing, which is a positive compiler-interpretation finding; none of this is an actual hardware experiment.

**Resource observation:** pinned CZ is numerically higher than the ARCHIVED unpinned CZ in **12/12**, and no pinned case is lower in both CZ and depth. However **causal caveat:** for many frozen rows, the newly requested normal Qiskit init+layout baseline initial phase address differs from the prior archived full-routing experiment's phase start (even for the same numerical seed); e.g. base2 b4/seed509 newly derived start77 vs archived initial90, cube8 b4/seed8776 newly derived start1 vs archived initial85. Consequently the two compilations were NOT compared as newly executed true same-snapshot native baseline/pinned pairs; differences may reflect backend target metadata or staged layout-pass decisions, not solely site85 pinning. **Do not conclude that pinning itself caused +CZ or +depth** from the archived comparisons. To measure its causal cost, a future trial must preregister same-run unpinned and pinned CPU compiles under one cached backend TARGET snapshot and maintain both source-integrity checks. That caveat does NOT weaken the strict pin-start and actual moving-phase/final-native-site falsification.

## Independent preservation and source-SWAP reconstruction

[**Independent original-artifact download, SWAP and operator receipt audit/preservation CI 40145320774**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145320774) **SUCCESS**. It downloaded the EXACT two original JSONs from source CI **40145166136** without any new compilation, checked:

- all **12 original native CZ/depth measurements and full original public base/precision/seed provenance**, exact source width23, unchanged source gate operations and prior-bit feedforward, physical pin85 respected, complete 23Q source-layout mapping with at most two changed original source assignments;
- **reconstructed source phase SWAP TOKEN positions independently** from saved original `instruction,from_physical,to_physical` event records interleaved with EVERY routed `measure/reset/if_else`, verified token matches actual routed phase addresses and all final native addresses in order;
- original native measurement/reset/feedback branch operation counts for every b, previously measured conditional bits and total **196 genuine original branch quantum-Operator success receipts**, and all 12 strict fixed-site failures;
- frozen physical feasibility gate **CZ≤800 AND depth≤2000 FAIL 12/12**, no IBM real device job/free or paid Quantum Runtime use.

The audit committed the byte-original CPU source-run receipts unchanged:

- [Original six pinned site85 rows, base2](../results/ibm_shor35_23q_initial_phase_site85/qrr_n35_site85_pinned_base2.json)
- [Original six pinned site85 rows, cube8](../results/ibm_shor35_23q_initial_phase_site85/qrr_n35_site85_pinned_base8.json)

All prior independent original TRUE recycled source, 32→23 actual idle-scratch reduction, prior source-conditional quantum math, routed one-logical-phase tracking, initial RCCX and arithmetic successes, and real IBM Open Plan N15 phase-recycling result remain separately preserved, with both successes and negatives attributed.

## Three outcome gates and next research step

1. **One genuine recycled logical phase source wire + compiler SWAP token through native phase operators: PASS 12/12.** True source width23, dynamic classical feedforward operator verification196/196, no extra source phase qubits.
2. **Physical site85 initial pin honored: PASS 12/12**, but **always-stationary phase qubit or same fixed dynamic site: FAIL 12/12**. To enforce fixed placement through routing, a real **phase-preserving constrained routing pass** must explicitly prohibit phase-token SWAP moves or keep phase dynamic operations pinned, not just specify initial layout.
3. **Actual N35 hardware feasibility: FAIL 12/12**, even smallest native CZ14,907/depth34,385 at cube8, far above unchanged 800CZ/depth2000 proxy, BEFORE physical coherence or dynamic-control timing. Thus **NO IBM QPU submission** and no verified physical factor finding.

**Next strict experiment, if pursuing physical placement:** first isolate whether Qiskit can route the REAL exact 23q source using a constraint of **NO phase-moving SWAPs** while satisfying device coupling, measure/reset/conditional operator equivalence and native ISA. If no constrained route exists on the target/with the frozen layout, report a topology-routing *inconclusive or fail*, not a hardware claim or reason to relax prior physical resource limits. Separately a same-target-snapshot paired unpinned/pinned native CPU compiler experiment is required to measure causal layout overhead. Neither implies a practical factorizing quantum computer.
