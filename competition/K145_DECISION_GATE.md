# K145 decision gate — targeted post-HMR nonlinear reachability (NOT an experiment yet)

## Date, status, and evidence
2026-11-12. **Status: HYPOTHESIS ONLY; no scored candidate; NO EXPERIMENT RUN OR WIN CLAIM.** Evidence: user-uploaded `K001_K097_RESEARCH_EVIDENCE.zip` (297 source/result files), inventory and reconciliation; existing `competition/experiment_registry.json` and K101–K144 source/result history on this branch. Baseline **62 qubits**, full-domain score **95,369.00696815242**.

## Overlap audit (reasons not to repeat)
- K009/K014/K059/K060/K097: opcode-region maps, measurements, feedback already profiled. A new high-level profiler repeats work.
- K015/K026/K027: row scheduling, multimethod 4,000 candidate campaign, and incomplete 48-case parameter fusion. K027 registry lists 14 *required* methods, but only coupled precision/mode/schedule mutation implemented; listing != testing.
- K028/K080 and K034–K047: carry-save multiplication and register-workspace optimizations. Their wins or savings applied to earlier much wider circuits and do not produce a 62q drop-in.
- K049–K056, K066, K073–K081, K086: polynomial/Walsh/digit arithmetic and standalone phase-oracle prototypes. Many prefix/numeric-only. Do not relaunch under a new K-number.
- K062/K067/K092/K143: exact or local Clifford/free-gate changes, no lower official score.
- K063–K071, K091–K096, K099–K113, K135–K138: local reversible/ANF and nonlinear sharing. K096 examined 885 windows with no savings; K137 top 20 templates rank-tight and K138 all 32 analyzed composite windows tight under their assumptions.
- K098 and K144: local and paired angle perturbations; K144 two tiny prefix wins, full PASS score 95,448.3307649 or explicit full tolerance failure.
- K129/K130: bounded one-bit/classical-stack conditional duplication; **not** global reachable-state proof.
- K131: exhaustive valid-x deterministic *prefix* through first HMR; zero scored gate removed.
- K132: global ternary abstraction found free-gate identities; abstraction insufficient for nonlinear reachable-state proof.
- K139–K143: measurement-feedback provenance and quadratic Clifford phase correction networks; no scored-gate removal.

## The one carefully distinguishable candidate hypothesis

**Exact post-measurement reachable-state restriction on the controls of a *specific* CCX/CCZ/CSWAP** in the current 62-qubit Helios source. At a chosen gate, show (with control-flow and quantum measurement represented correctly) that the costly operation is redundant, or can be moved to a provably lower-frequency branch, on *all* allowed input and measurement histories.

This is not the already-tested unguarded ANF identity, symbolic local window, or prefix identity screen. K131's exhaustive proof stopped before the first HMR. K139–K143 tracked HMR producer/phase corrective Clifford actions but did not establish a scored gate identity. K129/K130 screened limited equivalent gate signatures, not a general quantum-branch reachability claim.

**No specific eligible gate or proof has yet been found.** The current archive does NOT prove this method can work, and this document does NOT propose another broad source scanner as a substitute. The source KMX and private Kickmix verifier are only on the Ubuntu VM.

## Score arithmetic (full-domain K058 base)
- Baseline Q=62; C=1538.20978980891; score ~95,369.00696815242.
- Removing **one Toffoli-equivalent executed on every shot**, with unchanged Q/T/error, changes score by **−62**.
- A single new permanent qubit at fixed baseline C adds approximately **+1538.21** score, and requires over **24.416** Toffoli-equivalent units removed *after accounting for 63-qubit scoring*, i.e. generally **at least 25** saved per shot to break even. This is why product caching that saves one CCX but expands 62→63 is uncompetitive.
- If a gate executes only on fraction p of valid verifier shots, maximum expected benefit of its elimination is **62p**, not 62. Actual expected occurrence must be established; static opcode count is insufficient.
- At fixed Q=62, removing one of the 41 non-Clifford arbitrary rotations at unchanged global epsilon is estimated to save ~**445.8569** score points (baseline average), but *no legal equivalent rotation elimination has been found*. This figure is a screening estimate; full verifier recalculates headroom.

## Required exact proof and falsification gate BEFORE assigning K145

1. **Identify exactly ONE costly gate** by original 1-indexed KMX line, opcode, controls, and surrounding HMR/control-flow context; provide a concrete replacement and what pre-existing opcode counts it changes. No repeated heatmap or omnibus motif scan.
2. Show the source-level transformation is exact on the **reachable quantum state/channel** at that location, including arbitrary superpositions, measurement outcome probability and phase, and reset/scratch invariants. A classical bit truth table alone is insufficient if state is coherent.
3. Establish a strictly positive lower bound on mean executed cost saved (`ΔE[CCX/CCZ/CSWAP]`), and `ΔQ=0`, `Δnon-Clifford rotations=0`, before spending time on a campaign.
4. Only then generate one pinned candidate, run local exact-unitary/channel tests, then official short prefix as a *rejection filter*, then official full 3,133,452-input verifier (2 seeds as reliability check). Never claim a win from the prefix.
5. If no such gate/replacement can be identified without another broad scan, **stop, label this hypothesis unsubstantiated, and do not fabricate a K145 result**.

## Current decision
**Do not run K145 yet.** The overlap audit excludes commonly proposed repeats but does not yield a concrete new scored transformation. Best next action is a *manual proof attempt on a single specific post-HMR nonlinear gate* once the VM source snippet and actual guard semantics are available, or select a different formally justified mechanism. This is a research hypothesis, not an experiment that has succeeded.

## Concrete two-region gate audit from user's pinned source (2026-11-13)

**Status: visible local subregions do not establish any scored rewrite.** Read-only source excerpts supplied from the pinned Helios KMX.

- HMR 21606, later scored lines: 21617 `CCX q18 q8 q14`; 21629 `CCX q7 q50 q18`; 21638 `CCX q21 q49 q20`; 21642 `CCX q25 q32 q26`; 21644 `CCX q26 q33 q27`.
- HMR 25612, later scored lines: 25623 `CCX q28 q0 q21`; 25637 `CCX q40 q45 q28`; 25638 `CCX q28 q46 q41`; 25639 `CCX q41 q30 q51`; 25653 `CCX q46 q30 q41`.

**Exact algebraic observation, not a simulation:** before lines 25637–25639, lines 25633–25636 XOR q21 into four *different targets* q45, q46, q30, q51. For arbitrary prior target bits `a,b,c,d` and `s=q21`, their resulting values are `(a⊕s,b⊕s,c⊕s,d⊕s)`. This is a bijection on the four targets for each s. It therefore **does not by itself impose a Boolean relation** between q45, q46, q30 and q51. The three CCX then form a triangular nonlinear dependency chain (each target feeds the next gate's control), not an immediately canceling duplicate.

**Likewise**, lines 21616–21620 wrap a scored CCX in CX operations but do not exhibit an adjacent CCX inverse or proven zero control. The nearby HMR and classically conditioned CZ corrections are not proof of control-value restrictions.

**Conclusion:** these 10 selected gates are *not candidates with a demonstrated scored delta*. Claiming savings from their shape would repeat K063–K071/K096/K138's ungrounded local-window reasoning. To proceed would require a **specific independently established upstream state invariant** (including measurement histories and phase), not another scan of adjoining gates. No K145 candidate generated, no official verifier run, no score reduction demonstrated.
