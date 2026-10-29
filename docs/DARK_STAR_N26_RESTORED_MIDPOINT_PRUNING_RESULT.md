# Dark Star original midpoint pruning restored: 12-case exact audit and revised unified-classical replay

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-28. **Verified original pruning restored, no practical end-to-end speedup demonstrated.** Zero IBM hardware jobs or paid/free Runtime.

## Which original pruning was missing?

Dark Star v2 used **composite-specific Fermat midpoint pruning** from the PTP residue structure. Given odd N with a Fermat factorization `N=x*x-y*y`, possible midpoint x residues must satisfy public necessary congruences `x*x-N ≡ y*y (mod ell)`. An x failing the quadratic-residue test for ANY small prime ell cannot be a factor-producing midpoint. This safely eliminates *exact square-root tests* at many positions. The old `darkstar_v2.midpoint_residues` enumerated possible factor-root pairs `q=N*inverse(p) (mod M)`, converted to valid midpoint residues, sorted them, and jumped between allowed x positions. The earlier original reported ~28.8x square-root-test reduction with M=15015 but only 0.84x **overall** end-to-end throughput after its large per-N table setup.

The recent unified implementation kept short `M=105` and `M=15015` midpoint stages capped at **12 exact square-root tests each**. It omitted the stronger extended `M=255255=3*5*7*11*13*17` sieve and did not allocate the needed geometric midpoint span after those restrictive root budgets. The N26 published first-pass result, therefore, correctly recorded one classical-budget survivor but did **not** test the full original pruning method under an optimized setup.

## First audit: same immutable N26 inputs, no new holdout

- [Protocol frozen before implementation](DARK_STAR_N26_RESTORED_MIDPOINT_PRUNING_PROTOCOL.md).
- [Original public N26 manifest](../results/dark_star_unified/unified_n26_public_manifest.json), unchanged selected-row SHA **`0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939`**.
- [New standalone public-only quadratic residue sieve](../integrations/darkstar_hybrid/midpoint_qr_pruner.py). It prepares a small lookup for each ell and `N%ell` instead of computing thousands of inverse factor-pair residues for every N. It scans x within a **fixed 4096-midpoint-coordinate window**, rejects when any quadratic-residue membership is impossible, and calls `isqrt(x*x-N)` only if all public masks permit. It never receives p/q/order.
- [Exact 12-case comparison script](../integrations/darkstar_hybrid/darkstar_midpoint_pruning_reaudit.py) and [full immutable JSON receipt](../results/dark_star_unified/unified_n26_midpoint_pruning_reaudit.json).
- [Successful original scientific GitHub Actions run **40801569711**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40801569711). All 12 rows passed, source preserved, no QPU.
- **181,440 exhaustive prime-wheel residue-membership checks** (`12*(105+15015)`) proved the new QR sieve and legacy inverse-factor-pair table accept **exactly the same allowed midpoint residues** for both original wheels `M=105` and `M=15015`. All 12 factor results match plain Fermat and the original v2 table search; zero false rejection. For `M=255255` the same necessary-congruence proof independently establishes safe pruning, and all original N were factored.

### Measured operation counts and timing outcomes

Median reduction in *expensive exact square-root tests* versus plain Fermat across the twelve:
- **M=15015: 22.75×** fewer exact square-root tests.
- **M=255255: 47×** fewer exact square-root tests.

**Measured total setup+search microbenchmark gate:** M255255 was faster than a same-run conventional wheel210 trial-factor routine in **7/12** cases, and faster than a same-run original PTP LFK/kernel factor routine in **6/12**. The frozen strict gate required a majority (>=7/12) versus BOTH classical baselines. **GATE FAILED**, therefore this is **not a demonstration of better overall factorization runtime**. More aggressive quadratic-residue filtering trades fewer expensive exact squares for extra modular checks, Python loop overhead and mask setup; microsecond timing is noisy. No physical quantum gates or native circuit performance were tested.

### The single original N26 weak-classical-budget survivor

**N=49,273,331**, public base 17, verified factors **4703×10477**.

| Public factoring method | Exact square-root tests | Midpoint positions explored | Outcome |
|---|---:|---:|---|
| Plain Fermat | 571 | 571 | Factor found |
| Original PTP M105 | 64 | 571 span equivalent | Factor found |
| Original PTP M15015 | 14 | 571 span equivalent | Factor found |
| Stronger PTP M255255 | **8** | **571** | Factor found |
| Old unified `M15015` capped at 12 | **12 then stop** | shorter | **No factor within old budget** |
| New full unified fallback `M255255`, cap 12 square tests and span 4096 | **8** | **571** | **Factor found** |

Under the verified revised classical route, the N=49,273,331 case uses **985 quadratic-residue membership checks** and 8 costly integer square-root tests, with both bounds (max 4096 midpoint positions, max 12 exact square-root tests) enforced. This means the earlier need for its **simulated** quantum step was an artifact of a weakly capped classical front-end; the original ideal-QPE counterfactual remains a correct separately archived model outcome but is **not** practical evidence quantum factoring was needed.

## Follow-through: safe integration into the unified program

The [unified program](../integrations/darkstar_hybrid/darkstar_unified.py) now includes a **public-only, bounded `restored_midpoint_QR_255255` stage** after its original p-1/rho/trial budget. The stage has both a hard 4096-coordinate midpoint cap and a hard 12-integer-square-root cap; it counts QR modular membership work, setup, scanning, exact squares and verified factors. All original earlier N26 JSON science receipts and their 11/12 classical conclusion remain UNCHANGED.

- [Classical-only historical replay script](../integrations/darkstar_hybrid/darkstar_n26_restored_classical_replay.py).
- [Successful independent test/replay run **40801831973**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40801831973), including the updated unified integration tests.
- [Machine-readable, secondary classical-replay JSON](../results/dark_star_unified/unified_n26_midpoint_restoration_classical_replay.json).
- **Original N26 published outcome: 11/12** solved under the older fixed public classical budget. **NEW post-hoc replay: 12/12** solved under the restored classical budget. Exactly one changed row, N49,273,331, as expected; the other 11 methods and factors remain exactly the same. This is a *revised algorithm with altered stopping budget*, not a new independent sample and not a rewritten original experimental result.

## Separate quantum-circuit pruning remains a distinct track

The repo also has [N35 public identity controlled-modmul pruning](../hardware/qrr_n35_public_modarith_identity_pruned_preflight.py): when `pow(base,2**k,N)==1`, the controlled U is identity and can safely be omitted without using private order. It has [N35 proven unused nine-wire dynamic scratch removal](../hardware/qrr_n35_true_recycled_prune_idle_scratch.py), which reduced source width **32→23 qubits** but **FAILED** the preregistered native CZ/depth robustness gate across original seeds ([full result](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md)). The new unified CPU *source clean-MCX cost counter* still charges identity modmul when it appears and does not assert it can drop the clean-MCX scratch for arbitrary N. Those optimizations require separately validated structural and circuit-side integration; neither is magically included by restoring PTP midpoint pruning.

## Conclusion

**The user was right to revisit the original pruning.** It is implemented, validated and restored to the unified algorithm, and it materially changes which stage finds the one original N26 survivor. Its strong reduction in square-root operations is genuine under an exact modular proof; **the whole factorization speedup gate remains unpassed** against competent classical references. The correct next step is an independent public-only fresh population with the restored version frozen *before* selection and scoring, alongside costed public identity-U circuit pruning only if semantics are preserved. Do not claim real QPU use, paid runtime, RSA-2048/ML-KEM break, or a proven new factoring complexity bound.
