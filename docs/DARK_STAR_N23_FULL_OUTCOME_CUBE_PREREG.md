# PREREGISTRATION — first fresh 23-bit full-outcome Dark Star cube-vs-plain holdout

**Research lead/original direction:** Chase Lunsford / CaMaLabs. **Freeze date:** October 20, 2026 Pacific. Committed BEFORE generating new public N selections, validation orders, phase samples, model CCX outcomes. Zero real IBM QPU jobs or Runtime. Preserve old n17–22 wins and negatives unmodified.

## Primary question and realistic counterfactual

Does cubic public-base preconditioning `b=a^3 mod N` exhibit reliable improvement in the repository's generic clean-ancilla **ideal-QPE modeled logical CCX per successful factor-producing staged session** when we move to a completely NEW **23-bit semiprime interval**, holding a genuine public classical-factoring pipeline accountable? This is NOT a speedup versus classical factoring, an algorithmic theorem, hardware speed/fidelity or RSA cryptanalysis.

Previous 22bit high-precision full-outcome holdout (eight independent selected public N) found three/four trigger conditional wins and one factor-incapable, but **all 25 screened were classically factored** and 4/8 selected cases were factor-incapable. A new 23-bit interval is therefore a fresh modulus-size falsification, NOT a replication of the same N. Existing N35 static-gate sign-selector CPU native-compiler wins remain separate from this ideal-QPE order experiment.

## Frozen public population and classical-first selection

- Synthetic squarefree **distinct-prime semiprimes** `p<q`, `p,q>=11`; **2^22<=N<2^23**, all 23-bit. Prime factors allowed **ONLY** in constructing synthetic N frame and later after manifest commit for validation orders, never in selection, public factor verdict or public policy.
- Split using public N modulo 3, **trigger N%3==2**, **control N%3==1**. Public candidate N ranked SHA256 integer `QRR-N23-FULLOUTCOME-V1-POP-20261020|group|N`, tie N. Choose first coprime a from rotated public pool `(2,3,5,7,11,13,17,19,23,29,31)`, rotation SHA256 `QRR-N23-FULLOUTCOME-V1-BASE-20261020|group|N`.
- Public common first-line B31: gcd(a,N), x±1 GCD + squaring up to `2*bitlength(N)+2`, then Pollard p−1 stage1 base2 B31, as in `hardware/dark_star_public_multichoice_survivor_holdout.py`. Keep the first **FOUR** public-classical-B31 survivors for EACH group, **8 distinct N total**, with ALL ranked public screens/counters/classical sources retained; scanning cap 700 per group; fail rather than resample on shortfall. Freeze SHA256 over canonical public-only selected rows in GitHub main BEFORE any order/QPE scoring. No private r-based or observed-success replacement; eight selected includes factor-incapable cases.
- Extra public classical baseline on ALL survivors, BEFORE hypothetical quantum scoring: Pollard p−1 base2 B47; fixed Floyd rho `x²+1` seeds (2,3), 64 iterations each; public trial-prime ≤97; complete prime trial to √N if still unresolved. Record exact first source, valid factor, operation/CPU ledgers. This is cheap at 23-bit and expected to factor all; if it does, say there is zero practical quantum workload. Separately log public factor-producing denominator certificate enumeration CPU/modular arithmetic; its computations CAN reveal factors.
- Compare **plain a** and **cube b=a³ mod N** only. Both fixed by public a,N and independent of p/q/r. Public CF acceptance enumerates ordinary continued-fraction convergent denominator d with `1<d<=N`, EVEN, `pow(base,d,N)==1`, and a proper nontrivial gcd(base^(d/2)±1,N). Public certificate precomputation uses only modular arithmetic and GCD on N,a, not validation prime factors or hidden order.

## Frozen ideal QPE full-outcome-head method and uncertainty

Carry forward same N22 validated high-precision mathematical method, no posthoc estimator choice:

- m=4,6,...,46 (now **22 stages** for 23-bit modulus), **four ideal shots/stage**. At m≤18 exact entire uniform-eigenphase **FFT** output histogram and full public CF mask. At m>18 evaluate all **65 centered outcomes**, j=-32...32 around nearest y for each eigenphase; omitted QPE output probability ≤1/63 per eigenphase, with measured missed-head probability (not blindly maximum) upper bracket. This is full-outcome *interval*, NOT a complete exact all-y histogram at high m.
- Validation eigenphase order r<=131072: exhaustively enumerate all s=0..r−1; r>131072: **131072** independent nominal uniform eigenphase draws per (N,m), SHA256 seed salt unchanged `QRR-n22-precision-audit-iid-20261015`, shared uniform u between plain/cube. Sampling pseudorandom CPython Random not a formal independence/randomness certificate.
- Two-sided empirical Bernstein bounds for the bounded random accepted head H and omitted tail T, `eps=sqrt(2*sampleVariance*log(2/delta)/n) + 7 log(2/delta)/(3(n−1))`. Family budget **8 N ×2 bases×22 stages×2 H/T quantities×2 tails = 1408**, `delta=0.01/1408`, a nominal simultaneous **99%** statistical guarantee under IID sampling assumptions; no formal directed floating-point arithmetic. Exact phase enumeration uses no phase-sample penalty, but floating errors remain.
- Strict model stop success interval `[1-∏(1-L_m)^4,1-∏(1-U_m)^4]`; expected CCX per attempted staged session via monotone stage probability envelopes; cost per successful factor-producing hypothetical independent restart = `CCX / success`; compare cube/plain ratio `[cubeLow/plainHigh,cubeHigh/plainLow]`; cost if zero success undefined, not a favorable zero.
- Publish every stage bound, factor certificate count, validation-only order, exact factor witnesses, all sampler commitments and public classical ledgers. Never compare generic logical CCX to CPU time as equivalent physical costs; never claim quantum hardware speedup.

## PREDECLARED pass/fail across ALL four fresh trigger cases

Trigger primary gate PASS only if ALL: (i) **>=3/4** both-factor-capable selected trigger cases; (ii) cube public factor-production coverage not lower than plain among 4; (iii) **>=3/4 trigger cases have entire per-success CCX ratio upper bound <1**, not merely mean less than1. Otherwise FAIL; no new N or W adjustment. Control panel includes all four, may be positive, negative or factor-incapable; no post hoc conditioning/pooling. Report all eight, not only informative cases. Strict factor extraction and exact order identity assertions must pass.

Independent 23bit arithmetic width: expected generic coherent workspace **72** logical qubits (work23+acc24+flag1+scratch24); wide peak **118** (phase46), recycled peak **73** (one phase), 45 fewer logical qubits (38.14%), independent of cube. These are NOT physical qubits, FT overhead, or experimental QPU fidelity.

## Execution and stop rules

Two-phase GitHub CI: manifest-only public B31 selection FIRST and commit to main; then 8 individually sharded **zero-QPU CPU-only** scoring jobs with fixed NumPy/Numba pins (previous audited 2.2.6/0.61.2). Fail on absent manifest, changed SHA, wrong public base or group, factor witness/order identity, wrong number of rows, non-normalized probabilities, unbounded tails, timeout, missing shard or any IBM/QPU client submission. Preserve original unmodified 8 JSON receipts and independent total verifier in main. Each scoring shard CPU ≤35 minutes, no method fallback or public N substitutions. No QPU credential or paid IBM runtime; hardware gate remains CLOSED. Do not overwrite historic result.
