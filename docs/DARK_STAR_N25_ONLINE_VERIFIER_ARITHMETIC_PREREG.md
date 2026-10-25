# PREREGISTERED — N25 independent public-classical survivor + online CF/GCD and structural arithmetic test

Research lead: Chase Lunsford / CaMaLabs. Freeze date: 2026-10-25. IBM QPU / IBM free or paid Runtime: ZERO.
This follows the completed N24 analysis but **reuses none of its moduli**. Both the cubic hypothesis and the earlier simple selectors have had negative holdouts.

## Primary scientific question
On *new* 25-bit semiprimes, does always cube a public base via b=a^3 mod N improve a bounded
ideal phase-estimation **structural reversible-CCX cost per factor-producing attempt** relative
to plain a, when the program uses public **ON-DEMAND continued-fraction denominator verification**
instead of an advance O(N) classical factor-producing-denominator search? Test factor production
and classical-first costs independently. This is not a claim about a compiled/native circuit or quantum speedup.

## Immutable public case selection before ANY order/QPE outcome
- Construct new squarefree N=pq with distinct primes 3500<=p<q<=11000 and 2^24<=N<2^25.
  Construction p/q MUST NOT enter rank, base, policy or public manifest.
- Public groups N mod3==1 and N mod3==2, *four cases per group*, total 8, with NO
  predictive weighting of the groups. SHA salt `QRR-N25-ONLINE-ARITH-POP-20261025`;
  base-rotation salt `QRR-N25-ONLINE-ARITH-BASE-20261025`, base pool
  (2,3,5,7,11,13,17,19,23,29,31).
- Rank public candidate N within each group by SHA256 of `SALT|group|N`, tie N.
  Take first four survivors of exactly the existing public B31 classical_cascade(N,a).
  Max 600 public screening candidates/group or FAIL. Archive **all screens**, including
  classically solved, and exact operation count ledger. Freeze canonical selected 8 public
  N/base/groups and SHA256 in GitHub main in a SEPARATE workflow BEFORE model scoring.
- Do NOT select on actual factor witness, private true multiplicative order, QPE phase
  results, success probability, or compiler cost. No resampling after failure.

## Policies and realistic-cost boundary
- Matched baseline *plain a* and *always cube b=a^3 mod N* on ALL 8 frozen cases.
  The N mod3 split is DESCRIPTIVE and is NOT relabeled a successful selector.
- Count genuine program-structure-controlled modular multiplication components with
  `dark_star_recycled_scalable_arithmetic_audit.stage_arithmetic_count`: CCX,
  controlled-SWAP, CX, and clean-MCX decomposition per stage, using only public powers
  a^(2^k) modN, b^(2^k) modN. Include peak source logical width and note this is
  the existing explicit reversible-arithmetic gate *model*, **not** physical transpilation,
  native CZ, latency or fault-tolerant error correction.
- Stage m=4,6,...,50 inclusive (24 stages), 4 model shots each. For each stage record
  raw structural per-execution CCX and CSWAP for both arms and expected resource-cost
  interval from the stage success intervals and reach probabilities.
- Replace the OLD public O(N) enumeration of all factor-producing denominators. An on-demand
  verifier must first receive a simulated measured integer y, compute CF convergents
  of y/2^m with 1<d<=N, check even d, a^d=1 mod N and GCD(a^(d/2)±1,N).
  No secret p/q/order in online verifier; no precomputation of successful denominators.
  Count candidate denominators checked, modular exponentiations and GCD calls made by
  this ONLINE verifier, separately from both classical prefilter and quantum gates.
- Public additional classical B47 rho64 and small trial<=97 BEFORE hypothetical
  QPE; if a factor is found, mark **classical solved** and quantum-needed=FALSE.
  Complete public trial to sqrt(N) may be a validation-only diagnostic AFTER
  these fixed prefilters but cannot count as an unpriced QPE oracle.
- Validation-only factors/orders are allowed *solely to draw ideal QPE eigenphases*
  after public selection and fixed classical budgets. Verify cubic order identity
  and half-power witness identity independently.

## Predeclared probabilistic mathematical estimator
- For each (N,m), 4096 IID nominal uniform eigenphases per base; fixed Python SHA seed
  `QRR-N25-ONLINE-ARITH-PHASE-20261025|N|m` with paired shared uniform pseudorandom
  streams for the two arms, using Python Random seeded by SHA256.
- Simulate one measured outcome per eigenphase by discrete sampling the QPE sinc-squared
  probabilities of 65 bins at center +/-32. Account for all mass left outside the
  65-bin window with explicit residual; any omitted tail can contribute 0..residual
  success probability. **Never treat omitted probability as automatically unsuccessful
  when constructing upper success bound.** No full-y enumeration at large m.
- Stage bound: empirical Bernstein for head accepted indicator H and omitted-tail
  probability T separately, clipped to [0,1], upper success bound = H+epsilon_H+
  T+epsilon_T; lower = H-epsilon_H, no factor witness -> exact zero only after
  certified exhaustive structural impossibility, otherwise keep statistical zero lower.
  Union family size **8 N * 2 bases * 24 stages * 2 observables * 2 tails = 1536**,
  delta=.01/1536; nominal simultaneous 99% under IID pseudorandom-sampling assumptions,
  no claim of formal directed-rounding certified intervals.
- Expected CCX attempt costs and success intervals follow existing staged 4-shot,
  restart-adjusted cost envelopes; ratio undefined when lower success bound zero.
  Report ALL eight cases: bounded wins (ratio upper<1), losses (ratio lower>1),
  inconclusive, undefined. Do not exclude factor-incapable or classical-solved cases
  to claim population-wide improvement.
- **Primary win gate**: at least 3 of all 8 original rows have bounded cube/plain
  per-success CCX upper<1, no more than one has bounded loss, AND cube usable model
  factor-success coverage (lower>0) is not worse than plain. This is small-sample
  directional evidence only; model sampling intervals may be too wide to pass.
  A separate end-to-end gate requires at least one row not classically solved
  before quantum work; otherwise **practical quantum-work demand=0**, independently
  of CCX modeling.

## Execution controls
Implement pure CPU code, strict on-demand verifier selftests against original
slow public `explicit_cf_proper_factor` on small N and representative m/y;
big-int center calculation (s*Q) in Python prevents 25bit x 50bit overflow.
One GitHub Actions CPU shard per frozen N (8 total), then strict original-artifact
SHA/row verification + aggregate. Fixed finite timeout per shard. Any timed-out
stage fails; no hidden downgrading to another sampler. Store both model and
actual classical-work receipts; zero IBM SDK/secrets/QPU. The preceding N24
16-row positive and negative evidence remains untouched.
