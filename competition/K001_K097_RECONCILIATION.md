# K001–K097 historical reconciliation (2026-11-12)

**Scope:** reconciliation of the previously omitted early Helios/Kaggle research. This supplement is *not* a declaration that all 97 individual runs have been inspected.

**Evidence provenance:**
- **G**: GitHub versioned repository evidence inspected live in this reconciliation.
- **U**: user's previous pasted terminal output / run history recovered from prior conversations.
- **A**: earlier assistant report or handoff, **not** independently corroborated by a run receipt here.
- **MISSING**: exact raw result artifact not accessible from current GitHub branch or attached files.

## What exists in GitHub now (G)

At commit `7f493c71ae036643f92296feea59961174961c9e`, GitHub's **recursive git tree of the `competition/` directory** had 109 entries, containing directories `k101`–`k143`, `experiment_registry.json`, and the research ledger, but **no tracked `k001`–`k097` source/result directories**. This proves a versioning gap **in this branch only**, not that the early experiments were never run. The user has a local `~/quantum-a26-check/competition/` checkout with private assets and earlier output.

The old `CODEX_HANDOFF.md` in the repo documents a historical worktree state and must not be treated as current branch/VM status.

## Recovered chronological results and exclusions

| ID(s) | Experiment / outcome | Evidence | Decision / caveat |
|---|---|---|---|
| K001 | Acquired/inspected 35 official benchmark files, including `invsqrt.kmb` (~579,721 bytes), verifier/reference/scoring sources | U | Official benchmark assets were reviewed; do not repeat initial discovery |
| K003 / K009 | Early opcode/gate statistics and structural profiling reported as completed | A | Profiling already approached; raw receipts unavailable here |
| K004 | 260-qubit baseline smoke test: 62,160 ops, depth 4,005, 7,735 Toffoli-like operations, 16 sampled shots; reported score ~2,063,226.28 | A | **Smoke test**, not full-domain Helios final score |
| K006 | Corrected source cancellation removed two pairs (four instructions); scored resources unchanged | A | Free-gate rewrite; no scored win |
| K012 | Reviewed 17 transferable ideas (10 QRR, 7 LWE), none proven legal/scoring wins; plus early recycling studies | A | Prior transfer review exists; do not redo generic survey |
| K013 | Exhaustively screened 12 local identities; zero matches | A | Stop identical local rewrite library |
| K014 | Attributed 6,521 of 7,735 Toffoli-like operations to small (<=6-wire) arithmetic regions; identified CSWAP and arithmetic helper hotspots | A | **Hotspot profiling already performed**; do not repeat broad scan |
| K015 | Source-level row-scheduling search was proposed | A | **Result unknown**; do not label executed or untried without local receipt |
| K025 | Independent finalist verification was running at 32,768 and 65,536 inputs for top candidates / seeds | U | No record here of official winning result |
| K026 | Overnight multimethod campaign reached 4,000 candidates, 167 generations, 5,433 verifier tests, 490 partial passes, 235 static wins, 2,672 model rejects, 436 arithmetic overflows, 73 official rejects; cost proxy frontier ~1,851,045 through x=65,536 | U | Large campaign already attempted; partial success **not** an officially verified improvement |
| K028-B | Wallace-style 27-bit multiplier prototype: 5,007 primitive gates, 2,164 CCX, depth 264, 1,517 qubits vs reference 9,531, 3,672 CCX, depth 1,578, 2,674 qubits; 46 local tests | A | Local gate reduction, but width dominates cost; don't repeat Wallace without better recycling |
| K028-C | Compiled Wallace `wallace_m.kmb` smaller than control binary (493,546 vs 539,354 bytes), but later official audit scored ~16,529,548.76 due to 1,692 qubits / 9,565 nonlinear gates | A | **Binary size is not score**; rejected architecture |
| K040 / K044 / K047 | Early workspace/width/liveness profiling and constrained recycling; a historical 255→238 qubit improvement, 216 peak live against 238, 52 workspace configurations without further win | A | These are earlier circuits, **not** a demonstrated reduction below current 62-qubit Helios baseline |
| K056 | Profile run referenced alongside K040/K059; exact outputs unavailable | U | Mark inspected but outcome unconfirmed |
| K058 | Public `invsqrt.kmb` **binary SHA beginning `1c5b...`**, 62 qubits, 53,818 operations, depth 743, 41 rotations; two full-domain verifier passes scored **95,369.00696815242** and **95,369.18991398979** respectively; first mean executed Toffoli-like ~1,243.1189659, worst case x=161 / error ratio ~0.99932377 | **U, full verifier transcript reported** | This is **the proven score reference**; preserve binary/circuit seed and distinguish from later source hashes |
| K059 | Ran `helios_public.kmx` source report: 53,841 instructions; 1,090 CCX, 93 CCZ, 226 CSWAP, 874 HMR, 29,551 CX, 16,478 CZ, 578 BIT_INVERT | **U** | Static opcode counts are not executed averages; do not repeat |
| K067 | Conditional/classical gate and measurement profiling previously reported | A | Raw output not currently recovered |
| K080–K090 | No specific per-ID result receipts recovered in this reconciliation | MISSING | **Unknown, not untried** |
| K091–K098 | User compared local saved `.kmx` copies and reported common SHA `e7eb4386...04183`; **different from K058 benchmark `.kmb` hash** | U | Cannot compare hashes of different representations as proof of different semantics; don't conflate verification |
| K092–K096 | Exact experiment-by-experiment outcome not recovered | MISSING | **Unknown, not untried** |
| K097 | Audit of 53,841-source-line Helios benchmark; early source audit initially used the **wrong `dfthcsos` verifier** and was corrected to `invsqrt` | U | Treat earlier wrong-task results as invalid; inspect corrected reports before further claims |

## Additional cross-run work (prior reports, IDs not established here)

These items were reported from prior campaigns but do **not** yet have a reliable K-number-to-artifact mapping; do not assign invented IDs:

- Transfer sweep from QRR, LWE, Dark Star: **484 configurations**, **88 prefix-verified circuits**, no demonstrated below-baseline full-domain result (A).
- A retained-product cache saved one CCX but increased width **62→63**, thereby worsening score (A).
- **28 sparse Walsh variants** failed required phase tolerance (A).
- Measurement-branch-aware scratch reuse found **2,455** recomputation opportunities / gaps, but no design beat the 62-wire bottleneck (A).
- **20 suspected phase deletions** generated SAT counterexamples (A).
- DQI/Clifford-heavy rewrite reportedly removed **8,982,144** free operations with unchanged score (A; aggregate across execution counts, not a literal source-file edit count).
- Chemistry-offset numeric refit reported a tiny relative improvement but no credible competitive score gain (A).

## Definitive scoring and the provenance trap

Private invsqrt verifier `--help` was pasted by user in this conversation. It states:

`score = Q * (mean executed Toffoli-like + mean T-equivalent/4)`.

Toffoli-like includes CCX, CCZ, CSWAP, and T-equivalent includes T and synthesized non-Clifford `Z_POW`. Clifford Z/CZ/CX are free **directly**.

**The score 95,369.00696815242 is directly associated with the K058 `invsqrt.kmb` full-domain verifier outcome.** The pinned `.kmx` source SHA `e7eb4386...04183` may be behaviorally equivalent, but it is not byte-for-byte the same artifact and verifier seeds measurements from the compiled KMB bytes. Therefore a source SHA match by itself is not evidence the scored binary/seed is identical.

K058 mean Toffoli ~1,243.119, 41 rotations, 62 qubits are documented in user transcript. A previous assistant added approximated `294.841` rotation cost in Toffoli-equivalents and `C≈1538.210`; treat this as rounded/derived until checked against a machine-readable receipt, not an independently verified full-precision breakdown.

## What remains genuinely unconfirmed

The following are **records to locate**, not suggestions for redundant new science:

1. **K015–K024, K027, K029–K039, K041–K043, K045–K055, K057, K060–K066, K068–K096:** raw `summary.json`, `*.json`, `*.log`, and code metadata needed to assign each ID a technique and result.
2. Whether the exact **per-instruction dynamic executed-frequency** profile was already generated (aggregate attribution **has** been done).
3. The exact K058 source binary hash, verification CLI parameters and retained verifier receipt, plus whether the pinned later K098 source compiles to the same verifier-seeded representation.
4. Which of the 484 transfer configurations and 28 Walsh candidates belong to which K IDs, without inferring their IDs from narrative.

## One-pass, *no re-execution* local evidence inventory

The file `competition/K001_K097_LOCAL_INVENTORY.py` walks only local filenames and small JSON metadata for `competition/k001`…`competition/k097`. It **does not execute benchmark simulations or alter results**. Its receipt can close the gaps above.

Do not use `git reset`, `git checkout`, forced pull or destructive cleanup on the working VM. Copy any discovered receipts into a distinct audit output directory before committing anything. Any entries missing from the repo remain **UNKNOWN**, not "never tried".

## Reconciled decision

**Already done:** aggregate baseline profiling, arithmetic hotspots, several width/recycling campaigns, large candidate search, Wallace alternative, sparse phase approximation, phase-drop/SAT checks, QRR/LWE/Dark Star transfer screening.

**Still not demonstrated in available evidence:** exact *per-source-instruction* dynamic frequency receipt; a globally certified **scored** rewrite for the later measurement-reachable arithmetic; a joint compensated non-Clifford phase edit that beats the K058 score. These are research options **only after** local K001–K097 receipts have been checked, not fresh tasks to launch now.
