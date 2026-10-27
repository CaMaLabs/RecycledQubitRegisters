# VERIFIED CONDITIONAL TARGET — Dark Star N25 order-reducing cases: all three cost MORE source CCX over frozen fixed 96-shot workload; success gain still unmeasured

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-27. The study is a **second-order, post-hoc deterministic cost accounting** of the ORIGINAL eight SHA-frozen N25 candidate cases, not an independent cohort, not a success-probability or QPE rescoring, and **not quantum hardware execution**. Zero IBM QPU jobs, zero free/Open or paid quantum Runtime.

## Research history and exact limitations

The [original SHA-frozen N25 online-CF plus structural arithmetic experiment](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_RESULT.md) had **0 preregistered bounded wins, 0 preregistered bounded losses, 6 statistically inconclusive and 2 undefined**; seven of eight were also classically factored by the subsequent capped B47/rho64 budget. Its complete original eight-row JSON, per-stage arithmetic records, all original numerical intervals and SHA cohort are immutable. The next [exact-order same-order invariance](DARK_STAR_N25_EXACT_ORDER_DOMINANCE_RESULT.md) and [96-shot source-CCX prefix cost theorem](DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_RESULT.md) established an exact negative for **three factor-capable same-order N25 cases** (cube cumulative cost strictly higher at every possible attempted-session stopping point under a shared ideal outcome coupling), plus **two factor-incapable fixed-base cases** across the full original eight. These negative results are honest model-limited information, NOT native gate counts, QPU fidelity or practical cryptographic speed.

The **three unresolved factor-capable cases all have order reduced threefold by cubing**. Their ideal phase distributions and the public verifier's stopping-time distribution need not match. Therefore the previous exact same-stopping-time coupling cannot be used to claim that their cost per factor improves or worsens purely from structural CCX inequalities. We must measure or certify their **success probabilities** separately, with metered public classical computation, and ideally a fresh independently frozen cohort.

## Preregistration and one fixed cost break-even calculation

[Protocol `DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_PROTOCOL.md`](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_PROTOCOL.md), **pre-scoring commit `6026440498f130ca471894f1d538904f560bc392`**, froze all eight existing N25 rows, original SHA manifest `66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7`, and **exact original source gate costs for all 24 staged phase widths m=4,6,...50**, four shots per width, 96 possible fixed workload prefixes. The public test compares cube `a³ mod N` to same original a, while retaining exact original validation-only multiplicative order and factor-capability flags only as audit metadata. No fresh QPE outcome sampling, post-hoc selection, private factor implementation, noise model or QPU connection.

The [reproducible script](../hardware/dark_star_n25_changed_order_break_even.py) computes exact `fractions.Fraction` ratios for each stage and all 96 fixed-prefix workloads and independently cross-checks each prefix by *a separate stage-weighted cumulative arithmetic construction*. It audits original prior exact-order and same-order shot-prefix receipts, includes every one of eight cases and rejects original SHA, row or success-status changes. For a standalone, fixed phase width m with independently repeated attempts, source CCX expected cost per success is `CCX(m)/p(m)`; **if both success probabilities are positive**, the cube is cheaper only if `p_cube(m)/p_plain(m) > CCX_cube(m)/CCX_plain(m)`. The right side is an **exact conditional break-even ratio**, not the observed left side. Costs for classical online CF/pow/GCD verification are specifically EXCLUDED. For the full 96-shot **fixed workload** ratio the same aggregate condition is hypothetical only; different orders invalidate any claim that its ratio is the true cost per success in an adaptive early-stopping session.

## The THREE factor-capable changed-order cases

| Original public semiprime N | Base a | Exact validation-only order plain→cube | Cube cheaper source stage widths | Cube/plain CCX full fixed 96-shot workload | Scientific interpretation |
|---:|---:|---|---|---:|---|
| 20,508,127 | 3 | 854,124→284,708 | 0/24 | **1.013153236** | 1.3153% more fixed arithmetic CCX |
| 24,467,873 | 3 | 12,228,930→4,076,310 | 0/24 | **1.011131720** | 1.1132% more fixed arithmetic CCX |
| 28,064,303 | 13 | 1,753,308→584,436 | **2/24** (m=42,44 only) | **1.007470338** | 0.7470% more fixed arithmetic CCX |

All three have **96/96 positive cumulative fixed-workload cube-minus-plain source CCX differences**, despite two individually cheaper high-precision source-stage costs for the third. These are conditional *workload cost ratios*, NOT proofs that cube's expected **cost per successful factor** is worse: a modest improvement in the measured or exact public online-CF/GCD success rate could offset the extra arithmetic in a particular fixed-width experiment. The exact stage-specific break-even thresholds for **every m** are archived, not just the 96-shot total.

**Correct conditional interpretation:** At m=50, per-shot cube/plain structural CCX ratios are ~**1.009986816**, **1.005259732** and **1.002877020**, respectively. For a fixed repeated-trial experiment at that SAME width (with no differing public verifier overhead), cube would need `p_cube/p_plain` greater than those respective ratios to reduce expected source-CCX per successful factor. We have **NOT measured or established** those success-probability ratios in this new audit.

## All eight original N25 cases, no censorship

In addition to the 3 changed-order factor-capable cases:
- The fourth changed-order N=29,256,449/a5 is exact **factor-incapable for both arms** under this frozen even-order verifier; it can have finite arithmetic costs but **undefined per-success cost**. Cube is cheaper at 5 of 24 individual stages; nevertheless the 96-shot fixed cumulative cube/plain ratio is **1.002480051**, and no factoring opportunity follows.
- Three factor-capable same-order controls N=20,088,463/a29, N=28,811,323/a31, and N=32,295,103/a17 reproduce existing immutable 96-prefix exact minimum cost ratios **1.009067859, 1.005361763 and 1.008498493**, respectively. Their exact ideal outcome coupling and source-CCX negatives were proved in the earlier experiment, NOT re-established as fresh independent cohort observations here.
- The remaining N=28,787,333/a11 same-order case has the same fixed 96-shot ratio **1.013660527**, but **both arms are factor-incapable**, so its per-success cost is undefined.

The resulting 8/8 categories are **3 changed-order factor-capable break-even-only, 1 changed-order factor-incapable/undefined, and 4 same-order controls** (three factor-capable and one incapable). The original primary 0/0/6/2 statistical classification stays unchanged.

## Provenance: original CI science, independent exact receipt preservation

[**Original CPU-only proof and independent within-run cross-check GitHub Actions 40467868224**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40467868224) **SUCCESS**. The original source job processed all 8 original public cases, checked all 24 stage ratio fractions and 96 fixed-cost prefixes per case, and its separate CI checker recomputed all cost ratios independently from the untouched original JSON. No Qiskit native ISA work or quantum device methods.

[**Independent original-artifact audit + preservation GitHub Actions 40468006478**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40468006478) **SUCCESS**. It downloaded the original source-run JSON artifact WITHOUT rerunning any science, validated the original SHA and all 8 row identities, exact rational numerator/denominator of each of 768 prefixes, 24 original stage costs per row, original prereg summary, precise published three-factor-capable target ratios and all zero-QPU flags, and committed the **unchanged original JSON bytes** as:

[`results/dark_star_ptp/dark_star_n25_changed_order_break_even.json`](../results/dark_star_ptp/dark_star_n25_changed_order_break_even.json).

The source and prerequisites remain immutable; all existing N35 compiled arithmetic and actual N15 IBM Open Plan recycling accomplishments are separately preserved. This analysis cannot be used to claim a real quantum cubing benefit, an RSA/ML-KEM attack, physical QPU factoring or a theorem about all composite integers.

## Next independent research gate

Choose a **fresh publicly frozen population of N/a** (without conditioning selection on validation-only multiplicative orders) after serious B47/rho64 and transparently metered classical-first screening, then use an efficient publicly on-demand CF/GCD verifier with phase-pairing controls to measure or sharply bound **actual conditional factor-success probability ratios at selected m**, keeping source arithmetic and public verifier CPU costs separate. Include both same-order null controls and order-reducing cases when later revealed only for analysis. Do not reclassify the original N25 population or promote its post-hoc cost break-even arithmetic into a quantum advantage claim. No IBM physical device submission without independent feasibility, explicit authorization and live active Open Plan verification.
