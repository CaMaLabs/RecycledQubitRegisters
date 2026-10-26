# Dark Star N25: deterministic 96-shot cumulative source-CCX follow-up (passed)

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-25. CPU only, **zero IBM QPU, zero paid Runtime**. **Secondary post-hoc mechanistic analysis of the SAME eight frozen N25 cases; not fresh independent population evidence.** The [original N25 primary report](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_RESULT.md) remains 0 model-bounded wins, 0 model-bounded losses, 6 inconclusive, 2 undefined and unchanged.

[Protocol frozen before the new test](DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_PROTOCOL.md) · [Implementation](../hardware/dark_star_n25_prefix_dominance.py) · [Machine-readable 8-case/96-prefix receipt](../results/dark_star_ptp/dark_star_n25_prefix_dominance.json) · [SUCCESS, GitHub Actions 40271034234](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40271034234)

## Exact stopping-time proof

Previously we proved that when gcd(3,ord_N(a))=1, b=a^3 mod N has the SAME order, hence both have the same ideal uniform eigenphase QPE measurement distribution, and the public continued-fraction and modular-power/GCD verifier accepts exactly the same y values. For any accepted even d, z=a^(d/2) has z^2=1 and (a^3)^(d/2)=z^3=z modulo N. Consequently their **measured factor successes and stopping times admit an exact coupling**.

The existing staged model executes at most four shots for each of m=4,6,...,50: exactly **96 possible stopping-shot positions**. For each possible k in 1..96, sum the actual archived source-stage arithmetic CCX for *each attempted shot through k*, separately for cube and plain. If cumulative C_cube(k)>C_plain(k) for **EVERY** k, then every attempted session (no matter when it stops) is strictly more costly with cube in this structural CCX metric; c=min over k of C_cube(k)/C_plain(k)>1 is a deterministic lower bound on every coupled attempted-session cost ratio and, when factor success probability is positive and equal, on the ratio of expected **source CCX per successful factor**. This is not a statistical CI, native compiled cost, hardware runtime or physical fidelity result.

Unlike the previous stricter stagewise criterion, a single cheaper individual cube stage does **not** necessarily reverse the accumulated cost disadvantage. The 96-prefix criterion was written and committed as a separate protocol before running the new script. All original eight cases are included.

## Complete eight-row results

| N | Base a | Ord(a) -> Ord(a^3) | Existing exact witness capability | 96-prefix cube/plain cumulative CCX lower bound | Deterministic prefix verdict |
|---:|---:|---|---|---:|---|
| 20,508,127 | 3 | 854,124 -> 284,708 | Factor-capable | N/A | Order reduces; distribution differs |
| 20,088,463 | 29 | 2,007,928 -> 2,007,928 | Factor-capable | **1.00906786** | **Exact cube source-CCX regression** |
| 28,811,323 | 31 | 7,200,100 -> 7,200,100 | Factor-capable | **1.00536176** | **Exact cube source-CCX regression** |
| 32,295,103 | 17 | 1,008,860 -> 1,008,860 | Factor-capable | **1.00849849** | **Exact cube source-CCX regression** |
| 24,467,873 | 3 | 12,228,930 -> 4,076,310 | Factor-capable | N/A | Order reduces; distribution differs |
| 29,256,449 | 5 | 114,240 -> 38,080 | **Incapable both bases** | N/A | Order reduces but no fixed-base factor via this verifier |
| 28,064,303 | 13 | 1,753,308 -> 584,436 | Factor-capable | N/A | Order reduces; distribution differs |
| 28,787,333 | 11 | 4,796,098 -> 4,796,098 | **Incapable both bases** | **1.01366053** (attempted-run only) | Per-success ratio undefined; neither arm can factor |

**New deterministic result:** all four same-order rows pass strictly positive cumulative extra cube CCX at **all 96 stopping positions**, i.e. zero nonpositive prefixes; **three factor-capable same-order rows** therefore provably have no cubic source-CCX benefit. The fourth has no factor success route, and its per-factor cost is undefined despite a strict attempted-run structural disadvantage. The row N=28,811,323, previously inconclusive due to 1 cheaper cube stage out of 24, is **now resolved as a source-CCX loss** because that one stage does not outweigh earlier accumulated cost. This is a genuine stronger falsification within a specific model, not a rescored probability claim.

The earlier exact order/witness audit separately proved that **two original N25 rows** (29,256,449 and 28,787,333) were fixed-base factor-incapable in both arms under the specified strict even-order CF/GCD route. Together, this leaves **three factor-capable order-reducing cases** as the unresolved potential Dark Star mechanism cases from the original eight: 20,508,127; 24,467,873; 28,064,303. Positive conditional gains on these have **not** been established. Seven of the eight original cases were found by the deliberately limited subsequent public classical prefilter; the ONLY fixed-filter survivor N=32,295,103 is among the exact cubic source-cost regressions, not a quantum-advantage result.

## Controls / limitations

- The new JSON checks the original SHA manifest, original row order, both matching exact multiplicative orders, 24 aligned model stages, all 96 shot prefixes, valid integer gate counts, and original numerical classifications, and explicitly preserves the older deterministic classifications.
- The original 99% nominal empirical-Bernstein QPE success/cost intervals are **not** overwritten, tightened, or passed by this theorem; the theorem makes a different conditional assertion under exact same-order coupling.
- All results concern ideal phase estimation plus a particular source modular arithmetic **CCX-count** decomposition, not CZ routing, error correction, actual noisy QPU performance or cryptographically significant modulus sizes.
- This is an **exploratory post-hoc secondary analysis**. A new population must be frozen using public N/a/classical-budget information **before** validation-only order is inspected. Selecting fresh cases *because they turn out to have r divisible by 3* would leak oracle information into sample selection.

**Next scientifically meaningful direction:** on new publicly selected semiprimes with stronger and fully metered classical-first screening, focus conditional post-freeze analysis on cases where 3 divides the validation-only order, compare cube against plain with an efficient on-demand verifier, and include the exact same-order null group. No paid Runtime or QPU required.
