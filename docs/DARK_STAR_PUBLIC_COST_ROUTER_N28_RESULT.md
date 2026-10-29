# Dark Star: fresh N28 public classical cost router — preregistered primary holdout

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-29. **Primary preregistered classical speed gate: PASS** against the repository's Python wheel210 and PTP/LFK implementations on **16 fresh 28-bit synthetic semiprimes**. This is a positive **classical method-ordering** result, not an improvement in factoring complexity, not a novel PTP factor sieve result, not native quantum computation. **ZERO IBM QPU, zero paid or free IBM Runtime.**

## Chronology: policy and public population frozen before scoring

1. [Predeclared cost-routing policy and full benchmark criteria](DARK_STAR_PUBLIC_COST_ROUTER_N28_PREREG.md) committed before public population selection. [Fixed public-only router source](../integrations/darkstar_hybrid/darkstar_public_cost_router.py), SHA of its Git blob `4420a5d5d83869ccc41ab2396cde15d84f98a4c1` (never modified during original science).
2. [Separate original 16-row public-N selection](../results/dark_star_unified/darkstar_public_router_n28_frozen_manifest.json), SHA256 **`9f8cd1d83b3bcfdfce9c41ceda05621b52c9e9076d7cdc2dec36bc24598b7a51`**, 8 Nmod3=1 and 8 Nmod3=2, deterministically SHA-picked from **562,219** public N28 candidate semiprimes constructed with synthetic primes. No truth p/q, true order, classical method result, or cost was present in selection. [Public freeze workflow 40892476026 — SUCCESS](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40892476026) saved the inputs on main before any scoring.
3. [Scoring implementation](../integrations/darkstar_hybrid/darkstar_public_cost_router_n28_holdout.py), [standalone structural tests](../integrations/darkstar_hybrid/test_darkstar_public_cost_router.py), [original independent GitHub Actions run **40892932977 — SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40892932977) checked the hash and fixed source, tested correctness, factored all 16, ran **eight interleaved full-method timing repeats** per input (not post-hoc picking the fastest), validated every true synthetic factor *after* timing all public methods, and archived the full unmodified [original 16-case JSON with ALL per-case raw timings/operation counts](../results/dark_star_unified/darkstar_public_router_n28_original_16_holdout.json).

## Fixed router actually tested (not selected by secret factor information)

- Public small wheel prime checks `2,3,5,7` and eight exact early Fermat midpoints;
- budgeted deterministic **Brent's Pollard rho** batched-GCD, public `(c=1,y=2,max256 squarings)` followed on failure by `(c=3,y=3,max128 squarings)`, at most 384 modular squarings total;
- if still unresolved, **conditional restored M255255 PTP quadratic-residue midpoint sieve**, only when `4*(ceil(sqrt N)^2-N)<=ceil(sqrt N)`, at most 128 positions and 8 exact square-root tests;
- complete conventional wheel-210 factor search as **fully priced fallback**. No hidden factors, known multiplicative order, or QPU input.

## Primary outcome — original, prospectively selected 28-bit cases

| Metric / predeclared comparison | Verified result |
|---|---:|
| N28 cases factored by public router | **16/16** |
| Complete conventional wheel210 correct factors | 16/16 |
| Complete PTP LFK/kernel correct factors | 16/16 |
| **Router median latency faster than wheel210 on the same N** | **16/16** |
| **Router median latency faster than standalone PTP LFK on the same N** | **13/16** |
| Router faster than the previous fixed full classical preflight | 12/16 |
| Preregistered pass criterion | At least 9/16 faster than **each** of wheel210 and PTP/LFK |
| **Original primary classical runtime gate** | **PASS** |
| Median of casewise router/wheel210 elapsed-time ratios | **0.31544** (~3.17× speed ratio) |
| Median of casewise router/PTP-LFK elapsed-time ratios | **0.35504** (~2.82× speed ratio) |
| Cases factored via Brent Pollard rho | **15/16** |
| Cases factored via first eight Fermat midpoints | **1/16** |
| Cases needing PTP M255255 midpoint branch | **0/16** |
| Cases needing final wheel210 fallback | **0/16** |
| Real IBM QPU jobs | **0** |

The one early-Fermat result was **N=204,445,411**. **No case exercised the late PTP-sieve or complete-wheel fallback**, so their predeclared safety and theoretical validity are tested separately, not empirically demonstrated by this new cohort's outcomes. Their code remains in the router for future populations.

## What this result **does and does not** establish

The result establishes a clean *falsifiable win* against the two **specified conventional Python repository baselines** on a fresh publicly SHA-frozen set. It materially reduces wasted time in the former long fixed classical preflight, in which expensive PTP residue-table setup and multiple unsuccessful stages could be paid before getting to a standard fast factoring algorithm.

**It does NOT establish a new factorization algorithm or speedup from PTP mathematics.** The main winner on 15/16 inputs is standard **Brent-style Pollard rho**. The prior wheel210 and PTP/LFK routines are not state-of-the-art general integer factorization competitors. An optimized standalone **Brent rho control was NOT included in the preregistered primary comparators**; therefore this cohort cannot show that the *router's decision policy itself* is superior to simply running standalone rho first. More optimized compiled factoring libraries, larger semiprimes, different prime distributions, and a separate new original holdout may invalidate the latency ratios.

All timings are noisy, tiny-microsecond-scale Python wall times, eight rotated method invocations on a shared GitHub Actions runner. The result is **not** a statistically certified implementation-independent 3× speedup, and it does not establish an asymptotic or cryptographic factoring advantage. Do not convert classical wall time into source quantum CCX or claim this is a quantum-performance result. The original and restored PTP pruning remains mathematically valid and previously demonstrated substantial square-root-work reductions in other contexts; **nothing in this N28 cohort isolated a new PTP gain**.

### Next independent secondary audit, only after preserving this original result

A fair *mechanism-level* follow-up should explicitly compare original router to (a) the exact SAME deterministic Brent rho budget with complete wheel fallback but without early-Fermat, (b) a standalone Pollard rho implementation, and (c) pure wheel210/old PTP results. Use the SAME sixteen original cases strictly as **post-hoc controls** without reclassifying the preregistered primary PASS, include actual setup/timing, and preserve nulls/losses. A future entirely new preregistered N29 or larger cohort is needed to validate any learned router tuning. No paid or real QPU.
