# Local K001–K097 inventory reconciliation (2026-11-12)

**Evidence:** User's uploaded `K001_K097_LOCAL_INVENTORY.json` (289,645 bytes), emitted by read-only inventory script. Local run directories **86/97**. This is a sampled file and selected-metrics inventory, not all underlying JSON results; the uninspected artifacts are not evidence of failure or a missing experiment.

**Missing per-K folders:** K029, K061, K072, K082–K085, K087–K090. **Unknown, not untried.** K001 itself had **626 files, only 120 inspected**, with nested K023–K027 SQLite and KMB candidate files.

## Newly confirmed previously overlooked techniques

| K | Experiment found in local inventory | Observed status / evidence |
|---|---|---|
| 015 | `row_schedule_search.py` | `PASS_SEARCH_NO_VERIFIED_SCORE_WIN`; do not list as merely proposed |
| 016–017 | Precision width, staged precision safety | `PASS_PRELIMINARY_SCORE_WIN`, `PASS_STAGED_TESTED_LEVELS` but **not proof of full-domain winning score** |
| 020–027 | Overnight mutagenic, hybrid adder, frontier, candidate verifier, multimethod, fusion | K023 `PAUSED_BUDGET_OR_PARTIAL`; K026/K027 `STOP_CANDIDATE_BUDGET`; independent finalist K025 `COMPLETE`, not a verified score win |
| 028 | Carry-save vs schoolbook 27-bit arithmetic | 2,164 vs 3,672 CCX, but 1,517 vs 2,674 local qubits; full compiled architecture remained enormous |
| 030 | Official big-arithmetic candidate score audit | Control score ~1,903,125, Wallace score **16,529,548.76**, both far worse than later 95,369 |
| 031–032 | Full-domain precision repair/frontier | best around **1,940,431** (256 qubits); not modern Helios winner |
| 033–035 | Scratch trimming, row-local scratch, selective direct adder | K034 full-domain local improvement **1,933,697**, 255 qubits; K035 no full-domain winners |
| 036–047 | Allocation provenance, watermark, fragmentation, capacity, row-local budgeting | K047 **52** tested cap combinations, **0 prefix winners**. Generic liveness/recycling already heavily investigated |
| 049–056 | Direct phase polynomial, Horner, Walsh, sparse spectrum, monomials, reversible Horner | Mostly numeric/bounded input experiments. K056 x=1..15 only, 321 qubits, not full-domain |
| 058 | Public Helios benchmark `invsqrt.kmb` | K058 log **prefix 91,821.04015062934** on 64 shots; **not full-domain victory**. Historical full-domain reference is 95,369.00696815242 |
| 059–060 | Helios KMx opcode structure, measurement/feedforward trace | Explicit tracing of **874 HMR** in later source audit and conditional neighborhoods. Aggregate/structural profiling is **already done** |
| 062 | Classical parity/conditional phase folding | **5,346 phase gates removed**, 38 blocks; full-domain PASS at **95,369.00696815242** (score unchanged) |
| 063–066 | Nonlinear cancellations, nonlinear blocks, phase permutation motifs, low-angle phase ablation | Previously explored. K063 `NO_CANCELLATIONS` |
| 067 | Classical constant-control removal | Removed two conditional CZ; full-domain PASS at **95,369.00696815242**, unchanged |
| 068–071 | Nonlinear XOR factor, block ANF, dependency cones, phase router | K071 `NO_CHEAPER_CONTIGUOUS_PERMUTATIONS`; source/results present |
| 073–081 | Affine QROM, affine direct phase, range-reduced quadratic circuits, shared predicates, signed multiplier, CSA, phase oracle | K074 bounded, K076–079 prefix only; K080 resource proxy only; K081 numeric/resource only. **Do not call these untried** |
| 086 | Factored exponent coherent quadratic | `PASS_PREFIX_ONLY`; internally **770 CCX** and score **314,930** saved versus its own 409-qubit comparator, still not a Helios score win |
| 091–096 | Exact hybrid nonlinear/phase/CSWAP, classical and polynomial resynthesis | K092 `PASS_FULL` at **95,369.00696815242** despite CX/CZ elimination; K093 CCX variants also unchanged and some CCZ parser errors; K094–096 `NO_NONLINEAR_SAVINGS` |
| 097 | Helios score-path provenance | An early run referenced wrong dfthcsos verifier source; require **invsqrt** corrected receipt |

## Critical caveats

- **Score units:** avoid mixing K058 short prefix **91,821** with K058/K062/K067/K092 full-domain **95,369**. K016's preliminary status and K086's prefix result are **not** full-domain wins.
- **Earlier builder baselines** ranged from 260/255/238/409 qubits. Their relative wins should not be represented as a win over the present 62-qubit Helios program.
- **Versioned provenance:** K058 KMB binary hash begins `1c5b1ee...`, whereas later pinned KMX source hash begins `e7eb438...`. Different file representations/hashes do not establish semantic differences or identical verifier seeds.
- The inventory contains selected keys/log tails, not full reports; many per-run goals and numerical outcomes require examining their underlying `result.json` or `run.log`.
- There is **no basis to rerun generic source profiling, QRR transfer, phase folding, Walsh, Wallace, Horner, width-graph screening, or low-window nonlinear factoring** on the pretext they were untried.

## Actionable remaining *evidence* work (no new science)

1. Check uninspected nested K001 run databases and actual result bodies for K016/K025/K026/K027/K058/K068/K069/K073/K086/K097. Keep private official code/binaries local.
2. Only then mark a proposed algorithm as *untried*, with specific contrast to previous K number.
3. Require positive **ΔQ**, **Δmean executed CCX/CCZ/CSWAP**, or **ΔT-equivalent** before launching optimization. A local free-gate improvement does not change official score.

**Primary user-readable comprehensive per-ID audit:** `K001_K097_RECONCILED_AUDIT.md` generated from the uploaded inventory and supplied directly in the conversation (not uploaded to GitHub to avoid unnecessarily publishing potentially sensitive local artifact paths).