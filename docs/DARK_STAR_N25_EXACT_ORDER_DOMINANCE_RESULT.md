# N25 Dark Star exact same-order / source-CCX follow-up: deterministic conditional negatives

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-25. **CPU-only, zero QPU/paid Runtime.** This is an *exploratory, post-hoc mechanistic audit* of the same eight frozen 25-bit cases, **not independent population replication**, and **does not alter** the preregistered primary model outcome (0 bounded wins, 0 bounded losses, 6 inconclusive, 2 undefined).

- [Frozen analysis protocol](DARK_STAR_N25_EXACT_ORDER_DOMINANCE_PROTOCOL.md), commit b425ab6a5d3d9f056da980dfc286f2f3687ea0aa.
- [Analysis implementation](../hardware/dark_star_n25_exact_order_dominance.py), commit 6462dea0ed7a8f3442ab34c14dad4e6167b140d3.
- [Original complete N25 receipt](../results/dark_star_ptp/dark_star_n25_online_model_all_8.json).
- [Eight-row exact audit JSON](../results/dark_star_ptp/dark_star_n25_exact_order_dominance.json).
- [Successful GitHub Actions run 40270627654](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40270627654), all internal checks passed and result committed to main.

## Mathematical invariant (not statistical)

If r=ord_N(a) is not divisible by 3, then ord_N(a^3)=r and the **ideal QPE measurement distribution** is exactly the same for a and a^3 at every phase width (uniform ideal eigenphases). The online public CF verifier considers only even d with base^d=1. As z=a^(d/2) has z^2=1 mod N, (a^3)^(d/2)=z^3=z; hence the gcd(z±1,N) proper-factor outputs are *identical for every possible measured y*. Therefore the ideal two policies can be coupled to have precisely the same successful attempts and stopping times, without Monte Carlo variance.

When the arithmetic CCX source count for every stage is strictly higher for cubed base, each coupled attempted run costs more. Its cost ratio is at least the minimum of the 24 per-stage CCX ratios. This exact **structural model** statement is conditional on the archived modular-arithmetic cost implementation; native transpilation, noise, routing, parallel depth and wall-clock speed are not tested.

Separately, with an exact multiplicative order r, if r is odd or if a^(r/2) is the trivial root +1/-1 mod N, then **no even multiple d of r** can yield a nontrivial GCD factor from this fixed base. This is stronger than the previous conservative numerical zero-*lower*-bound classification, but pertains only to the specified order/GCD factoring route.

## Complete original eight-row secondary audit

| N | a | Order under cubing | 24-stage cubed CCX counts vs plain | Lower bound on coupled attempted-run cube/plain CCX | Exact follow-up verdict |
|---:|---:|---|---|---:|---|
| 20,508,127 | 3 | 854124 -> 284708 | 24 greater, 0 less | Not certified | Order changed; no exact cost verdict |
| 20,088,463 | 29 | 2007928 -> 2007928 | 24 greater, 0 less | **1.0053045** | **Exact strict source-CCX loss for cube** |
| 28,811,323 | 31 | 7200100 -> 7200100 | 23 greater, 1 less | Not certified by stagewise gate | Same order but stage costs cross |
| 32,295,103 | 17 | 1008860 -> 1008860 | 24 greater, 0 less | **1.0027691** | **Exact strict source-CCX loss for cube** |
| 24,467,873 | 3 | 12228930 -> 4076310 | 24 greater, 0 less | Not certified | Order changed; no exact cost verdict |
| 29,256,449 | 5 | 114240 -> 38080 | 19 greater, 5 less | Undefined per-success | **Exactly factor-incapable for both bases** |
| 28,064,303 | 13 | 1753308 -> 584436 | 22 greater, 2 less | Not certified | Order changed; no exact cost verdict |
| 28,787,333 | 11 | 4796098 -> 4796098 | 24 greater, 0 less | Undefined per-success | **Exactly factor-incapable for both bases** |

**Secondary outcome:** 2 deterministic source-CCX worsening cases with potential factoring success; 2 exact fixed-base factor-incapable cases (no finite factor-success cost); 1 same-order stage-cost crossover not certified by stagewise argument; 3 changed-order cases left undecided. Importantly, **N=32,295,103, the only N25 survivor of the deliberately weak additional classical B47/rho64 filter, is among the exact cubic source-cost losses.** That is a limited-budget classical survivor, not a hard cryptographic semiprime.

**Cross-checks:** 20 small-N same-order examples, 13 nontrivial cubes, **6,720 exhaustive CF measurement-output comparisons**, all matched. In each of the four same-order N25 rows, 142 public denominator checks and 176 selected full online-CF measurements independently agreed between plain and cube. For the factor-incapable rows the exact root-of-unity condition and original factor-witness diagnosis agreed.

**Interpretation:** This strengthens the *negative evidence for unconditional cubing* in the archived ideal structural model. It does not negate the universal odd-cube half-order witness identity, nor prove there is no benefit on order-reducing cases. More sampling cannot overturn the exact same-order/no-success identities; further statistical experiments should focus on genuinely order-reducing, factor-capable cases with honest classical cost accounting and fresh selection. This follow-up must not be presented as a new positive result or as physical quantum hardware validation.
