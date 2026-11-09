# K095 competition and cross-repository audit — 2026-11-09

**Outcome: no leaderboard-beating submission found.** No Kaggle submission was made. Negative results are retained; neither fewer textual instructions nor tiny measurement-seed fluctuations are treated as a score improvement.

## Scope and evidence

Inventoried all 38 repositories exposed by the connected GitHub installation. Read their complete default-branch filename trees (one repository is empty), then examined the relevant quantum sources and research branches. This is a cross-repository relevance audit, **not an exhaustive line-by-line review of every repository or historical branch**. Inventory and commit/tree identifiers: `repository_inventory.json`.

The important competition implementation is in RecycledQubitRegisters branch `research/k028-native-arithmetic`, inspected at commit `9d556cf5a9a8c35fa556492d118ae275d34c7437`, not its default branch. K027's other branch contains a research specification, not an implemented all-methods search. K001–K026 receipts and the user's live `~/quantum-a26-check` workspace were not accessible here. Older numerical claims from conversation are not independently reproduced results.

Other relevant sources: QRR's reversible arithmetic, measurement cleanup and XOR/ancilla work; LWE_GeometryLab's Walsh transforms, public constraint searches and quantum optimization pilot; Dark_Star's cryptography project. Android-compute-cluster provides reusable compute infrastructure, but its Kaggle CABT plugin targets Pokémon, not this competition. No directly applicable quantum compilation files were found in the other repository trees.

## Techniques already implemented or investigated

“Implemented” here means inspected source exists; it does not imply an accepted full-domain competition result.

| Technique | Evidence | Actual evidence boundary |
|---|---|---|
| Newton/Horner arithmetic, precision and phase truncation | K029–K032 | Full-domain verification support exists; local receipts not all available |
| Ancilla recycling, row-local scratch, coefficient lifetime scheduling | K033–K047 | Built circuit experiments; K040 is the previously reported own frontier, not reproduced in this session |
| Schoolbook/ripple, controlled additions, carry-save/Wallace multipliers | native arithmetic, K035, K079–K080 | Includes exact small arithmetic tests; microbenchmarks are not whole-task scores |
| Piecewise Chebyshev/polynomial fitting and integer Horner | K049–K056, K075–K077 | Numerical screens, bounded-domain circuits and larger coherent prototypes are distinct |
| Walsh/parity and Boolean monomial direct phase synthesis | K053–K055 | Bounded-domain circuits; not a full 22-bit solution |
| Affine QROM encoding and measurement-uncompute | K073–K074 | Small symbolic/finite-state studies and bounded phase circuit |
| Shared pair/triple predicates and exponent factoring | K078, K082–K090 | Implementations exist; do not list these as untried |
| Classical affine feedforward propagation and diagonal parity folding | K062, K067, K092 | Preserve quantum measurement outcomes as unknown classical variables |
| Involutory cancellation, shared-control Toffoli factoring, local ANF resynthesis | K063, K068–K069, K091 | Conservative exact rewrites; new scans below found no nonlinear gain |
| Controlled-permutation and parity-router re-encoding | K071, K093–K094 | Exact identities implemented; encoding changes alone do not reduce scored Toffolis |
| Relative-phase Toffoli, QAOA, physical routing | QRR/LWE and K084 | Separate pilot/operator/hardware studies; not an established Kaggle advantage |
| Fourier/NTT arithmetic, blanket cross-method fusion, full QROAM substitution | K027 specification / K028 notes | Proposed or partially studied; no completed whole-task integration found |

## Today's actual tests

Public circuit source: https://www.kaggle.com/datasets/heliosli/qcc-circuits-live, release `v101pk0_mx4_ay3`. This is **third-party work**, carrying the authors and upstream lineage recorded in that dataset's `CREDITS.md`. Current invsqrt SHA256: `034c7c2a54d51e13aff6e62ec4c14997d3968b6c11122146c57290b1a1b8c7e2`. This differs from the older `1c5b1e...` artifact pinned by K091–K094.

Verifier was obtained from an accessible mirror, https://github.com/Inzainos/quantum-circuit-compilation/tree/main/verifiers. Its invsqrt file SHA256 is `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a`, matching the independently published verifier checksum. Source was not modified. Authenticated competition-data download returned HTTP 401, so exact provenance as the user's installed competition kit could not be checked. Kickmix PyPI version 1.0.0 was used.

| Test | Measured result | Decision |
|---|---|---|
| Public baseline, every x=1..3,133,452, 2 shots/x, seed 12345 | PASS, Q=62, score 95,345.561062 | Reproduced baseline, not own gain |
| Same domain, 2 shots/x, seed 23456 | PASS, score 95,345.372269 | Seed variation is not an optimization |
| K094 bridge pass on latest baseline, original and both global CSWAP orientations | 0 bridge rewrites | No nonlinear savings |
| K069 local ANF, up to 8 qubits / 100 gates | 443 windows, 0 replacement blocks | No savings |
| Broader exact gate commutation within unconditional unitary regions | 42 CX and 6 X removed | Clifford-only, no score advantage established |
| Quantum-state symbolic propagation and clean-reset lifetime coloring | 30 zero CX and 8 redundant SWAPs; width remained 62 | No scored gain |
| Global reachable-state linear-span replacement in chemistry | 15 circuits, no nonlinear reduction when both forward/reverse entry word states are included | Reject initial zero-word-only savings |
| Joint minimax refit of all 41 non-Clifford q28 angles | Full-domain predicted minimum phase slack 3.1765959836e-12 turns | Matches existing public optimum; no useful new headroom |
| Rebuilt unconstrained refit, every input, 2 shots/x, seed 12345 | PASS, score 95,345.600676, same width and rotation count | No gain over matched baseline 95,345.561062 |
| Joint refit with smallest adjustable q28 rotation removed (column 16) | Best full-domain slack -3.2710908059e-12; verifier FAIL at x=161 | Rejected |

These baseline runs use **2 shots per input, not the default 64 shots**. They exhaust the integer input domain but do not replace the default measurement-fuzzing configuration or a Kaggle score. Actual JSON verifier receipts are included. The diagnostic feature circuit deliberately copies intermediate rotation controls into extra wires; **it is never a submission candidate**.

The minimax fit is an offline numerical screen, followed by real-circuit verification for the rejected drop candidate. Its full-domain feature extraction covers every input and one measurement trajectory per input; it is not a formal proof over all measurement outcomes. The original circuit's unmodified two-seed verifier results establish the baseline; the full-domain refit PASS is retained as a negative A/B result, not promoted as an improvement.

## Promising gaps not found as completed competition implementations

1. **Chemistry factorization and loader co-design.** Optimize the actual full score `lambda_eff * T_total * Q_total`, with rank/ensemble reduction, angle quantization, bank sizes and weight refit together. Current own experiments overwhelmingly target invsqrt. Changing one chemistry circuit in isolation can miss the dominant heuristic resource cost and the strict Hamiltonian accuracy gates.
2. **DQI finite-field arithmetic and product-lifetime reuse.** Audit repeated GF products, constant multiplications, Reed–Solomon decoder stages and terminal measurement cleanup in the current public decoder. QRR's shared-product/ancilla ideas transfer more directly here than Shor order finding itself. No comparable own DQI experiment suite was found.
3. **Measurement-aware SAT/SMT or exact Boolean synthesis.** Current ANF resynthesis handles small contiguous, unconditional windows. Larger windows with explicit classical state, reachable input constraints, complete phase tracking and proof certificates remain an implementation gap. Never discard a phase correction just because basis values match.
4. **Full QROAM/SelectSwap cost sweep.** K073's affine measurement-uncompute study is not a completed QROAM replacement on the actual chemistry tables. Test dirty/clean workspace schedules under the 128-qubit cap and total cost, including uncomputation.
5. **Certified global approximation plus circuit synthesis.** Rather than another unconstrained polynomial with hundreds of scratch wires, optimize a smaller domain-aware Boolean/lookup representation and prove all retained branches. K095's chemistry test shows why both valid forward and reverse entry states must be included.

Physical routing, GPU acceleration, Shor/QPE and cryptographic key recovery do not directly lower this competition's scored logical circuit resources. They may improve development throughput or supply compiler components; those benefits must not be reported as a Kaggle score gain.

## Reproduce the phase-fit experiment

Install `numpy`, `scipy`, `kickmix==1.0.0`. Obtain the credited public dataset and verifier tree separately. The extractor pins both circuit and verifier hashes and refuses a different version.

```bash
python k095/extract_phase_features.py \
  --source /path/to/invsqrt.kmb \
  --verifiers /path/to/verifiers \
  --out /tmp/k095-fit
OPENBLAS_NUM_THREADS=1 python k095/fit_phase_angles.py --work /tmp/k095-fit
# Optional deliberately rejected rotation-removal experiment:
OPENBLAS_NUM_THREADS=1 python k095/fit_phase_angles.py --work /tmp/k095-fit --drop 16
python /path/to/verifiers/invsqrt/verify_submission_invsqrt.py \
  /tmp/k095-fit/refit.kmb --max-x 4095 --shots-per-x 2 \
  --batch-size 63 --max-workers 1 --seed 12345
```

The fit scripts overwrite only their explicitly selected output work directory. Original public artifacts and local active research workers are not modified. A feasible numerical fit must still pass the untouched verifier before any score claim.

## Leaderboard comparison

Competition: https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation

The overall metric is the geometric mean of the three reference-cost/candidate-cost ratios. A retrieved leaderboard snapshot listed **27.15971** at rank one, but it was cached and is not a verified live standing. Today's public portfolio advertises component ratios about **21.7815, 65.2262, 11.200**, whose geometric mean is **25.1522**. Those chemistry/DQI ratios were not independently verified here. Even adopting that complete public portfolio would therefore not demonstrate beating the retrieved leading score.

**Success criterion remains unmet.** No generated candidate from this session justifies claiming a leaderboard win or a new best invsqrt cost.
