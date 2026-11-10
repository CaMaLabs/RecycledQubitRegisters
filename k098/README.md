# K098: chemistry compiler and fixed-angle normalization search

Research lead: Chase Lunsford / CaMaLabs. Executed November 9, 2026 Pacific.

**Outcome: a reproducible but practically negligible chemistry cost reduction. No leaderboard win.** The unchanged chemistry verifier at its default 64 shots per address returned the same candidate cost at both explicit measurement seeds. All circuits remain byte-identical to the credited public baseline; only the scorer-used H2_I offset weights change; auxiliary offset_W is updated consistently.

| Setting | Baseline | Offset candidate |
|---|---:|---:|
| Official component cost, seed 12345 | 299,614,710.21253383 | 299,614,710.18364155 |
| Official component cost, seed 23456 | 299,614,710.21253383 | 299,614,710.18364155 |
| lambda_eff | 46.8907908586437 | 46.89079085412195 |
| Total Toffoli count | 14,964 | 14,964 |
| Total qubits | 427 | 427 |
| Shots per address | 64 | 64 |
| All 1,220 addresses, forward and reverse traversal | PASS | PASS |

The cost difference is **0.02889228**, approximately **9.64e-11 relative**. This is far too small to be a useful leaderboard edge. It is not presented as a significant quantum improvement. The energy-gap floor and both 20 mHa residual gates are enforced without clamping or modifying any scorer.

## Source and verification

Public source: https://www.kaggle.com/datasets/heliosli/qcc-circuits-live, portfolio v101pk0_mx4_ay3. Original factorization SHA256 is recorded in offset_patch.json. The source manifest and all four unchanged-verifier receipts are under receipts/.

The public portfolio credits syed3000's table/loader and the marculera/Özer pipeline, with Heliosli/maoxin123 refit lineage and pramitdas's ANGLE_0. Preserve that dataset's complete CREDITS.md and LICENSE.md. The baseline is third-party work. This experiment applies our own offset search and cross-project compiler adapters to it.

Verifier code is the documented accessible mirror in Inzainos/quantum-circuit-compilation. Its hash, exact package versions and the reference FCIDUMP hash are in receipts/runtime.json. FCIDUMP/fixed shifts came from the hosts' public starter-kit dataset and pass the verifier's own integrity checks. The authenticated competition package was not available in this environment, so this is local verification, not a Kaggle-scored submission.

## What was actually tested

1. **QRR retained-product reuse on all 15 ANGLE circuits.** Existing fixed/affine-control AND caching was applied with measurement-based erasure and a long search window. No profitable cache groups were found. The family was unchanged, so the baseline verification was a real default-configuration run rather than a candidate proxy.
2. **Analytic constrained offset refit.** Circuit-loaded words were recovered and independently checked against the stored angle table. Two-body weights and every angle circuit stayed fixed, so the two-body residual cannot change mathematically. The 352 H2_I offsets were optimized with analytic eigenvalue derivatives, full one-body residual, original strict gap floor and original normalization floor. Four independent finite-difference direction checks validated gradients away from absolute-value kinks. SLSQP used 107 model evaluations and 14 callback iterations. The candidate was then checked by the unchanged complete verifier, independently of the optimizer's model.
3. **Exact two-column gauge rotations.** Rotating w and H2_I columns together leaves the represented Hamiltonian, one-body target, SOS energy and both error contracts invariant in exact arithmetic. Only the L1-based LCU normalization changes. Every absolute-value breakpoint and stationary point was checked for each of the 7,568 column pairs across eight groups. None improved the published table. The minimizer was independently compared with 10,001-point grids on 12 random tests, and Gram invariance was checked.
4. **Combinations that lose individually were retained.** The pairwise-null result was followed by random coupled orthogonal moves in 3, 4, 6 and 8 columns, with exact pair-coordinate cleanup after each kick. There were 1,200/600/240/120 selected column sets respectively, 2,160 total, with multiple random restarts and up to 30 cleanup sweeps. No normalization improvement was accepted. These are numerical architecture searches, not additional verifier-passed quantum candidates.

A separate exact reshape-cost check considered merging groups while preserving all loaded vectors and physical factors. The heuristic Toffoli count increased from 6,662 for (R,B,C)=(8,143,44) to 10,030/16,677/29,946 for the exact merged shapes. Those were rejected at the resource-model stage; no new circuit validity is implied by that model check.

## Reconstruct or reproduce

The small offset_patch.json stores the absolute tested H2_I values and pins the source NPZ hash. It avoids redistributing the public circuit binaries. This reconstruction was checked to reproduce every candidate array and the NPZ hash exactly.

```bash
python k098/apply_offset_patch.py --source /path/to/dfthcsos__submission.npz \
  --patch k098/offset_patch.json --out /tmp/candidate/submission.npz
# Put the unchanged public angle_k_0..angle_k_14 files beside that NPZ.
python /path/to/verifiers/dfthcsos/verify.py /tmp/candidate \
  --shots-per-address 64 --seed 12345
```

The public dataset's flattened names dfthcsos__angle_k_N.kmb must be copied as angle_k_N.kmb in the candidate directory. Refit, gauge and cache scripts have explicit source/output arguments. The search scripts emit numerical candidates only; the unchanged complete verifier is the acceptance gate.

No paid quantum runtime, QPU submission, live worker modification or Kaggle submission occurred. The overall leaderboard goal remains unmet.
