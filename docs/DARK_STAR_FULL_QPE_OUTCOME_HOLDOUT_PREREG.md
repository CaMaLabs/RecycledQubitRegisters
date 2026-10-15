# PREREGISTRATION — Complete ideal QPE outcomes vs nearest-bin Dark Star cube

**Freeze 2026-10-14 Pacific BEFORE new selected-N outcomes, new script execution, or CI.**
**Research lead / original questions:** Chase Lunsford (CaMaLabs); AI-assisted implementation and critical controlled validation. **Zero QPU jobs.**

## Preserve prior research, including failure

- Recycled phase register's reduction in simultaneous logical width is validated independently of Dark Star. At 18bit generic clean-ancilla arithmetic: 93 conventional-wide vs58 iterative phase recycled (37.63%) in a resource model, no physical-QPU advantage proven.
- Three chosen Dark Star scouts: 43–69% lower *nearest-bin ideal stage model* logical CCX through earlier stopping; original broader n17 population: ell3 directional positive, ell5 trigger enrichment FAIL, ell7 very weak. Resource per phase round is slightly MORE expensive for transformed base; shorter ideal stopping—not cheaper multipliers—explains wins.
- Later n18 heldouts under a B31 public classical filter: 85/120 classical factorizations, leaving 35 modeled. The preregistered fresh 40 B31-survivor multiexponent holdout (CI 38667303027) screened 200 Ns, 160 factored classically. Locked trigger cube/unchanged modeled CCX-per-success ratio 0.77638 (8/9 comparable pairs improve), but `ladder` == `always3` on all 20 selected trigger instances and locked control 3/7 improve, 4/7 worsen. **A multi-exponent selector advantage was NOT established.** Old ell5 fail unchanged.
- Crucial weakness: every above QPE estimator scored **nearest phase outcome bin only** for each validation eigenphase, not the full phase measurement distribution.

## Fresh tiny-N population with computationally exhaustive outcome support

Choose a computationally tractable but completely new 10bit population: squarefree N=pq with **512<=N<=1023, distinct primes p<q and p,q>=11**. Group by only public N modulo3 (trigger if N%3!=1, control if N%3==1; exclude N divisible by3). **TWO deterministic independent cohorts** `replication` and `locked_holdout`; exactly **THREE semiprimes per cohort×group**, 12 distinct Ns total. Rank the full group from eligible 10bit Ns by SHA256 integer of frozen salt + cohort + group + N, then select first three, and for locked_holdout exclude the *selected replication Ns* before ranking. Selection must NOT use order, factorization success, QPE performance, classical-survivor status or private factor sizes. Do not sample until the favorable instances are found. Fixed salted public first-coprime a from rotated pool `(2,3,5,7,11,13,17,19,23,29,31)`, salt `QRR-full-QPE-bases-v1-20261014`; selection salt `QRR-full-QPE-outcome-holdout-v1-20261014`. All 12 selected Ns stay in the denominator even if classically factored.

This tiny 10bit range is chosen to make **all Q=2^m outcomes at up to m=20 phase bits** explicitly enumerable. It is deliberately a precision-model falsification NOT a statistical or RSA-scale inference; small groups may contain no classically unresolved keys and that outcome is itself a result. Fixed exponents `plain=a`, `cube=a^3 mod N`. No new fitted selector.

## Public classical baseline; never hide easy factoring

For each selected N,a run: initial public gcd(a,N), existing bounded repeated-squaring GCD chain at cap 2×bitlength(N)+2, then Pollard p-1 base2 stage1 with fixed **B=7**, in order and stop at first factor; count executed gcd/modular squarings/modular powers. The reason for B7 on tiny N is to avoid silently removing nearly every case, while still using a predeclared public classic factor baseline. Separately on EACH selected N independently run **public Pollard p-1 B31 and B47 diagnostics**, without using their outcomes to select, remove or relabel cases in the frozen B7 analysis. These stronger classical controls may show this entire toy quantum simulation is operationally redundant; disclose that prominently. Do not convert classical operation counts to CCX or claim practical combined runtime savings.

## Exact full QPE measurement probability, not nearest-bin/truncated

For a uniform mixture over the r eigenphases s/r, measure an m-bit QPE register Q=2^m. Standard ideal probability is
`P_r,m(y) = (1/r) sum_(s=0)^(r-1) |(1/Q) sum_(k=0)^(Q-1) exp(2πi k(s/r-y/Q))|²`.
Compute the **exact all-Q-bin probability distribution (up to float roundoff)** by FFT of a cyclic lag autocorrelation: for k=0,…,Q−1, define
`C[k] = ((Q-k)*I(k mod r=0) + k*I((Q-k) mod r=0))/Q²`, with k=0 second term zero.
Then `P(y)=Re(FFT(C))[y]`; numerical negatives must be less than 1e-11, clamp only floating noise and assert `abs(sum(P)-1)<1e-9` BEFORE any clamping/renormalization. No sampling, no peak-window approximation, and no missing tail probability. Validate against direct matrix geometric-sum formula for small Q and r in selftests. Work cap Q=2^20 (1,048,576), n10 cap m=20. This method is O(Q log Q), no exponential-in-order full state simulation.

For each y, success predicate uses **ONLY PUBLIC N,a,y,m**: enumerate ordinary CF convergent denominators d of y/Q, restrict 1<d<=N and d even, verify pow(base,d,N)==1, and accept only if gcd(base^(d//2) ±1,N) returns actual nontrivial divisor. Speed up by precomputing the public set of d passing these public pow/GCD conditions and checking whether the CF sequence intersects that set; assert this matches the existing slow public CF factor predicate on exhaustive small selftests and additional fixed validation bins. Validation p,q and true order r are used **ONLY** to generate the ideal eigenphase distribution after N,a and classical processing have been selected. The CF acceptance remains independent of p,q,r.

The matched nearest-bin estimator MUST be the **existing frozen** `hardware/dark_star_public_selector_larger_holdout.py:true_factor_producing_probability`, or an independently cross-checked exact clone: sum only the single nearest y to each s/r weighted by its actual ideal probability; all other outcome probability is omitted, never renormalized. This enables a paired full-versus-earlier-estimator check.

Model staged policy: m=4,6,…,20, four attempted shots per stage, public factors verified at each shot, expected stage executions via survival weighting, generic reversible modular arithmetic and recycled phase-register logical CCX as in `dark_star_recycled_scalable_arithmetic_audit.py`. Report expected CCX/attempt, model factoring success by cap, and CCX per successful session with independent restarts (undefined when success=0) for both base choices and both probability modes. QPE full vs nearest share EXACT same arithmetic cost and stop policy; only probability changes.

## Primary endpoints and decision

Primary locked holdout = all six N irrespective of classical status; (1) disclose classical factor counts and whether anything remains at B7/B31/B47; (2) for classically unresolved and *both mode-policy success-positive* rows compare cube/plain CCX-per-success ratios in full-outcome and nearest-bin models (aggregation of paired successful sessions, plus per-row improve/tie/worsen). (3) Each individual full-outcome success probability must be >= the corresponding nearest-bin probability within tolerance (the latter counts a subset of disjoint bins); report failure as algorithmic bug. (4) Quantify whether the cube advantage gets larger, smaller, disappears or reverses with full outcomes; exact paired within-case differences, no cherry-picking. (5) A positive finding requires both a nonempty comparable holdout and a majority of strictly improved rows under full outcomes with no reduction in factoring-success coverage; otherwise report inconclusive/fail even if weighted ratio <1.

Replication is a separate control; do not pool to produce a success. A stronger public-classical baseline factoring all N trumps any practical quantum-value claim. Keep independent phase recycling logical width result separate.

**Computational gate:** if the 2^20-bin CF enumeration exceeds CI budget, do NOT reduce the phase cap, exclude cases or approximate the distribution posthoc; fail/censor and document. CI matrix 4 jobs × cohort and trigger/control, each 20-minute timeout; pinned NumPy, zero QPU. Archive all selected original rows, classical outcomes, exact probability normalization checks and per-stage metrics; preserve wins and negatives after validation.

**Claim boundary:** tiny 10bit synthetic semiprime ideal model; no real QPU, experimental runtime, physical error/fault tolerance, asymptotic Shor improvement, strong population inference, practical RSA factorization or user-originated discovery of a new order theorem.
