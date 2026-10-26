# N25 Dark Star deterministic same-order structural audit — frozen plan

Research lead: Chase Lunsford / CaMaLabs. 2026-10-25. **This is a post-hoc mechanistic analysis of already published N25 cases, NOT an independently blinded holdout.** All eight original rows must remain included and the original preregistered gate classifications unchanged. Zero IBM QPU jobs and no paid Runtime.

## Exact conditional claim

For any N and coprime public base a, set b = a^3 mod N. If ord_N(b) = ord_N(a) = r (equivalently 3 does not divide r), the ideal QPE outcome probabilities for equal phase-width m are exactly equal under the standard uniform-eigenphase model. For any measured y and any even continued-fraction denominator d, the public modular-order check a^d =1 iff b^d =1. When it is 1, put z = a^(d/2) mod N. Because z*z=1 modulo N, b^(d/2) = z^3 = z modulo N. Consequently the same public CF/GCD factor verifier accepts exactly the same measurements for plain and cube. Coupling phase outcomes proves identical success and stopping times, independent of Monte Carlo errors.

Read archived 24-stage structural CCX counts per arm. If every stage has cube CCX >= plain CCX and first stage strictly larger, all coupled staged attempts consume more source CCX under cubing. If every stage ratio cube/plain >= c>1, then each attempted run has cube/plain source CCX >=c; provided factor success probability is nonzero, the ratio of expected per-factor-success source CCX is >=c. For zero-success cases DO NOT report a defined per-success ratio, only the per-attempt domination. If orders differ or source costs cross, do not certify a negative or positive result.

## Frozen procedure

Source only the eight existing original audited results in results/dark_star_ptp/dark_star_n25_online_model_all_8.json. Verify total eight, original manifest SHA256 66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7, no QPU, 8 distinct moduli, 24 aligned stage counts, exact original order identity r_cube=r_plain/gcd(r_plain,3), nonnegative integer CCX, and source only. For every row compute same-order flag, smallest and largest stage CCX cube/plain ratio, stages cube better/equal/worse, and conditional deterministic verdict; retain previous numerical CI status and public classical filtering status. No post-hoc case suppression.

Provide independent numerical assertion of factor-verifier invariance for each same-order row over >=100 seeded public d values, including even multiples of r and odd/even controls. Also exhaustive checks on small test N for the full CF measurement domain. This numerical validation supplements algebraic proof and is not a 25-bit exhaustive search.

Output machine-readable results/dark_star_ptp/dark_star_n25_exact_order_dominance.json with all original eight. Validate in GitHub Actions with strict test assertions, save receipt, report interpretation, append docs/RESEARCH_LOG.md. Do not relabel original N25 zero bounded wins; this follow-up is a separate deterministic conditional classification in a source-CCX model and is NOT native compiled hardware, a real-QPU run or a cryptanalytic breakthrough.