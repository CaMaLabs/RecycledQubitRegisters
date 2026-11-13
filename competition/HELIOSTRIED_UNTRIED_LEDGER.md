# Helios scored-optimization research ledger — reconciled through K143

**Objective:** an officially verified score below **95,369.00696815242** on the pinned Helios inverse-square-root circuit.

**Baseline:** `competition/k098/results/helios_immutable.kmx` (local VM, not tracked), SHA-256 `e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183`. 62 qubits, 22-bit input, max x = 3,133,452. Source 53,841 lines.

**Authoritative scoring rule:** `score = Q * (mean executed CCX/CCZ/CSWAP + mean T-equivalent / 4)`; T-equivalent includes synthesized non-Clifford Z_POW rotations and any explicit T gates. The epsilon budget is determined by the global worst-case phase-error margin. **Z, CZ, CX, HMR and Clifford gates have zero direct score cost, but altered measurement RNG or gate scheduling can affect measured execution/error.** See private verifier help at `competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py --help`; this file is only on the VM. Do not substitute source instruction counts for executed mean counts.

## Evidence grades

- **Officially verified:** full required input domain and shot requirements using private verifier; source SHA and output retained.
- **Partial verifier:** restricted x, shots, or seeds; cannot establish leaderboard success.
- **Exact local proof:** algebraic equivalence on a bounded region, not a full-circuit verification.
- **Read-only screen:** candidate selection or structural analysis, no circuit generated.
- **Numerical prototype:** arithmetic approximation without a complete reversible circuit.
- **Hypothesis only:** not yet tested against Helios. Never label as tried because another project used a related technique.

## Tried / investigated: do not casually repeat

| Experiments | Technique | Observation and evidence grade | Revisit only if |
|---|---|---|---|
| K012/K018/K040/K044/K047 and later width studies | Qubit lifetime, register recycling, branch-aware reuse, static/measurement-aware liveness | Mixed historical width progress (including a 255→238 phase); **current 62-qubit target has no demonstrated score win** | A specific new legal reuse schedule eliminates at least one *simultaneously required* qubit; not another generic interference graph |
| K098 | Phase merging / dropping / fixed perturbation | Zero exact merges; several phase-drop candidates failed; some full-domain archived candidates worse, but **their baseline SHA differs from current pinned circuit** | New collective phase-error compensation verified under pinned target |
| K099–K113 | Small-window gate factoring, CX parity, commutation, CSWAP rewrites, reversible truth-table and affine synthesis | No verified lower official score | Materially different global transformation with positive predicted scored delta |
| K114–K123 | Reachability, arithmetic representation, bucketing, Chebyshev/Horner, piecewise cubic, lookup bitplanes, generic multiply-accumulate | Numeric approximations sometimes pass tolerance; complete reversible arithmetic generally too costly or not constructed | Explicit full Q and executed-CCX/T budget beats pinned score |
| K124 | Direct phase monomials | Rotation count too large; sampled numeric tolerance only | A fundamentally different sparse phase realization |
| K125–K128 | q28 phase-ladder analysis, exact DAG Z_POW predicate matching, complements, reduced BDD | No proven matched sites or rotation reduction; BDD exceeded budget | New bounded symbolic method with evidence of a *scored* removal |
| K129–K130 | Measurement-condition XOR fusion of identical Toffoli-class gates | No eligible pairs within restricted source/condition scope | Different nonlocal or multi-condition scheduling with explicit expected-count savings |
| K131 | Exhaustive valid-input deterministic-prefix gate identity | One zero-cost reset identity; zero scored removals through first HMR | Later phase/measurement region under proven reachable-state constraints |
| K132 | Full-circuit ternary abstract-state identity screen | Suggested zero-cost CX/CZ/SWAP identities; no scored CCX/Z_POW candidate | Exact reachability information stronger than ternary abstraction |
| K133 | Source-cost heatmap | Static source hotspots, **not** executed-gate attribution | Obtain actual dynamic count profiling |
| K134 | PTP-inspired periodic phase screen | Tested simple residue-dependent phase patterns; no legal scored transformation | Explicit quotient-dependent correction with predicted rotation/CCX saving |
| K135 | Repeated reversible CCX motif family screen | 269 families, many overlaps; source patterns do not imply saving | A transformation spanning genuinely distinct blocks |
| K136 | ANF algebraic-degree bound on top 20 motifs | Some apparent gaps under weak degree bound | Stronger lower bounds or different gate model |
| K137 | Nonlinear-output-rank lower bound | All top 20 isolated templates saturated CCX lower bound | Measurement-assisted/global/non-independent-state semantics |
| K138 | Combined reversible CCX windows | 32 analyzed windows all tight; 197 windows constrained by caps/span/width, not proven optimal | New reachability/feedback/global hypothesis, not just larger caps |
| K139–K141 | HMR feedback gadget scan, producer provenance and exact Boolean ANF tracking | 874 HMR; 529 immediate CZ; 76 matched/preserved, two complex correction networks; 451 unresolved by producer boundaries | Complete phase-aware channel rewrite with a scored gate reduction |
| K142 | Conditional Clifford phase polynomial audit | 574 feedback blocks; 53 multi-term; no Z/CZ cancellation; 21,606 and 25,612 isomorphic | Factor only if **Q, CCX, or T** can decrease |
| K143 | CX-basis phase-congruence rewrite | 12 local polynomial proofs, 187 fewer CZ and 184 added CX; candidate SHA `6e332f43226ffb15126ba8e62cdf6ea7170d4e51951f78e9046b2e5ccf206b1e`; **zero direct scored delta**, no official verifier run | A new use of basis rewrite that removes scored gates or width |
| QRR / Dark Star / PTP / LWE transfer | Qubit recycling, modular arithmetic, cryptanalytic residue/Fourier/recursive ideas | Broadly investigated in separate domains; **not evidence of a Helios score win** | Precise mapping to Helios's function and resources; no claims of factoring-based advantage |

**K143 distinction:** The candidate file was generated on the user's VM, not submitted or officially verified. The arithmetic of free Clifford-gate replacement does not imply a scored improvement. The verifier seed derives from the circuit binary unless explicitly overridden; local equality alone is insufficient for an official pass.

## Prioritized **not-yet-demonstrated** Helios research avenues

These are hypotheses, not claims that an implementation is new to quantum computing. A source/results search is required before marking an avenue completely untried.

| Priority | Hypothesis | Why it can affect official score | Go/no-go experiment, no costly search until gate passed | Status |
|---|---|---|---|---|
| P0 | **Actual executed-cost attribution by opcode and position for representative and adversarial x** | Find which CCX/CCZ/CSWAP and Z_POW gates contribute to mean cost; static heatmaps are not enough. This is profiling, not an optimization itself | Trace or instrument verifier without changing source semantics; confirm counts equal verifier's own report and preserve baseline hash | **No reliable executed-cost profile documented in current registry; check historical logs first** |
| P1 | **Measurement-branch-conditioned CCX cost reduction using reachable predicates** | Only way a free feedback/scheduling rewrite scores is if it provably removes or suppresses executed Toffoli-class work | Pick one high-execution CCX; prove classical guard implication on reachable states across HMR outcomes, produce candidate and check mean delta | **Not established as tested globally; K129/130 covered restricted duplicate fusion** |
| P1 | **Cross-rotation *joint* compensated approximation with phase-error allocation** | May reduce **executed** arbitrary rotations or T-equivalent cost while controlling aggregate phase error | Numeric full-domain certificate first; then exact Kickmix edit; verify with pinned official scorer at matched RNG seed; unlike K098 single-site perturbations | **Partially adjacent work (K098, K116–128); joint nonlocal candidate not documented** |
| P1 | **Targeted reachable-state simplification in post-HMR regions** | Discharge a CCX on states actually possible under valid x and measurement outcomes, rather than independent wires | Dynamic/symbolic reachability at chosen hot scored gate; explicit witness-free proof and source gate drop; bounded verifier | **K131 prefix tried; later HMR region not exhaustively settled** |
| P2 | **New low-Toffoli table/bit-serial rational or digit-recurrence arithmetic** | Completely different reversible evaluation architecture could reduce width or CCX compared with current 62-qubit program | Cost equations including reversible lookup, control, reset, uncompute, phase encoding and minimum qubits; only build if beats 95,369 projected | **Polynomial/Horner, piecewise cubic and generic multipliers tried; digit recurrence architecture not confirmed** |
| P2 | **Phase-correction fusion with scored Toffoli controls across HMR boundaries** | Conditional Clifford predicates may allow moving/simplifying a separate *scored* arithmetic step if complete channel remains unchanged | Exact dynamic circuit/channel proof (including measurement outcome probabilities and phase); one minimal candidate; fail closed on unsupported opcodes | **K139–143 did structural and phase-only work, not scored fusion** |
| P3 | **Global instruction scheduling explicitly reducing expected branch-executed Toffolis** | Conditional execution is what verifier counts; scheduling and guard simplification could lower mean cost without changing logical map | Baseline executed-gate traces, proof of exact guard equivalence, candidate with measured ΔE[CCX] | **No full-circuit evidence in current registry** |

## Rules for future work

1. Before any new `K###`, search this ledger, `competition/experiment_registry.json`, GitHub experiment source, VM logs, and official candidate receipts. Mark what new assumption is being tested compared with known failures.
2. State exactly which scored term changes: `ΔQ`, `Δmean executed Toffoli`, or `ΔT-equivalent`. If all predicted zero, do not run full official verification except for a separate non-scoring engineering reason.
3. Read-only screens are **not** breakthroughs. Output one explicit candidate or a provable no-go per hypothesis; avoid chains of scanners.
4. Keep the pinned immutable baseline intact; the user's VM checkout may be dirty. Download individual pinned script files, never blindly reset/pull.
5. For measurements, compare both phase and outcome distribution; candidate binary seeds the verifier. Partial validation is not an official success.
6. Do not declare success without a retained full-domain verifier result whose score is strictly below 95,369.00696815242.

## Known missing records / source limitations

- K001–K097 individual run outputs remain incompletely normalized; K098 archived results used a nonmatching baseline hash.
- K132–K143 outcomes above were supplied in conversation from user's actual VM runs, and corresponding script commits exist, but not every generated report is committed on GitHub.
- K143 private scoring rule is documented from VM verifier `--help`; private verifier source itself is not available in GitHub.
- Check local files `competition/k*/results`, `competition/k*/run.log`, and previous experiment notes before asserting an avenue is genuinely untried.
