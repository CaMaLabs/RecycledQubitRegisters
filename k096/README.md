# K096 — systematic transfer onto the public competition baseline

**Executed 2026-11-09. Outcome: no verified official-cost improvement.** This is an executed compiler/combination experiment, not another integration specification. One retained-product variant removes a Toffoli but loses overall because it needs an extra qubit. No Kaggle submission or QPU job was made.

## Baseline and metric

Freshly re-downloaded `heliosli/qcc-circuits-live`, portfolio `v101pk0_mx4_ay3`; invsqrt SHA256 `034c7c2a54d51e13aff6e62ec4c14997d3968b6c11122146c57290b1a1b8c7e2`. The download matched the artifact from the earlier audit. Circuit is third-party work: preserve the dataset's CREDITS.md and LICENSE.md and the original authors' lineage. No original circuit is claimed here.

This is the accessible public circuit portfolio, not a claim of access to the current rank-one team's private submission. Native circuit score is lower-is-better; the overall leaderboard also depends on chemistry and DQI.

The unchanged invsqrt verifier is pinned at SHA256 `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a`. It was obtained from the previously documented accessible verifier mirror; the authenticated competition download remains unavailable here. All candidate verification uses that exact file and kickmix 1.0.0.

Baseline: **62 qubits, 1,405 static nonlinear instructions** (1,086 CCX, 93 CCZ, 226 CSWAP), 48 Z_POW instructions. Dynamic mean execution is about 1,242.74 Toffolis and 41 synthesized rotations; static counts must not be confused with executed means.

## Executed matrix

| Test family | Actual execution | Result |
|---|---|---|
| QRR/classical/phase/compiler transfers | 13 individual passes, all 156 ordered pairs, 18 longer chains and baseline: **188 configurations** | 37 distinct circuits; baseline full-domain PASS, other 36 prefix PASS; no resource wins |
| Multi-output shared-product/shear extension | All 37 distinct circuits, **21,953 candidate windows** | No further nonlinear replacement; exact adopted-window equivalence gate remains enforced |
| Retained-product cache | Coherent/measurement erasure × fixed/affine control pairs × raw/combined cleanup, on all 37 circuits: **296 configurations** | 51 additional distinct cached circuits prefix PASS; no winning cost |
| LWE-style full-domain Walsh phase representation | Four invalid-domain/gauge extensions × seven sparse sizes: **28 numerical screens**, each checking every valid x | All fail tolerance; even the best worst-input ratio is about 187 million times tolerance |
| Dark Star/LWE reachable-constraint transfer | Baseline and commutation+symbolic candidate; **4,982 solver queries** | 0 UNSAT gate-removal certificates; 849 SAT, 4,133 UNKNOWN due to query time limits. UNKNOWN is unresolved, not a falsification |
| A114 constructive T ledger | All 37 original distinct circuits | Static exact-construction T upper bound remains 9,836 for every circuit; no T-count gain. This is not the Kaggle metric |

Thus **484 compiler configurations were screened**, yielding **88 distinct circuits checked by the prefix verifier** across the initial matrix and caching extension. These counts do not claim 88 full-domain passes. Numerical Fourier screens and SAT queries are separately reported, not counted as accepted quantum circuits.

The baseline and two representative combined circuits additionally passed **every input 1..3,133,452, two shots/input, two measurement seeds**, using the same batch settings:

| Circuit | Seed 12345 score | Seed 23456 score | Interpretation |
|---|---:|---:|---|
| Baseline | 95,345.60068460317 | 95,345.372269424 | Matched control |
| `candidate_058`: commutation → symbolic state propagation | 95,345.60068460317 | 95,345.372269424 | 86 fewer textual instructions, no scored gain |
| `candidate_170`: CSWAP re-encoding → classical simplification → phase folding → commutation → XOR factoring → commutation → symbolic propagation → lifetime coloring | 95,345.60068460317 | 95,345.372269424 | Combined chain valid, no scored gain |

**Two shots per input is less than the official default 64.** No claimed improvement rests on a prefix, a static proxy, or seed fluctuation. All full-domain receipts and the entire configuration ledger are included under `receipts/`.

### Concrete cache result, including its loss

A new QRR-style retained-product adapter allows an AND to remain cached while its two controls undergo reversible two-bit affine changes. This includes complementing controls and CNOT basis changes. It applies exact corrections when the product is consumed and when the cache is erased. The correction identity was checked over all 24 invertible affine maps of two bits, all basis inputs, and both erasure outcomes.

On the raw public baseline it found two overlapping candidate intervals and selected one interval by weighted interval scheduling. It replaced two repeated CCX computations with one cached computation and two CX uses, then used HMR + conditional CZ/Pauli correction for phase-exact erasure. The interval spans original lines 16050..18340, controls q4/q51. **Static nonlinear count fell 1,405→1,404, but width rose 62→63.** Plain and symbolic-assisted lifetime coloring both still required 63 wires. The baseline-cache prefix score was approximately 96,829.44; the best combined cached variant was approximately 96,823.68, versus baseline prefix approximately 95,345.14. This is a real local saving and an overall score regression, retained rather than hidden.

Coherent erasure and other cache variants that were null or lost individually were still tested in the combined matrix.

## Which earlier work was actually transferred

| Earlier source/mechanism | Application to this baseline | Boundary |
|---|---|---|
| **A110**, `hardware/qrr_a110_commuting_gate_cancellation.py` | Ported control/write-set commutation cancellation to native Kickmix, extended safely to diagonal phases | 3,920 accepted four-wire gate-pair commutations exhaustively checked on 16 basis inputs including sign; no crossing measurement/scope/unknown barriers |
| **A97**, `hardware/qrr_a97_adaptive_modadd_multiplier.py` | Its adaptive equivalent-implementation/whole-circuit comparison principle informs the variant and combination matrix | The actual A87b/A96 selector requires a known odd-modulus modular-adder contract. No such replaceable contract was established in this raw invsqrt gate stream; those adders were not blindly substituted |
| **A114**, `hardware/qrr_a114_clifford_t_resource_audit.py` | Applied a separate exact 7-T CCX/CCZ/CSWAP construction ledger | Decomposition accounting is not itself a scoring optimization. The competition's native Toffoli accounting is unchanged |
| QRR register reuse, cleanup, shared XOR/carry/product ideas | Symbolic zero/support tracking, reset-split wire coloring, retained-product cache, exact single-/multi-target quadratic factoring | Borrowed or entangled inputs are never reset or measured as disposable workspace |
| Existing K062/K063/K067/K068/K071/K093/K094/K095 mechanisms | Classical affine propagation, phase folding, involution cancellation, XOR factoring, router permutation, both global CSWAP orientations, affine bridges, quadratic resynthesis | Individual nulls/losses remain in ordered pairs and long chains |
| LWE Fourier/Walsh original transform family | Actual full-22-bit Fourier spectrum and sparse parity-phase screen, with exact valid input set used for error checks | Numerical rejection only; no approximate phase table was mislabeled as a quantum verifier PASS |
| Dark Star/LWE constraint and pruning mechanisms | SSA/SAT reachability under 1≤x≤3,133,452 and arbitrary measurement outcomes | Only UNSAT certificates permit a deletion. No sampled HMR outcome or secret oracle is assumed |
| Prior full-domain phase-error fitting | Earlier K095 numerical minimax study remains preserved on this branch's predecessor | Its no-headroom result was not silently promoted or redundantly rerun here |

The original A97/A110/A114 source files were read from branch `agent/a24-darkstar-n35-cost-audit-20261030`; exact blob hashes are in `receipts/runtime.json`.

## What remains untransferred, with the missing condition

This is a bounded systematic application, not proof that every possible cross-project technique has been exhausted.

- **NTT/FFT multiplication:** the sparse phase-Walsh screen is not an NTT multiplier implementation. A certified arithmetic-block contract plus a cheaper reversible convolution implementation is still required before replacement.
- **Factoring residues/PTP, order changes, Quaspy and Shor/QPE:** these operate on factoring/order-finding contracts absent from inverse-square-root phasing. Their search/pruning/representation mechanisms can transfer; their number-theoretic conclusions do not automatically apply.
- **LWE noise separation/manipulation, peak/valley and geometric transforms:** a valid approximation or circuit identity respecting the phase tolerance is required. Do not alter the specified target or treat an LWE noise model as a property of this circuit.
- **Broader SAT/SMT synthesis and reachability:** most SAT queries here were inconclusive at 15 ms/query. Longer budgets, smaller isolated cones, and better arithmetic encodings remain open experiments.
- **Entirely new arithmetic architectures and chemistry/DQI-specific rewrites:** not established by this invsqrt gate-stream experiment. The original cross-project search is preserved; these are remaining tasks, not silently discarded methods.

## Reproduce

Use the repository checkout containing `k028/` and `k096/`. Dependencies: numpy, scipy (for the invsqrt verifier), `kickmix==1.0.0`; z3-solver for constraints. Supply the credited public invsqrt artifact and the pinned verifier tree; no credentials are stored in the scripts.

```bash
python k096/run_transfer_matrix.py --base /path/to/invsqrt.kmb \
  --verifiers /path/to/verifiers --out /tmp/k096-run
python k096/extend_multioutput.py --results /tmp/k096-run
python k096/extend_retained_products.py --results /tmp/k096-run \
  --verifiers /path/to/verifiers
python k096/verify_selected.py --results /tmp/k096-run \
  --verifiers /path/to/verifiers --tags candidate_058 candidate_170
python k096/constructive_t_ledger.py --results /tmp/k096-run
python k096/fourier_full_domain.py --out /tmp/k096-fourier
python k096/domain_constraints.py --source /tmp/k096-run/baseline.kmx \
  --out /tmp/k096-sat --seconds 120 --query-ms 15
```

All outputs go to explicitly selected isolated directories. Existing K025/K026 workers and the original public artifacts are untouched. Final code broadens the initial multi-output pass to include shared-target shear synthesis; its separate application across all 37 existing circuits found no changes, so the retained initial configuration outcomes remain valid.
