# Cross-project integration map — restored prior instructions, 2026-11-09

This supplements the competition audit. The earlier audit concentrated too heavily on the current invsqrt implementations. It does not establish that all historical QRR, LWE and Dark Star methods, or their combinations, have been transferred and tested.

## Governing research requirements

- Preserve older approaches and positive and negative results.
- Retain methods that lost individually in the combination matrix. A standalone loss is evidence about that configuration, not proof that every combination loses.
- Distinguish proposed, implemented, isolated-tested, whole-task-tested and official-verifier-passed. An integration specification or adapter is not completed integration.
- Preserve coherent inputs, full phase behavior and clean ancillas. No QPU jobs are needed for this competition search.
- Count actual competition cost, not improvements from unrelated hardware metrics or multiplication of separately measured gains.
- Keep Dark Star factoring, QRR compression and LWE cryptanalysis scientifically distinct while transferring applicable mechanisms.

## Historical methods that must remain in the matrix

The source of the historical statuses below is retrieved prior conversation, unless a repository source is explicitly identified. These are leads to verify against source and receipts, not newly reproduced results.

| Family | Mechanisms to carry forward | Historical evidence and transfer boundary |
|---|---|---|
| QRR arithmetic | A97 adaptive arithmetic; shared XOR/carry; complement constants; validity and wrap comparator simplification; retained products; ancilla-free and borrowed-ancilla adders | Prior Kaggle discussion said A97 was not yet applied at that point. One ancilla-free adder lost all 24 whole-circuit comparisons; keep it for combinations rather than silently deleting it. |
| QRR phase-aware synthesis | A110 cancellation and A114 constructive Clifford+T reductions; phase-exact cleanup and relative-phase constructions | Earlier competition discussion reported A110 removed four instructions; A114 had not been transferred then. Later transfer studies must be checked individually. Clifford+T savings are not automatically kickmix score savings. |
| QRR register compression | Lifetime sharing, reusable clean workspace, dynamic measurement/uncompute, shared pair/triple predicates | Source width 32→23 was real in its original task but failed native resource gates. Many later Kaggle components exist; identify the exact combinations actually measured, not just the method names. |
| LWE original transforms | Fourier/FFT/NTT, peak/valley transforms, polynomial and noise-separation ideas, recursive pruning, public constraints, geometric search, structure-preserving rotations | Retain original methods alongside later lattice methods. A transform being reversible does not guarantee preservation of noise/support assumptions. Transfer candidate construction or arithmetic identities, not an unsupported cryptanalytic conclusion. |
| LWE later optimization | Reused bases, negacyclic/ring transformations, adaptive search and bounded selection | Reported reused-basis recoveries were matched replay, not established genuine ML-KEM recovery. Candidate/basis reuse may help offline search; a Kaggle circuit gain requires its own complete test. |
| Dark Star original work | Prime/residue tables, Fermat/PTP constraints, public preprocessing, recursive candidate pruning, bounded routing/selection | Conditional improvements and failed predictor/holdout results must both remain. No generic factoring shortcut is assumed applicable to invsqrt. Seek proven unreachable branches, restricted-domain logic and offline search reductions. |
| Cross-project phase work | Full-history phase reweighting | Earlier PR #12 reportedly improved its own phase-estimation benchmark, but that is not the inverse-square-root angle refit tested in this audit. Do not conflate the experiments or their evidence. |
| Combined integration | Classical preprocessing + arithmetic choice + reversible synthesis + workspace reuse + phase-safe cleanup | K027 explicitly requested all-method fusion, including individually negative methods. Its specification is not an implemented, verified full integration. Compare combinations and ablations on the same whole-task baseline. |

## Existing Kaggle source anchors

- K027: branch `research/k027-all-methods-fusion`, `docs/K027_ALL_METHODS_FUSION.md`; inspected integration specification.
- K082–K085: `k028/k082_k085_transfer_suite.py`; inspected isolated mechanism suite, not by itself a whole-task verified integration.
- K086–K090: actual coherent circuit variants exist. Their source presence does not prove all older mechanisms are integrated.
- K091–K094: public-baseline exact compiler rewrites; useful but narrower than the complete cross-project request.
- A separate, newer `k028/k095_symbolic_quadratic_resynthesis.py` now exists on `research/k028-native-arithmetic`. It is distinct from this branch's `k095/` audit and phase-fit experiment. Do not merge their results by number alone. At this inspection its `sha` helper exists, but `main` also references `load`; startup completeness and actual run receipts still need checking.

## Required experiment accounting

For each original method and each selected combination, record:
source project/path/commit; semantic identity or approximation contract; adapter status; exact tested baseline; whole-circuit qubit/Toffoli/rotation resources; verifier settings and receipt; interaction with other transforms; and rejection reason if incompatible.

The next implementation decision must follow this map and the earlier competition conversation. The audit's suggestion to examine DQI/chemistry does not replace or cancel the authorized cross-project fusion work.

No additional score win or completed combination experiment is claimed by this map.
