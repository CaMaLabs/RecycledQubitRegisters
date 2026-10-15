# Preregistration — Dark Star 20-bit public-policy classical-survivor holdout v3

**Frozen before selecting hidden orders, QPE probability estimates or CCX outcomes:** 2026-10-14 (Pacific).
**Research lead:** Chase Lunsford / CaMaLabs. QRR zero-QPU classical/quantum resource modeling; no IBM service calls.

## Reason for this step

Prior n17 and n18 scouts, preregistered holdouts, 120-row public-selector and 40-survivor multi-exponent controls remain intact. In particular: ell=5 trigger enrichment repeatedly failed, ell=7 generally failed, and simple multi-exponent ladder did not improve on always-cube in previous trigger survivors. A stronger classical first-line sometimes removed 70–80% of 18-bit samples. The next target is a larger disjoint modulus range with **publicly selected classical-unsolved cases**, no hidden-order case selection, explicit factor-producing continued fractions, and upfront numerical uncertainty for high order.

## Frozen population and public selection (before quantum resources)

- Distinct-prime squarefree semiprimes `p<q`, `p,q>=11`, **524288<=N<=1048575** (20 bits). Private factor metadata are used to form a synthetic semiprime population *only*, not to choose the public policy or survival filter.
- Six panels in fixed order ell=(3,5,7), group=(trigger,control). Trigger N%ell !=1 and N%ell !=0; control N%ell==1. Both panels may have order divisible by ell.
- From all eligible synthetic semiprime N, sort by SHA256 of `QRR-n20-public-policy-survivors-v3-20261014|ell|group|N` ascending, tie by N.
- Public a is first coprime in cyclic fixed pool `(2,3,5,7,11,13,17,19,23,29,31)` rotated by SHA256 `QRR-n20-public-base-v3-20261014|ell|group|N`.
- Apply only the frozen public common classical cascade (below) in ranked order. Retain the first **12 classically unresolved N per panel**, and retain *every screened* N, result/source/counters, even when factored. Stop scan by first 12 survivors or **400 screened N per panel**, whichever comes first; failure to reach 12 is an incomplete result, not license to resample. Exclude previously selected N in earlier panels within this run to keep 72 unique N; publish exact manifest + SHA256 before quantum scoring. No post hoc factor-/order-based eligibility filter.
- Every panel gets exactly 12 survivors, total **72 unique public-classical survivors** if completed; total screened N reported separately, not conflated with survivors.

## Bounded public classical preprocessing

Use **identical N,a-dependent filter** for all compared policies: gcd(a,N); public power-of-two/GCD chain up to `2*bitlength(N)+2` squares with x±1 GCD; then Pollard p−1 **stage one from base2, B=31**, sequential prime powers <=31, with gcd(x−1,N). Stop on first proper public factor, record actual GCD/modular squarings/modular pow calls and factor/source. The model is intentionally bounded, not a complete classical factoring baseline.

As independent public diagnostic only, apply Pollard p−1 with B47 on the 72 survivors; do not retroactively drop them or replace B31 with B47. Include extra public transform costs as a separate ledger rather than mixing modular CPU operation counts numerically with logical CCX.

## Frozen public policies; all compare on same surviving N,a

For each public N and a construct 4 candidates: original a (exponent=0), a³, a⁵, a⁷ mod N. Exponent labels are selection metadata; no hidden order is used for the choice.
- `plain`: exponent 0.
- `always3`: exponent 3.
- `cube_trigger`: 3 iff N%3==2 else 0.
- `ladder`: first ell in 3→5→7 with N%ell not in {0,1}, else 0.
- `cheap4`: choose minimum public generic **four-phase-bit arithmetic CCX proxy** among 0,3,5,7, tie in that same ascending order. No oracle or full-session outcome enters the proxy.

The ladder previously failed to beat always3 on relevant trigger cases; v3 tests the same frozen choice rather than tuning it. Public policy comparison must include **ladder vs always3**, not just ladder vs plain, and must include **success coverage**. Never call the validation-only hindsight-minimum 'public'.

## Ideal-QPE scoring: frozen sampling approximation, NOT exact

The prior 18-bit experiments exhaustively looped through r possible validation eigenphase numerators for each phase-precision stage. That is expensive for 20-bit orders. **Before observing v3 data**, freeze the following finite-sampling estimator:

- phase-stage precision `m=4,6,...,40` (textbook 2×20-bit cap), 4 nearest-bin-only ideal-QPE shots/stage and the existing polynomial controlled reversible modular-add/multiply CCX counter;
- for each (public N, stage m), draw **4096 common seeded uniform random u in [0,1)**, using CPython `random.Random(int.from_bytes(SHA256('QRR-n20-phase-v3-20261014|N|m'),'big'))`. For each candidate hidden validation order r, phase numerator `s=floor(u*r)`, use the existing exact analytic nearest-bin probability for that s/r, weighted as `I(public factor-producing CF succeeds at nearest bin)*P(nearest bin | s/r)`. For **r<=4096**, instead enumerate all r numerators exactly. The same u stream is reused across all candidate bases at given N,m to reduce paired simulation noise. No Monte Carlo quantum measurements or IBM QPU access occurs.
- The **factor-producing CF verdict** for a proposed m-bit y uses public N,a only: enumerate continued-fraction denominators d from y/2^m, require 1<d<=N, d even, pow(a,d,N)==1 and gcd(a^(d/2) ±1,N) returns proper factor. Validation-only p,q,r never enter this verdict. Cache verdict by (N,base,m,y); no hidden order shortcut.
- Record per-stage simulated success p, number of phase numerators, and whether r was exhaustively enumerated. The bounded 4096-sample estimate is **not** an all-bin QPE distribution or exact r-mixture. Its Hoeffding 95% per-stage bound (worst-case, independent uniform draws) is `sqrt(log(40)/(2*4096))≈0.02122`; report it, plus observed sampling uncertainty, not artificial significant digits. If a policy-level conclusion depends on a ratio near parity, label uncertain.
- Compare factor-production probability, expected CCX per *attempted staged session*, and CCX/success-by-cap assuming independent restarts; 0-success entries have infinite/undefined cost per successful session. Do not discard them from selected denominator or coverage.

## Frozen primary comparison and falsification

For each panel (ell, trigger/control), preserve all **12 public classical survivors**, successful/unsuccessful factor-capable rows. Compare each policy against plain and ladder against always3:
1. factor-success coverage (positive p) over all 12, including losses;
2. both-positive comparable denominator and improve/tie/worsen counts for CCX **per successful session**, not just per attempt;
3. aggregate ratio sum(candidate CCX/success) / sum(comparator CCX/success) on paired both-positive cases only;
4. all-12 average success, per-attempt CCX ratio, phase rounds ratio, coarse classical ledger, and explicit noncomparable rows;
5. fixed seed deterministic bootstrap (2000 replicates, seed 202610142038 + panel and policy) 95% CI for paired aggregate successful-session ratio when >=2 comparable cases.

Primary gate for `ladder` as a **general public selector**: success coverage no lower than plain in **each** panel, paired aggregate successful-session CCX below plain and **strict majority** improvements in **each** relevant trigger panel, and outperform **always3** on at least one panel with positive paired improvement and no higher aggregate cost on other trigger panels. If any fail, report the broad selector claim as failed. Prior ell5/ell7 negative results remain part of the narrative. An ell3-specific positive finding is separate from the broad selector gate.

Do not pool unlike ell groups into a headline population gain or reselect favorable survivors using true orders. Bootstrap/model sampling uncertainty must not be ignored; claimed improvement requires robust direction under uncertainty.

## Independent recycling-width and hard safety

20-bit generic clean-ancilla coherent arithmetic workspace: work=20, accumulator=21, flag=1, clean scratch=21 => **63** arithmetic logical qubits. Wide cap 40 phase: **103** peak logical qubits; iterative recycled phase: **64** peak, 39 saved (37.86% reduction). Independent from any odd-power transform and from measured hardware performance.

No QPU, no Qiskit Runtime imports, no Sampler/Estimator, no IBM credential use, no paid billing permission. The experiment measures **in-silico ideal nearest-bin simulated QPE and polynomial logical CCX** only. It is not noise/fidelity, full-bin hardware performance, asymptotic Shor change or RSA-2048 attack. Full preregistration/manifest must be durable before result is scored; allow no silent scoring-method changes after observing data.
