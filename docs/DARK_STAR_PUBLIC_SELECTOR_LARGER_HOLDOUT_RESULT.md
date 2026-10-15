# VERIFIED: 18-bit Dark Star public selector with Pollard p−1 and explicit continued-fraction factor extraction

**Date:** October 14, 2026 Pacific (GitHub CI October 15 UTC). **Research lead and original direction:** Chase Lunsford / CaMaLabs. AI-assisted preregistration, implementation, independent numerical review and result preservation.

**Scope:** 120 newly selected *small 18-bit* semiprimes; ZERO QPU submissions. Ideal nearest-bin QPE and the repository's generic scalable logical CCX model, **not a device measurement, true hardware speedup, fault-tolerant cost or practical factoring advantage**.

## Historical wins retained and why this experiment differs

The previous [three selected successful scouts](DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_RESULT.md) showed 43%–69% lower expected logical CCX through earlier ideal-QPE stopping, and separate phase recycling lowered peak logical width. The first [preregistered 96-semiprime, 17-bit population](DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md) showed ell3 trigger 20.10% vs control 13.09% CCX saving; ell5 trigger 9.35% vs control 15.52% (**failed original enrichment**); ell7 trigger 2.88% vs control 1.64% (weak) when both groups were transformed and only validation-eligible rows were considered. Per-round modular arithmetic was slightly **more** expensive after transformation. Do not present scouts as population averages or conflate wide-to-recycled width savings with Dark Star work savings.

**New question is DIFFERENT, not a rerun of the old endpoint:** can a frozen decision using only **public N,ell,a** choose transform vs **no transform**, outperform the unchanged base among still-classically-unresolved cases, and actually produce nontrivial factors through explicit public continued-fraction denominator/power/GCD checks? Samples, range, classical guardrail, CF success definition and cost denominator are different, so comparing the percentages between studies as if they were like-for-like is invalid.

## Frozen study, provenance and full receipts

- [Preregistered BEFORE data](DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_PREREG.md) commit **`2264ada02e22488c04a18475ef5512d8fdedfc85`**.
- [Implementation](../hardware/dark_star_public_selector_larger_holdout.py), commit `b9df891fd21b376edec8213564223c28702adc8a` (two pre-run selftest corrections: `2c90b4fcb8ca680e70ad0d18d534959787ba3e70`, `043b5973249905e1622387ec760939c904192dac`; NO data/selector modifications after results).
- [Three-way independent GitHub Actions CI 38664537058](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664537058) **SUCCESS** (3/3 jobs, all 120 selected rows, selftests, committed frozen salt and base rule, explicit factor-producing CF and public-oracle guardrails).
- [Receipt-preservation GitHub Actions CI 38664867576](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664867576) **SUCCESS**. Independently downloaded artifacts from the original verified run, validated all denominators, zero-QPU flags, full sample count and public selector decisions, and **committed the exact three JSON receipts unchanged** in commit **`e2381628365606dbf4e90023b9034bb26d6f58c9`**.
- Immutable full data: [ell3 JSON](../results/dark_star_ptp/dark_star_public_selector_n18_ell3.json), [ell5 JSON](../results/dark_star_ptp/dark_star_public_selector_n18_ell5.json), [ell7 JSON](../results/dark_star_ptp/dark_star_public_selector_n18_ell7.json). I additionally inspected all three ZIP artifacts and parsed each JSON row; repository copies were compared to CI summaries. No row dropped. Factors/orders labeled **validation-only**.

Frozen semiprimes p≠q prime, p,q>=11, `131072<=N<=262143`; ell=3,5,7; 20 trigger (`N mod ell !=1`) +20 control (`N mod ell==1`) per ell = **120 distinct ell-labelled selections** (not necessarily unique N across different ell panels). Public SHA256-ranked selection salt `QRR-public-selector-population-v2-20261014`, public base pool (2,3,5,7,11,13,17,19,23,29,31) and independent hash salt. Frozen policy: **plain = a**, **unconditional = a^ell mod N**, **public selector = transformed on trigger, otherwise unchanged** (also unchanged if base happens to equal its transform). No validation order/factor information enters sample/base/policy decision.

Before ANY modeled quantum processing, all policies share an identical bounded **public classical filter**: baseline GCD, power-of-two/GCD chain, Pollard stage-one p−1 from base2 with prime powers up to B=31. A successful proper public factor terminates the row with **no QPU work**. An additional b-specific shortcut is a *diagnostic only*, not silently used to cherry-pick quantizable rows. Primitive modular arithmetic counts are stored, but **classical CPU operations and quantum CCX have not been combined into a single wall-clock/energy/physical cost**.

For unresolved cases, nearest-bin-only ideal eigenphase probabilities are generated from validation multiplicative orders, but sampled continued-fraction denominator candidates d are accepted **only** when public pow(base,d,N)==1, d even, and at least one of gcd(base^(d/2)−1,N), gcd(base^(d/2)+1,N) yields a proper nontrivial factor. This replaces the previous convenient validation-order-divisibility success shortcut; factors/orders are never consulted inside the acceptance verdict. Four ideal shots per precision stage, stages 4,6,…,36 bits. This still omits all nonnearest phase outcomes and real noise; it is NOT an exact full QPE distribution simulation.

## Classical preprocessing: the major result

| ell | Trigger classically factored /20 | Control classically factored /20 | Total remaining /40 |
|---:|---:|---:|---:|
| 3 | 11 | 15 | **14** |
| 5 | 13 | 13 | **14** |
| 7 | 19 | 14 | **7** |
| **All** | **43/60** | **42/60** | **35/120** |

**85/120 = 70.83% were already factored classically**, before any quantum arithmetic. Among classical wins, the bounded stage-one Pollard p−1 B31 dominates; across all six groups, power-of-two/GCD found 10 and Pollard B31 found 75 as the first reported proper factor (GCD coprime-base selection produced 0 first-factor finds). The residual comparison cohort is *small* and highly selected by this public preprocessing; no practical cost advantage follows from a simulator ratio.

## PRIMARY TRIGGER comparisons — strict factor-producing expected cost per successful session

For rows with both plain and public-selector success probability >0, compute each policy's **expected logical CCX per successful factor-producing staged session with independent restarts**, then report the ratio of sums (selector/plain). `1-ratio` is the modeled relative CCX saving. Rows whose success probability is zero in either policy are **retained and disclosed separately**, not silently treated as successes. Public selector uses no oracle.

| ell | Classically unresolved trigger /20 | Both success-positive | Selector vs plain CCX-per-success ratio | Improve / tie / worsen | Frozen trigger criterion |
|---:|---:|---:|---:|---:|---|
| **3** | 9 | 8 (1 not jointly factor-capable) | **0.769280** (**23.07% less**) | **7 / 0 / 1** | **PASS**, small cohort |
| **5** | 7 | 7 | **0.790726** (**20.93% less**) | **4 / 0 / 3** | **PASS**, marginal majority |
| **7** | 1 | 1 | **1.029531** (**2.95% MORE**) | **0 / 0 / 1** | **FAIL** |

`ell=3`: among nine classically unresolved trigger keys, unchanged base is model factor-capable for 8 and selector for 8; seven of the eight comparable cases improve and one worsens. The one worse case has no order reduction (ell3 order 20726->20726), while the seven improving cases reduce their orders. Expected arithmetic CCX per *attempted* session summed across all nine rows changes by ratio **0.837195** (16.28% lower), but that differs from the 0.769280 successful-session endpoint because success probability and averaging differ.

`ell=5`: among seven unresolved triggers, all seven have model factor success probability >0 under both policies. Four improve and **three worsen**, even though aggregate successful-session CCX ratio **0.790726** passes the prespecified bare-majority criterion. Thus the positive aggregate finding is fragile. Those three worsening cases have unchanged validation order; the four positive cases reduce order. Attempted-session cost ratio **0.797288**. The earlier ell5 trigger-enrichment FAIL remains valid: its panel, denominator, conditioning and comparator differ, and must NOT be erased or described as a replication.

`ell=7`: only **one** of twenty trigger rows escapes bounded classical factoring. Its transform leaves validation order 89142 unchanged and increases its modeled CCX by **2.95%**, so preregistered selector benefit **FAILS**. There is effectively no useful population inference with one surviving row.

### Control strata and unconditional-transform diagnostic

In every control row `N mod ell==1`, the **frozen public selector intentionally chooses the unchanged base**. Therefore its modeled cost equals plain **by construction** (no selector changes in any control). This is an implementation control, **not independent evidence that the transform has no value on control residues**. In the same archived receipts, unconditional transform can still reduce multiplicative order and arithmetic work on some controls. The residue-only gate discards those opportunities, so it is NOT established as an optimal public selector.

Control remaining / classically factored: ell3 5/15, ell5 7/13, ell7 6/14. Both-success comparable counts: ell3 4, ell5 4, ell7 5; public selector versus plain: all ties. Plain positive factor-producing success coverage among control remaining: 4/5, 4/7, 5/6 respectively. Among trigger remaining, coverage plain and selector: **8/9, 7/7, 1/1**; no decrease in coverage from the selector in this small panel.

All 120 rows passed odd-power order identity checks `ord_N(a^ell)=ord_N(a)/gcd(ord_N(a),ell)`. These are exact validation equalities, **not a newly proven theorem**. No attempts to simplify work using hidden order/factors occurred.

## Recycled width: independent mechanism

All N are **18-bit**. The modeled generic clean-ancilla arithmetic workspace is **57** simultaneous logical qubits, fixed for wide/recycled and independent of Dark Star. With textbook 36-bit phase cap, wide peak **93**, recycled peak **58** (**35/93 = 37.63% fewer simultaneous logical qubits**). This is **recycling's** width benefit, not the odd-power selector's benefit. No hardware physical-qubit, coherent error or surface-code costs were evaluated.

## Honest interpretation and next gate

**Preserved success:** This is a fully public, locked residue-based choice and a stronger small-semiprime nearest-bin factor-producing-CF resource model. Under its preregistered conditional trigger metric, ell3 passes with 7/8 improved and ell5 passes weakly with 4/7 improved; ell7 fails outright. Compared with the earlier order-only shortcut, the CF acceptance now really verifies `a^d=1` and emits nontrivial public factors. The classical bound removed 85/120 toy instances before any QPE work.

**Not shown:** strong population-level statistical evidence, guaranteed improvement from N mod ell, dominance over unconditional transforming, advantage over stronger public classical factoring, total practical runtime/energy gains, actual IBM QPU speed or fidelity, fault-tolerant scaling, a new Shor theorem or practical RSA factoring. Indeed the selector is deliberately unchanged on control N where unconditional transformation sometimes helps.

**Next discriminating experiment:** first compare a **larger classically-unresolved population** without choosing modulus or bases based on order/outcomes, preferably at larger factor sizes or explicitly balancing public classical-survivor strata. Enforce a stronger public classical baseline and record its operations. Then test an *oracle-free public* decision between no-transform and several exponent choices under **fresh independent** evaluation, including unconditional and random-choice policies, avoiding learned selection on this locked holdout. Expand beyond nearest-bin-only to exact full phase-outcome distribution for a small independently selected set, and compare model CCX, factor yield and wall-clock/classical preprocessing separately. Preserve failed ell7 and prior failed ell5 findings.
