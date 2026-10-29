# Dark Star N28 public router versus identical standalone Brent: secondary mechanism falsification

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-29. **Secondary router-specific incremental speed gate: FAILED.** Zero real quantum jobs, zero paid or free IBM Runtime. This is an explicitly **post-hoc head-to-head on the SAME previously sampled sixteen 28-bit cases** and must NOT be treated as an independent fresh holdout.

## Original positive milestone remains preserved

The original, prospectively frozen [N28 public-router result](DARK_STAR_PUBLIC_COST_ROUTER_N28_RESULT.md) was successfully completed and added to `docs/RESEARCH_LOG.md` **before** this additional experiment. Original [16 complete raw outcomes](../results/dark_star_unified/darkstar_public_router_n28_original_16_holdout.json) and the source SHA remain unchanged. Against the two original precommitted Python baselines, the public router was faster than standard wheel210 in **16/16** cases and faster than PTP/LFK in **13/16** (original primary speed gate **PASS**). On the 16 semiprimes, however, Brent Pollard rho alone supplied **15/16** of the router's factors; one case was caught by the early Fermat precheck, and no case used the QR/255255 or wheel fallback.

This secondary analysis asks the stronger, missing question: is the **routing logic itself** faster than directly starting with the same optimized standard rho method?

## Independently controlled secondary procedure

[Secondary protocol committed before implementation](DARK_STAR_N28_ROUTER_VS_STANDALONE_BRENT_SECONDARY_PROTOCOL.md), specifying the exact same public method and fixed source: standalone control calls the **same** `brent_attempt` implementation and **same frozen** c1/seed2 256 modular-squaring budget plus c3/seed3 128 modular-squaring budget, preceded by equivalent 2/3/5/7 public divisibility and followed by the **same complete wheel210 fallback**; it omits the router's eight extra Fermat probes and its unused conditional PTP QR branch. No use of hidden factors or orders, no re-selection, budget increases, or rewritten historical results. The remaining comparison arms are the exact original router source and standalone wheel210, with **eight interleaved rotated timing repetitions** for all sixteen original public N.

- [Full secondary audit source](../integrations/darkstar_hybrid/darkstar_n28_router_vs_brent_secondary.py)
- [Successful, independent CPU workflow **40893476655**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40893476655)
- [Machine-readable sixteen-case original secondary receipt with all raw timings](../results/dark_star_unified/darkstar_n28_posthoc_router_vs_brent_control.json)
- Original public input SHA256 `9f8cd1d83b3bcfdfce9c41ceda05621b52c9e9076d7cdc2dec36bc24598b7a51` and frozen router source Git blob `4420a5d5d83869ccc41ab2396cde15d84f98a4c1` verified unchanged.

## Verifiable findings

| Metric | Secondary result |
|---|---:|
| Same original 28-bit N cases analyzed | **16** |
| Complete correct factors via original router | **16/16** |
| Complete correct factors via standalone exact-budget Brent control | **16/16** |
| Standalone Brent factors found before complete wheel fallback | **16/16** |
| Original router faster than standalone Brent on the same N | **1/16** |
| Precommitted secondary gate | At least **9/16** router wins |
| **Incremental advantage of routing over Brent alone** | **FAILED** |
| Median of per-case router / standalone Brent elapsed time ratios | **1.071603** (router ~7.16% slower) |
| Real QPU jobs | **0** |

The secondary audit demonstrates that, on this finite and easy synthetic 28-bit population, **simply placing deterministic Brent rho first is faster than the added public method selection overhead in almost every case**. The router's original positive result against wheel210 and PTP/LFK was real for those specified Python implementations, but its main mechanism was **using a standard stronger classical factoring algorithm**, not a demonstrated novel periodic-prime-table pruning or adaptive selector advantage. The additional eight Fermat squares pay overhead on the fifteen cases Brent would solve quickly, and the PTP QR branch was never exercised.

## Scientific boundaries and next defensible experiment

This is a single original input population tested twice, so it is NOT a new independent replication. Eight submillisecond Python timing repeats on GitHub are noisy, and the small semiprime construction is favorable to rho; no asymptotic claim or performance guarantee for larger primes, balanced cryptographic semiprimes, or native quantum circuits is justified. The supplementary negative control does **not** retroactively erase or reinterpret the original wheel/LFK primary PASS—it clarifies its mechanism.

**Next rigorous direction:** freeze a genuinely new original cohort with a broader range of factor separations/bit lengths, plus a separately fixed public predictor of *whether QR midpoint filtering is worth paying for*; compare a policy against a STRONG optimized Brent/Pollard rho baseline from the start, as well as wheel210 and PTP/LFK, with per-N setup and whole-algorithm work included. The important open research question is whether PTP-based public structural information can identify even one reproducible stratum in which its additional overhead beats modern general-purpose classical factorization—not whether it beats ordinary trial division on tiny numbers. No QPU until there is a justified circuit-resource experiment.
