# DARK STAR N24 FULL-OUTCOME QPE FOLLOW-UP — protocol frozen before scoring

Research program: Chase Lunsford / CaMaLabs. October 25, 2026.
**Zero QPU / zero IBM Quantum Runtime / no tokens / no paid submissions.** All computations CPU-only in public GitHub Actions.

## Scientific status and scope
This is **NOT an independent blind holdout**. The 16 public N/a pairs were already preregistered and frozen in
`results/dark_star_ptp/dark_star_n24_public_predictor_manifest.json` (canonical selected-row SHA256
`d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889`).
Their orders and standard half-order witnesses were previously published in
`DARK_STAR_N24_PUBLIC_PREDICTOR_RESULT.md`. That necessary-condition predictor test
FAILED: N%3=1 and N%3=2 each had 2/8 useful threefold-shrinking+witness cases.
The existing 16 are now a **reused exploratory model cohort**; this run measures
**actual bounded ideal-QPE logical CCX per factor-producing staged session** and may
not be described as a new holdout, predictor validation, QPU experiment, or factoring speedup.

No N/base resampling, no post-hoc eligible-only replacement, no change to original manifest,
no alteration of earlier favorable or unfavorable receipts.

## Frozen comparisons
For EACH of all 16 N, public a, group and public features, score:
1. Unchanged a.
2. Cubic base b=a^3 mod N.
3. Predetermined public P1 policy: cube if N mod 3==1, otherwise unchanged.
4. Predetermined public P2 policy: cube only if 8-step public bit-density proxy B(N,b)<B(N,a); otherwise unchanged.
Always-cube is the **primary policy comparator**; unchanged is the secondary baseline.

The P1 and P2 votes are copied exactly from the previously frozen PUBLIC manifest,
**never retrained or tuned** using prior labels, factors, order, outcome or this run.
Comparison of policies reuses paired same-N QPE scores; there is no extra quantum experiment
for each policy. For every case retain classical outcomes, both factor capacities,
model cost-per-success intervals or explicit undefined values, selector decisions and
policy-vs-always-cube intervals. No division by zero and no selection on model outcomes.

**Exploratory preregistered decision gate** for each fixed selector versus always-cube:
on its cases where it chooses *plain* rather than cube, require
(i) at least 75% of those switched rows to be robust bounded improvements (ratio upper<1),
(ii) zero robust bounded regressions (ratio lower>1),
(iii) no loss of model factor-capable coverage over all 16,
(iv) nonempty switched cohort. Classify remaining rows as inconclusive or factor-incapable,
not wins. Also publish unconditional cube-vs-plain complete-population results.
Because this population was already analyzed for order/witness, even a gate PASS is
**hypothesis generation, not an independent scientific confirmation**.

## Mathematics, scoring, uncertainty and controls
- Preserve public B31 screen as already frozen; independently confirm each N/base and
  public-B31 survivor status. The additional original public B47 / bounded Floyd rho /
  trial division factors all 16; record factor/CPU ledger. If verification fails, fail job.
- Public continued-fraction (CF) factor-producing denominator enumeration and explicit
  modular exponentiation/GCD precede hidden-order-based ideal-QPE simulation. Ledger its
  classical operations and any factor already found by classical certificate search.
  This is an evaluation aid with potentially **expensive classical factor recovery**,
  not a free quantum subroutine.
- Validate p*q=N, lambda(N), r(a), r(b), order minimality, b-order=r/gcd(r,3),
  and identity of even-order half-power proper-factor witnesses. Validation order r
  may determine **simulated ideal-QPE phase probabilities only**, never public selection,
  CF acceptance or stopping conditions.
- Use the previously audited `dark_star_n22_numerical_precision_audit.py`
  `prec.score_base` unchanged, extending its stage list to m=4,6,...,48
  (23 stages). Four hypothetical shots per stage. Exact FFT all-outcome at m<=18;
  for m>18 compute 65 centered outcome bins per uniform eigenphase, plus analytical
  omitted-tail upper bound <=1/63.
- 131072 seeded pseudorandom uniform phase draws for orders >131072; otherwise
  exhaustive eigenphases. Use shared public N/stage random stream for plain/cube,
  same historical source sampling salt `QRR-n22-precision-audit-iid-20261015`.
  Record probabilistic **empirical Bernstein** head and omitted-tail intervals.
  Stage-wise family: 16 cases × 2 bases × 23 stages × 2 quantities × 2 sides = **2944**;
  alpha_total=.01, delta=.01/2944. Interpret as nominal simultaneous 99% under
  IID sampling, NOT formally directed-rounding numerical certification.
- Retain original 65-bin, m<=18 FFT, 131072-draw, public certificate, clean-ancilla
  polynomial logical CCX modeling assumptions. The additional phase stage m=48 is
  the only intentional change from the 23-bit protocol, plus family error budget.
- Aborts/timeouts are ERROR, not favorable nulls. No result may be merged unless all
  16 original shard receipts are complete and SHA-validated. Preserve original receipt
  for every row plus the merged summary. Original failed shards remain failed.
- Hardware feasibility, native CZ/depth/fidelity, physical qubit routing and actual
  quantum runtime are **NOT** measured. The tiny semiprimes are classically easy:
  modeled circuit savings cannot imply practical factoring advantage or RSA attacks.

## Reproducibility / execution
Two phase-gates on GitHub main: commit THIS protocol before uploading scoring code,
then commit a CPU-only workflow with a 16-shard matrix and a strict independent merge.
No IBM client SDK, secrets or remote QPU access. After run, archive all positive,
negative, inconclusive, undefined and classical prefilter outcomes unchanged.
