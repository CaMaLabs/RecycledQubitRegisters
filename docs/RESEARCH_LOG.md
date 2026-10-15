# Research Log

This file is the narrative record for the RecycledQubitRegisters project. It is
intended to preserve not just results, but **why each experiment was run, what
assumptions were intentional, and what later tests do or do not invalidate**.

## 2026-10-14 — Preserve optimized-mapping intent

### Context

The project intentionally treats physical-qubit placement as part of the
compiler/architecture strategy. The strict Fez-vs-Nighthawk topology study
searched for compact, favorable connected subgraphs under a hard source-width
cap. That optimized placement was deliberate.

A later unique-placement benchmark was added to sample many distinct connected
placements and measure sensitivity to placement quality.

### Interpretation guardrail

**Do not describe the optimized-placement result as a placement artifact.**

The two experiments answer different questions:

- **Optimized mapping:** What resource cost can the recycled architecture
  achieve when the compiler deliberately searches for a good physical-qubit
  placement? This is the intended engineering strategy.
- **Placement sensitivity:** How much do CZ count and depth change when the same
  architecture is mapped onto other valid connected subgraphs? This measures
  robustness to mapping quality.

If random/unique placements perform worse than the optimized placement, that
does not invalidate the optimized result. It quantifies the value of topology-
aware placement optimization.

The correct reporting format is therefore to keep both:
1. optimized-placement resource results; and
2. unique-placement distribution results.

A useful derived metric is the **mapping-optimization gain**:
optimized result versus median unique-placement result, separately for Fez and
the Nighthawk-style square-lattice proxy.

### Related results already preserved

- `docs/NIGHTHAWK_STRICT_TOPOLOGY_PROXY_RESULT.md` — optimized strict-width
  topology result.
- `docs/NIGHTHAWK_PLACEMENT_ROBUSTNESS_RESULT.md` — placement-distribution
  result and sensitivity interpretation.
- `hardware/ibm_nighthawk_unique_placement_benchmark.py` — current stricter
  unique-placement follow-up.

### Runtime-cost safety

IBM paid runtime is not authorized by default. A credit card being present on
the IBM account is **not** permission to use paid runtime.

Before any real QPU submission:
- positively verify that the resolved IBM instance/plan is free/open;
- if plan or billing status is ambiguous, do not submit;
- prefer zero-QPU compiler/topology work and local/fake backends whenever they
  answer the research question.

The current unique-placement topology benchmark is zero-QPU and can fall back
to local FakeFez plus the public square-lattice proxy.

### Current story

The durable result is the width reduction from recycled phase estimation:
the recycled architecture remains fixed-width while the conventional phase
register grows with precision. Topology-aware placement can materially affect
whether that width advantage also produces CZ/depth savings.

The research question is therefore no longer simply "does recycling beat wide?"
It is:

> Under a realistic topology-aware compiler policy, how much width does
> recycling save, what CZ/depth cost or benefit remains, and how dependent is
> that result on placement quality and hardware connectivity?

Future summaries should preserve that distinction.


## 2026-10-14 — Full repository narrative checkpoint

This checkpoint was written after a full project-wide review of the main branch,
including the hardware history, simulation work, generic full-register path,
qubit-floor/phase-scaling studies, placement and interaction-graph mappers,
Dark Star/PTP experiments, TCT fusion-search integration, LWE_GeometryLab
bridge, current issue tracker, and publication branch.

The purpose is to preserve the causal story of the research so later work does
not flatten separate experiments into one claim or misinterpret a control as a
refutation of an intentional optimization.

### 1. Original QRR question

QRR began from a systems/architecture question, not a claim that a few qubits
can emulate an arbitrary wide coherent register:

> When an algorithm permits measurement, reset, and feed-forward, can temporary
> quantum state be measured into classical state so the physical qubit can be
> reused, reducing simultaneous coherent width?

Iterative/semiclassical phase estimation and qubit recycling are established
prior art. The QRR contribution under study is architecture/compiler/hardware
co-design: when to retain coherence, when to measure/reuse, and how to place the
remaining coherent workload on actual hardware.

The coherent modular-arithmetic work register and its ancillas do not disappear.
Only algorithmically disposable/recoverable phase/control state is recycled.

### 2. Early IBM hardware evidence

The initial IBM Fez dynamic-circuit/QPE experiments established that the
recycled architecture could trade phase-register width for sequential
measurement/reset/feed-forward without simply collapsing the useful signal.

The N=15 matched same-job Shor benchmark then provided a clean phase-width
scaling example. At eight phase bits the wide circuit used 12 logical qubits
and 190 CZ gates while recycled used 5 logical qubits and 68 CZ gates. The
factor-recovery result was 32.03% wide versus 68.16% recycled. This remains a
compiled toy-N=15 hardware result, not a scalable factoring claim.

### 3. N=35 affine compiled-orbit milestone

The next major benchmark was N=35, a=2, whose validation order is r=12.

The first natural-label implementation hit a synthesis-depth wall. An exact
four-qubit affine representation of the twelve-state modular orbit reduced the
controlled-work cost enough to expose the architecture question experimentally.

The six-phase-bit affine run remained near the random-output floor. This was
kept as a negative boundary result rather than hidden.

At eight phase bits, matched IBM Fez hardware produced a reproducible order
signal:

Initial Fez run:
- wide: 12 logical qubits, 331 CZ, strict direct-order 12/512 = 2.34375%;
- recycled: 5 logical qubits, 175 CZ, strict 30/512 = 5.859375%.

Clean replication:
- wide strict: 15/512 = 2.9297%;
- recycled strict: 36/512 = 7.03125%.

The exact uniform-output strict baseline is 2.34375%. Distribution metrics
(Hellinger and TV) also consistently placed recycled much closer to the exact
finite-precision order-12 distribution than wide in those Fez runs.

A later calibration-aware placement search reduced the recycled circuit to
160 CZ / depth 572 and produced 53.71% permissive recovery, 7.03% strict
recovery, Hellinger 0.6441, and TV 0.3947.

This is an important historical win, but it is a **compiled-orbit** result. It
does not remove the need for scalable reversible modular arithmetic.

### 4. Cross-backend control changed the interpretation, not the result

Marrakesh same-job four-circuit A/B controls compared legacy/optimized wide and
recycled circuits in the same calibration windows.

One window favored optimized wide on the strict-order metric; another favored
optimized recycled strongly. Therefore the correct hardware conclusion is:

> architecture × placement × backend/calibration interaction.

QRR does not claim recycled circuits universally outperform wide circuits.
Instead, simultaneous coherent width is one hardware resource whose value
interacts with topology, routing, measurement/reset/feed-forward quality and
calibration.

### 5. Removing the known-orbit construction

A separate line attacked the affine benchmark's largest algorithmic caveat.

Generic reversible arithmetic was first implemented without supplying the
multiplicative order. Correctness passed, but the earliest HLS implementation
cost roughly 428,681 CZ for one controlled modular multiplication. Explicit
arithmetic reduced this to roughly 72,229 CZ but remained impractical.

The project then moved to exact full-register small-N permutation synthesis:

    y < N:  y -> multiplier*y mod N
    y >= N: y -> y

The circuit builder uses public N, a, and a^(2^k) mod N, but no multiplicative
order and no reachable-orbit encoding.

The key direct-transposition identity replaced long Gray-path chains with a
CNOT basis fold, one phase-controlled pattern MCX, and the inverse fold. At
N=35 this reduced the expensive high-control MCX count dramatically and gave:

- 6 phase bits: 10,795 CZ, depth 23,633;
- 8 phase bits: 14,396 CZ, depth 31,084.

Ideal wide/recycled validation passed without supplying r=12 to construction.

This closes the **order/orbit-independence** semantic gate for the small-N
full-register path, but the truth-table/permutation synthesis still scales
exponentially with work-register width. It is not scalable RSA arithmetic.

### 6. Qubit floor and the practical Pareto point

For the exact generic N=35 full-register representation, 35 values require at
least six binary work qubits. Iterative QPE adds one phase/control qubit.

Therefore, under the current representation:

- 7 qubits = architecture-specific hard width floor;
- 8 qubits = practical Pareto knee with one reusable clean scratch qubit.

At eight phase bits the strict 7-qubit path costs about 45,750 CZ and depth
116,470, while the 8-qubit path costs about 14,394 CZ and depth about 31k.

At 64 phase bits, the three-way strict Fez-target comparison was:

- floor7: 7 q, 341,049 CZ, depth 860,530;
- optimum8: 8 q, 110,067 CZ, depth 233,439;
- wide: 71 q, 123,452 CZ, depth 238,581.

Thus the 8-qubit construction saved 63 of 71 simultaneous qubits (88.73%) while
also winning the selected strict compile on CZ and depth. The 7-qubit floor
remains useful as a width extreme, but one clean reusable ancilla is vastly
cheaper in gates/depth.

These are compiler/resource results, not QPU runtime/fidelity results.

### 7. Cross-N/base tests showed what actually controls native cost

The exact full-register architecture was extended to N=21, 35, and 77 and then
to a fixed-32-phase-bit N/base matrix spanning 5-, 6-, and 7-work-qubit cases.

The simultaneous phase-width saving generalized cleanly. At 32 phase bits the
wide-to-recycled reductions were 38->7, 39->8, and 40->9 respectively.

However, CZ/depth behavior did not follow work-register width alone. Changing
public N or a within the same width class changed the result materially. This
identified the post-HLS modular-permutation interaction graph and physical
topology as central variables.

### 8. Placement optimization is intentional methodology

Subgraph ensembles showed that the narrow recycled circuit is much more
placement-sensitive than wide. This is not a reason to discard optimized
placement; it is the reason to optimize placement deliberately.

The project therefore keeps two separate reporting regimes:

1. **optimized mapping** — performance achieved by the intended
   topology-aware compiler/search policy;
2. **placement sensitivity** — the distribution obtained on other valid
   connected placements.

The ensemble median answers "what happens on a typical sampled placement?"
The optimized search answers "what can the intended mapper deliberately find?"

These are different scientific questions.

Best-placement searches at 16/32/64 phase bits found recycled circuits with
lower CZ and depth than searched wide circuits on both Fez heavy-hex and the
square-lattice proxy.

An independent fresh stochastic replication reproduced the best-placement
advantage in all six tested topology/precision cells. At 64 phase bits:

- Fez fresh best R/W CZ = 0.8940, depth = 0.9765;
- square-proxy fresh best R/W CZ = 0.9171, depth = 0.9845;
- width = 71 -> 8.

Median placements were weaker. That is evidence that **mapping quality is part
of the architecture**, not evidence that the optimized result is an artifact.

The current unique-placement run is a stricter sensitivity audit. Its output
must be interpreted in this framework. The useful derived metric after it
finishes is **mapping-optimization gain**: optimized versus median unique
placement, separately for each topology and architecture.

### 9. Interaction-graph mapper became a compiler research result

At N=35 / 32 phase bits, the post-HLS recycled circuit has a dense but highly
nonuniform 8-qubit logical interaction graph. Dominant pressures include the
recycled phase qubit, scratch qubit, and selected work qubits.

The v1 weighted shortest-path score strongly predicted compiled patch quality.
Exhaustive v3 validation on one holdout put the true global optimum inside the
minimum-score bucket on both topologies, reducing the patches requiring
compilation by roughly 83-88%.

Independent replication was deliberately allowed to falsify that stronger rule:
it replicated cleanly on Fez but failed on one square-lattice seed, where the
true optimum appeared around predictor rank 19-20 and was about 5% better in CZ
than the top-ranked patch.

The frozen v4 challenger added a topology-only minimum-diameter bucket to the
screen. Its first fresh-seed preregistered test retained both fixed-layout and
Qiskit-auto optima with zero regret, while reducing compilation count. This is
promising but not yet universal.

The durable mapper result is therefore:

> post-HLS interaction structure is a strong population-level predictor of
> placement quality and can reduce patch-search compilation work, but no
> topology-independent perfect-screen theorem has been established.

Custom in-patch logical mapping and Qiskit auto-layout remain close competitors;
neither is uniformly superior.

### 10. Nighthawk/Phoenix work is a topology proxy

The account has not exposed authenticated Phoenix/Nighthawk metadata during the
current topology experiments. The Nighthawk side is therefore explicitly a
10x12, 120-qubit square-lattice proxy.

The square lattice substantially lowers absolute routing cost for both
architectures. A stronger early hypothesis that it uniquely amplifies the
relative recycling advantage did not survive an 8-patch ensemble.

The safe result is:

- fixed recycled width survives;
- denser connectivity lowers absolute routing burden;
- optimized placement can produce strong recycled results on both topology
  models;
- the present data do not establish a unique Nighthawk-specific advantage.

The current unique-placement benchmark uses local FakeFez plus the labeled
square-lattice proxy when IBM metadata lookup is unavailable. It submits no QPU
jobs.

### 11. Dark Star/PTP evolved from residue filtering into a Shor preconditioner

The PTP work began with modulo-210 residue/kernel-factor structure and was
tested against ordinary wheel baselines.

Real classical result:
- Fermat-midpoint quadratic-residue filtering reduces expensive exact-square
  tests by measured constant factors.

Negative result retained:
- naive residue-symmetry canonicalization can discard the actual fixed-N factor
  pair and therefore cannot simply halve the factor search.

For Shor, raw N mod M categories did not provide a convincing direct QPE-width
shortcut. The useful mechanism emerged from an exact elementary identity:

    ord_N(a^L) = ord_N(a) / gcd(ord_N(a), L).

For odd L, order parity and the standard Shor half-order witness are preserved.

The novel research question is not the identity itself. It is whether **public
residue information can select useful odd exponents before order finding**, and
whether that can reduce adaptive/recycled QPE work after classical shortcuts
are excluded.

For squarefree semiprimes not divisible by 3:

    N mod 3 == 2 -> 3 divides lambda(N).

This does not guarantee 3 divides the selected base's order, but it strongly
enriches that event.

The selector survived independent-N and diverse-public-base holdouts. The later
ell={3,5,7} panel showed that ell=3 gives the strongest deterministic lambda
selector, while ell=5 and ell=7 provide probabilistic but statistically
significant order enrichment.

A separate fresh-range replication for ell=5 and ell=7 also reproduced the
direction with zero theorem violations.

Every quantum-value analysis applies a classical-shortcut guardrail first.
Cases already solved by gcd/repeated-power checks do not count as reduced
quantum burden. This is essential because large smooth odd powers overlap with
Pollard-p-1-style classical preprocessing.

### 12. Adaptive stopping is the link between Dark Star and recycled QPE

A smaller hidden order does not automatically shrink a conventional fixed
textbook phase register. The resource benefit appears when iterative/staged QPE
can:

1. run at a lower precision;
2. measure/recycle the phase qubit;
3. reconstruct a denominator;
4. verify it using only public modular arithmetic;
5. stop if factor-producing verification succeeds;
6. otherwise increase precision.

For N=209, the public cube transform changed validation order 90->30 and reduced
the modeled staged stopping burden. Compiler-weighted replay on Fez-target
circuits reduced paired cumulative native CZ by about 37% and depth by about
38%, while remaining zero-QPU.

Selected post-replication scouts extended this direction:

- N=713, ell=5: validation order 330->66; staged native-CZ reduction about 51%;
- N=781, ell=7: validation order 70->10; staged native-CZ reduction about 74%.

These are selected small-instance compiler-weighted results, not measured
hardware speedups.

The N=713 end-to-end synthetic RSA demo reconstructs the factors, phi, private
exponent, and plaintext from public inputs plus idealized QPE measurements. It
demonstrates end-to-end semantics, not RSA-2048 practicality.

The major remaining engineering boundary is scalable reversible modular
arithmetic. The current exact full-register synthesis produces multi-million-CZ
circuits at N=713/781 and cannot support a meaningful QPU run.

### 13. TCT fusion integration produced both compiler wins and hardware nulls

The TCT integration maps a frozen 320-scenario reduced-order fusion-control
search to Grover-style experiments.

The initial table oracle showed an ideal query-count opportunity but was
classically precomputed, so it could not establish end-to-end quantum value.

A coherent reversible arithmetic implementation of the actual reduced-order
loss formula was exact but extremely expensive: roughly 272k CZ and depth over
one million per Grover round on the logical fully connected probe. This was an
important negative result.

A fixed-instance semantic/ESOP factorization exploited structure in the eight
marked states and reduced one round to 199 CZ / depth 1,013 using 10 qubits,
with six rounds at 1,194 CZ / depth 5,973. This is a strong fixed-instance
compiler result, not a scalable surrogate-evaluation result.

Two Fez QPU pilots failed to demonstrate Grover amplification. The cleaner
11-qubit exact-route pilot used 252 CZ / depth 706 and was verified ideally
before submission, yet hardware produced 9/1024 marked candidate shots versus
22/1024 in the matched uniform baseline. Distribution forensics showed
structured displacement away from the marked subspace rather than simple
uniform depolarization.

The project correctly stopped further QPU spending on this line pending a
substantially different physical implementation.

### 14. LWE_GeometryLab bridge preserved the quantum-value discipline

QRR was also used as a methodological bridge into the LWE_GeometryLab project.

The repo explicitly records that phase-register recycling does **not** directly
compress an arbitrary QAOA candidate register whose search qubits must remain
coherent.

On two newly generated ML-KEM-512 public keys, ideal four-qubit QAOA had a
higher single-sample optimum probability than random sampling, but every tested
tile's public objective was already minimized by the known base candidate
0000. A trivial classical keep-0000 policy therefore had 100% local-optimum
success.

The result was recorded as a negative quantum-value audit rather than a quantum
advantage or ML-KEM break.

The methodological lesson is now part of the wider project: **before allocating
QPU resources, prove that the proposed quantum subproblem is not already solved
by a cheaper public-data classical baseline.**

### 15. Publication state

The main branch contains the original Shor-35 preprint draft and result record.
Draft PR #2 contains a later cross-backend manuscript and Zenodo/PRA publication
package.

Its central framing is consistent with the mature project story:

- no claim of first quantum factorization of 35;
- no claim of universal recycled superiority;
- central hardware result is replicated r=12 recovery for the compiled
  N=35,a=2 problem plus an architecture × placement × backend interaction.

That PR is intentionally still draft/unmerged and predates much of the later
generic-full-register, phase-scaling, mapping, and Dark-Star work. Those later
tracks should not be casually folded into the Shor-35 hardware paper unless the
paper scope is deliberately revised.

### 16. Runtime-cost safety is now a project-level requirement

Historical QPU scripts were written when the account was explicitly configured
for IBM Open Plan. The account now has a credit card attached, and current IBM
instance discovery no longer resolves the old us-east/open filter reliably.

Therefore the project policy is now stricter than the historical scripts:

**No paid IBM Runtime is authorized by default.**

Before any future Sampler/Estimator/QPU submission:
- positively identify the resolved instance and confirm its plan is free/open;
- fail closed if plan/billing status cannot be verified;
- do not interpret a saved credential or attached credit card as permission;
- prefer local fake backends / zero-QPU compilation whenever that answers the
  research question.

A repository-wide hard submission guard should be installed before the next
real-QPU experiment. Until then, no historical hardware runner should be used
for a new submission merely because it can authenticate.

### 17. Current state and next sequence

The current in-progress experiment is the zero-QPU unique-placement sensitivity
audit at 32/48/64 phase bits. It is using 12 genuinely unique connected
placements per architecture/topology and two transpiler seeds, with FakeFez and
the square-lattice proxy when cloud metadata is unavailable.

When it completes:

1. preserve the unique-placement distribution;
2. compare it with the already replicated optimized-placement result;
3. calculate mapping-optimization gain and dispersion;
4. do **not** relabel optimized mapping as an artifact;
5. close the topology line unless a specific unresolved falsification remains.

After that, the highest-value mainline research step is to combine the two
strongest independently developed ideas:

- fixed-width / placement-aware recycled phase estimation; and
- public residue-conditioned odd-power order preconditioning with adaptive
  stopping;

while replacing the small-N truth-table/full-register modular permutation with
a scalable reversible arithmetic construction or, at minimum, a polynomial
resource model whose assumptions are explicit.

That combined study should answer:

> Does the Dark-Star stopping advantage persist when modular arithmetic is
> represented by a scalable construction, and how does the resulting
> width/CZ/depth trade compare between wide and recycled phase estimation under
> the same optimized mapping policy?

This is the next place where the project can move from a collection of strong
small-instance compiler/hardware observations toward a more general resource
argument without overstating current hardware capability.


## 2026-10-14 — Combined Dark Star + recycled scalable-arithmetic milestone

The first combined resource audit now removes the largest remaining modeling
objection from the Dark Star scout results: their earlier IBM-target circuits
used exact small-N full-register truth-table permutation synthesis.

New audit:
- `hardware/dark_star_recycled_scalable_arithmetic_audit.py`
- `docs/DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_AUDIT.md`
- `docs/DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_RESULT.md`

The new model analytically mirrors the repository's generic reusable-clean-
ancilla modular arithmetic. Its gate count grows polynomially with modulus bit
width and does not use the hidden order or a reachable-orbit encoding.

For the three classical-shortcut-clean scout cases, expected staged arithmetic
CCX work changed as follows:

- N=209, ell=3, order 90->30: **43.15% fewer expected CCX**
- N=713, ell=5, order 330->66: **48.76% fewer expected CCX**
- N=781, ell=7, order 70->10: **69.33% fewer expected CCX**

The corresponding ideal staged phase-work reductions were 43.23%, 49.39%, and
69.48%. Dividing the CCX ratio by the phase-round ratio gives 1.0015, 1.0124,
and 1.0050 respectively.

That isolates the robust mechanism: **the general resource saving is earlier
adaptive stopping, not intrinsically cheaper transformed modular constants.**
The same-precision transformed-circuit savings seen in earlier full-register
IBM-target compilations should be treated as implementation-specific secondary
effects.

Under this scalable clean-ancilla arithmetic family, the arithmetic workspace is
27 qubits for N=209 and 33 qubits for N=713/781. At the textbook phase cap,
recycling changes peak logical width:

- N=209: 43 -> 28 (**34.88% reduction**)
- N=713: 53 -> 34 (**35.85% reduction**)
- N=781: 53 -> 34 (**35.85% reduction**)

This is the intended orthogonality result:
- Dark Star reduces expected sequential modular-arithmetic work;
- recycled QPE reduces simultaneous phase-register width;
- the coherent arithmetic workspace remains explicitly present.

This is a successful milestone and should be preserved before broadening the
population. The next falsification should move from the three selected scout
cases to a preregistered held-out semiprime population, reporting the full
distribution of resource ratios rather than only selected positive examples.


## 2026-10-14 — Mapping optimization quantified against unique placements

The unique-placement sensitivity run and the fresh optimized-placement
replication can now be compared directly.

New result:
- `docs/NIGHTHAWK_MAPPING_OPTIMIZATION_GAIN_RESULT.md`
- analyzer: `hardware/analyze_nighthawk_mapping_optimization_gain.py`

The key result is that mapping optimization helps the recycled architecture much
more than the wide architecture.

At 32 phase bits:
- Fez recycled CZ improves 9.88% from unique median to optimized best, versus
  only 1.47% for wide.
- Square-proxy recycled improves 15.13%, versus only 0.88% for wide.

At 64 phase bits:
- Fez recycled improves 7.83%, versus 0.84% for wide.
- Square-proxy recycled improves 18.25%, versus 0.45% for wide.

Using the independently replicated optimized placements, recycled beats wide in
all four overlapping 32/64-bit topology cells:

- 32 Fez: R/W CZ 0.9173, depth 0.9784;
- 32 square proxy: R/W CZ 0.9330, depth 0.9840;
- 64 Fez: R/W CZ 0.8940, depth 0.9765;
- 64 square proxy: R/W CZ 0.9171, depth 0.9845.

The unique-placement medians are intentionally weaker and sometimes reverse the
gate/depth sign. That does not invalidate the optimized result. It quantifies
how much value the intended topology-aware mapper is adding.

This closes the immediate topology-interpretation question. Future reporting
must show both optimized performance and placement sensitivity, but should not
treat arbitrary placement as the deployment policy.

The 48-bit row is intentionally absent from the optimization-gain comparison
because the fresh optimized replication and unique-placement datasets overlap at
32 and 64 bits only. No discovery result was substituted just to fill the table.


## 2026-10-14 — Preregistered 96-semiprime scalable-resource holdout: mixed result preserved

**Milestone:** the frozen Dark Star + polynomial clean-ancilla arithmetic
population audit completed successfully in GitHub Actions with **zero QPU jobs**.
This is the first held-out population after the favorable three-scout audit;
the selection/preregistration preceded the run.

Evidence:
- `docs/DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_PREREG.md`
- `hardware/dark_star_scalable_resource_population_holdout.py`
- `docs/DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md`
- `results/dark_star_ptp/dark_star_scalable_resource_population_holdout.json` — all 96 rows, 51 eligible, full guardrail/exclusion data
- `results/dark_star_ptp/dark_star_recycled_scalable_arithmetic_audit.json` — independently rerun baseline scout receipt
- Actions run: https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38663133662 (passed)

Primary *eligible-row* aggregate expected CCX ratios (transformed/baseline):

| ell | trigger eligible | trigger CCX T/B | control eligible | control CCX T/B | trigger stronger? |
|---:|---:|---:|---:|---:|---|
| 3 | 11/16 | **0.799035** (20.10% saving) | 5/16 | 0.869060 | **yes** |
| 5 | 6/16 | 0.906479 (9.35% saving) | 9/16 | **0.844764** | **no** |
| 7 | 9/16 | 0.971187 (2.88% saving) | 11/16 | 0.983586 | **yes, weakly** |

Improve/tie/worsen outcomes in eligible trigger rows:
- ell=3: **10/0/1**;
- ell=5: **2/0/4** (median row ratio 1.0228);
- ell=7: **3/0/6** (median row ratio 1.0080).

The odd-power order identity and witness-preservation tests had **zero
violations**. The selected scout cases remain true successful mechanism probes,
but their 43–69% savings are **not** population estimates. The ell=5
trigger-enrichment hypothesis **failed** its frozen primary comparison; this is
a useful falsification and must not be concealed. Ell=7 barely satisfies the
aggregate directional comparison but does not yield a broadly favorable row
distribution.

**Mechanism survived:** for ell=3/5/7 trigger, aggregate phase-round ratios were
0.7863/0.8859/0.9603 while CCX-per-executed-phase-round ratios were
1.0161/1.0232/1.0114. Transformed modular constants are slightly **more**
costly per round; positive aggregate effects come from earlier stopping.

**Independent width result:** all held-out N are 17-bit. The explicit
polynomial clean-ancilla arithmetic workspace requires 54 coherent qubits,
so the matched conventional-wide to phase-recycled cap is **88 -> 55 peak
logical qubits** (**37.5% fewer**). This width saving is from recycling, not
from Dark Star. Neither is QPU speedup/fidelity evidence.

The next falsification should enlarge and independently reseed the eligible
population, include a bounded Pollard-p-1-style public classical baseline,
verify factor-producing denominators explicitly, and evaluate the *full public
selection policy*, including a no-transform option. Do not try to rescue
ell=5 by selecting favorable rows post hoc.


## 2026-10-14 — Larger public-selector holdout with factor-producing CF and classical baseline

**Research lead and original idea: Chase Lunsford / CaMaLabs.** Verified the next preregistered Dark Star falsification step, now with no-transform option, a fixed public Pollard stage-one p-1 B31 baseline, factor-producing public continued fractions, a fresh n18 semiprime population, and **zero QPU jobs**. Preserve the previous wins and failures explicitly rather than replacing them.

- Precommitted protocol: `docs/DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_PREREG.md` (`2264ada02e22488c04a18475ef5512d8fdedfc85`).
- Implementation: `hardware/dark_star_public_selector_larger_holdout.py`.
- Verified actual three-way CI: https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664537058 — **3/3 jobs SUCCESS, all 120 selected samples, no violations**.
- Verified receipt preservation CI: https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664867576 — **passed**, all full JSON results committed in `e2381628365606dbf4e90023b9034bb26d6f58c9`.
- Complete receipts: `results/dark_star_ptp/dark_star_public_selector_n18_ell3.json`, `...ell5.json`, `...ell7.json`.
- Interpretive report: `docs/DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_RESULT.md`.

Frozen sample: p≠q semiprimes 131072..262143, prime factors ≥11, exactly 20 public-N hash-selected trigger and 20 control per ell in {3,5,7}; 120 rows; public base pool and new selection/base salts. Three policies: plain a; unconditional a^ell mod N; public selector applies that transform only when N mod ell !=1 and b != a, otherwise **no transform**. No hidden factors/orders used in choosing candidates, bases, transform decisions or classical preprocessing.

**Major classical checkpoint: 85/120 (70.83%) semiprimes factored WITHOUT any QPU processing** using the frozen classical baseline (10 cases first factored by power-of-two/GCD, 75 by bounded Pollard p-1 B31). The quantum-modeled population is only 35 rows after this common public baseline, and subgroup sizes are small.

Primary trigger-only **model CCX per successful factor-producing staged session with restarts** (selector / plain, on cases with positive success in both policies):

| ell | Classical trigger wins /20 | Remaining | Both success-positive | Ratio | Improve / tie / worsen | Frozen criterion |
|---:|---:|---:|---:|---:|---|---|
| 3 | 11 | 9 | 8 | **0.769280** (23.07% less) | **7/0/1** | **pass, small n** |
| 5 | 13 | 7 | 7 | **0.790726** (20.93% less) | **4/0/3** | **pass, fragile** |
| 7 | 19 | 1 | 1 | **1.029531** (2.95% MORE) | **0/0/1** | **FAIL** |

These are **not** actual quantum-device speedups or all-in classical+quantum runtime. The old n17 study had different endpoints/selection: its ell5 trigger-vs-control FAIL still stands; the fresh ell5 positive result here is not apples-to-apples replication. Public selector on control group always leaves the base unchanged, so those controls **tie by policy design**; unconditional transformations sometimes still help those control residues, which this selector would miss. Sign-test evidence is limited: for 7/8 improve/worsen, two-sided exact sign p≈0.0703, for 4/7 p=1, and ell7 n=1 cannot support generalization. No preregistered statistical significance threshold is retroactively invented.

All 120 rows preserve the known odd-power order identity. For each unresolved row, the ideal-QPE simulator enumerates nearest-bin eigenphase probabilities using validation-only orders, but **actual CF success verification** uses only candidate denominator d, `pow(a,d,N)==1`, even d, and public nontrivial GCD factors. The 18-bit generic arithmetic model has workspace 57 qubits and wide/recycled peak 93/58 (**37.63% logical width reduction attributable to phase recycling**, not the transform); none of these are fault-tolerant physical cost measurements.

**Next discriminating gate:** more independent *publicly selected and still classically unresolved* instances (without private-order filtering), stronger fixed classical baseline, new public no-transform vs multi-exponent/conditional selector and random-choice controls, with actual factor-producing denominator checks. Evaluate the full phase distribution on limited fresh controls before asserting an end-to-end Shor benefit. The objective is a genuinely useful public decision rule, not posthoc selection of the successful rows.


## 2026-10-14 — Public multi-exponent survivor holdout, including failed general selector

**Research lead/original geometry and quantum-resource program:** Chase Lunsford / CaMaLabs. Completed next preregistered independent Dark Star zero-QPU experiment, frozen before outcomes. Preceding wins and failures remain in the research log: optimized placement and phase-register recycling, exact order identity, three successful scouts, mixed n17 population (ell5 trigger enrichment FAIL), mixed n18 public/no-transform results (85/120 classically solved, ell3/5 conditional positives, ell7 FAIL). No hardware, physical-qubit cost, asymptotic quantum algorithm improvement or RSA-scale cryptanalytic result is claimed.

Precommit: `docs/DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_PREREG.md` `7d66007e106ef4e4ff84b0f9b50c4af58ffeeacd`. Script: `hardware/dark_star_public_multichoice_survivor_holdout.py`. Trial [CI 38667303027](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667303027) **4/4 SUCCESS**, 40 frozen new classically unresolved 18-bit semiprimes in 4 independent replication/locked holdout × public N%3 trigger/control cells. Receipt preservation [CI 38667614971](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667614971) **SUCCESS**, with all four complete JSON receipts committed at `results/dark_star_ptp/dark_star_public_multichoice_{replication,holdout}_{trigger,control}.json`. Complete verified report: `docs/DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_RESULT.md`.

**Public classical screening:** 200 semiprimes scanned in deterministic SHA256 order (no private information in candidate ranking, base choice, policy selection or classical filtering); **160/200** were factored by bounded classical gcd/power2/Pollard p−1 B31 before quantum modeling. Exactly **40 distinct** classically unresolved public sample Ns were selected, 10 per stratum. A stronger public Pollard B47 diagnostic can factor **another 4/40**. Of 40 retained, only **27** produce a nonzero *nearest-bin ideal quantum factor* success probability under the policies. Remaining zero-success rows retained and denominator clearly disclosed. Distinct semiprime test frame is synthetic; validation p,q are used only to compute ideal eigendistribution order/witness, not to inform proposed selectors.

Five strictly PUBLIC policies compared on identical instances: plain a; unconditional always3 a³; ladder chooses first N-residue-qualified odd exponent among 3,5,7; cheap4 chooses lowest fixed-stage public logical CCX count; SHA random4 chooses a public uniform control. Full successful-session resource comparison uses explicit public factor-producing continued fractions, validation-order-generated ideal nearest-bin QPE, and generic scalable arithmetic. Never silently choose known order or factors.

| Cohort/group | Both success-positive /10 | Ladder / plain modeled CCX-per-success | Improve/tie/worsen | Ladder / always3 | Ladder / random4 |
|---|---:|---:|---|---:|---:|
| replication trigger | 5 | **0.770799** | **5/0/0** | **1.0000** | **0.8068** |
| replication control | 6 | 0.810945 | 3/0/3 | 0.8475 | 0.8666 |
| **locked holdout trigger** | 9 | **0.776382** | **8/0/1** | **1.0000** | **0.8530** |
| **locked holdout control** | 7 | 0.870264 | **3/0/4** | 0.9227 | 0.9371 |

**Primary multi-exponent claimed gain FAILS.** Trigger ladder picked ell3 in all 20 selected trigger Ns across both cohorts, making exactly the SAME choice and cost as the simpler unconditional a³. The **locked control fails** the prespecified majority of paired improvements test (3 improve/4 worse). Thus evidence supports conditional cube reduction in a selected small ideal-model population, **NOT** a useful general public multi-exponent decision rule. On locked trigger, exploratory unadjusted exact paired sign p=0.0390625 (8 improves / 1 worse), **not** corrected for multiple tests or a preregistered significance threshold; replication trigger 5/0 p=0.0625. No broad statistical discovery. Cheap4 selected plain in **39/40** and had no locked-holdout advantage, demonstrating generic cheap modular constants do not predict order savings.

**Independent width calculation** for 18-bit generic clean-ancilla reversible modular arithmetic retains 57 logical coherent workspace qubits, full-wide peak 93, recycled peak 58 (**37.63%** fewer); entirely attributable to iterative phase-register reuse, not the odd-power transform. ZERO QPU jobs submitted.

**Next gate:** stop claiming novelty from the failed multi-exponent ladder. Retain cube in known N-residue trigger as a baseline and test truly full phase-distribution factor-producing classical/quantum model on a fresh smaller benchmark, with stronger public classical baselines and no posthoc selector tuning. Continue to distinguish model resource reduction from actual device runtime/fidelity or practical factoring capability.


## 2026-10-14 — Complete ideal-QPE phase-outcome audit: cube survives tiny cases, no practical quantum value

**Research lead and original direction: Chase Lunsford / CaMaLabs.** Frozen protocol before selected instances: `docs/DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_PREREG.md` at `27a6097a5336205254c1c3d32afbda2a8d528a65`. Implemented complete ideal-QPE phase outcome distribution in `hardware/dark_star_full_qpe_outcome_holdout.py` with *analytically exact* FFT autocorrelation, small-Q direct geometric-sum and public CF/GCD cross-checks. All Q=2^m possible outputs explicitly included through m=20, phase bits 4,6,…,20, no truncation or Monte Carlo. Parent-only true factors/orders generate ideal phase eigenvalue distributions; no private factors/orders allowed to select public N,a or factor-producing y success. ZERO QPU jobs.

Provenance:
- Initial CI [38669418119](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669418119) had a **validator-only variable shadowing bug** (`x['summary']` after `x` had been rebound to a policy), NOT a failure in the scientific model. Fixed only CI validator naming at `78b3a49adc8b4e392b04461663f1eb39f916fc52` with no model/seed/policy changes.
- [Corrected original CI 38669467890](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669467890): **4/4 independent jobs SUCCESS**, all twelve preregistered 10bit Ns, no violations, full measured probability mass and original strict public CF/GCD test passed.
- [Separate JSON receipt preservation CI 38669565271](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669565271): **SUCCESS**, verified and committed original four full JSON outputs at `results/dark_star_ptp/dark_star_full_qpe_{replication,locked_holdout}_{trigger,control}.json`.
- Complete signed-off interpretation: `docs/DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_RESULT.md`.

The 12 new independently frozen public SHA-selected **10bit** semiprimes were NOT conditioned on hidden order, true factors or quantum success; no resampling. Public GCD / power-two / Pollard p−1 B7 factored **8/12** before modeling, leaving **4**. Stronger standalone B31 and B47 diagnostics found **no additional** factor on those four (different p−1 bounds are not monotone because oversmoothing can make gcd=N); elementary trial division to sqrt(N)≤32 trivially factors **all twelve**. Of 4 classically unresolved under artificial B7, **N=533** is modeled factor-*incapable* under both bases and both distribution modes even though order shrinks 30→10. Thus **only THREE** paired factor-producing cases were available.

| Cohort/group | Full all-bin cube/plain modeled CCX per factor-producing success | Previous nearest-bin-only ratio | Classically unresolved /3 | Joint positive factor-producing /3 |
|---|---:|---:|---:|---:|
| Replication trigger | **0.527462** (47.25% fewer) | 0.509030 | 1 | 1 |
| Replication control | not evaluable | not evaluable | 0 | 0 |
| **Locked trigger** | **0.535706** (46.43% fewer) | 0.516915 | 2 | 1 |
| **Locked control** | **0.539765** (46.02% fewer) | 0.548352 | 1 | 1 |

**Positive mechanism milestone preserved:** replacing nearest-bin-only outcome approximation with an exact **all-bin** distribution does **not** reverse the cube cost-saving direction in the three factor-capable tiny instances; it changes the effect size slightly. Every per-stage full distribution was normalized to 1 before any numeric clamping, and its exact proper factor-production chance was >= nearest estimator as expected. Order identities passed.

**Negative critical boundary:** there is **no useful population or practical quantum factoring advantage** here: 8/12 removed by B7, one of the four remaining unable to produce a factor, only one comparable case each in locked trigger and locked control. The preregistered narrow directional criterion of >half improved among comparable rows technically passes 1/1, but this is not a significance or population result. Every N is trivially factored by trial division and no QPU used. The generic 10bit clean-ancilla logical workspace 33, wide peak 53 vs recycled peak **34** (35.85% less) is independent of cube and not a physical-qubit claim.

Prior results and failed controls remain explicitly preserved: 17bit ell5 trigger-enrichment FAILED; 18bit ell7 FAILED; n18 public multiexponent ladder offered **no advantage** over unconditional cube on triggers and FAILED the locked-control majority-improvement criterion. No new theorem, practical RSA break, IBM hardware speedup or fault-tolerant cost evidence.

**Next defensible step**: quantify a mathematically **rigorous outcome-tail error** approximation that can be independently checked against these exact full-QPE results, then test it on fresh larger (17–18bit) public-classically-unresolved N with cumulative B7/B31/B47/trial/Pollard-rho baseline. Do not cite nearest-bin estimates as a complete QPE distribution or spend QPU time yet.


## 2026-10-14 — Public-policy/classical-first v2 holdout completed (mixed/negative result)

A stronger **pre-registered before scoring** and independent held-out population
experiment has now completed. It compared conservative/no-transform,
always-transform, and public-residue trigger-only policies on **144 18-bit
semiprime rows** across ell={3,5,7}, 24 trigger + 24 control per ell.

The new result is preserved in:
- `docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_PREREG.md`
- `hardware/dark_star_public_policy_classical_v2.py`
- `hardware/analyze_dark_star_public_policy_classical_v2.py`
- `docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_RESULT.md`
- `results/dark_star_ptp/dark_star_public_policy_classical_v2.json`
- shard run 38669629155, receipt recovery 38669941950 (successful)

**New classical-first milestone:** bounded public trial/power2/Pollard-p-1 checks
already factor **114/144 = 79.17%** of the small 18-bit cases; only 30 require
further quantum modeling and only 23 meet paired eligibility. This is an
important negative boundary for practical quantum value at the tested size,
not a generalization to RSA-size moduli.

Among paired quantum-eligible rows, modeled aggregate CCX transformed/baseline:

| ell | trigger eligible | trigger CCX T/B | improved/tied/worsened trigger | control eligible | control T/B |
|---:|---:|---:|---|---:|---:|
| 3 | 5 | **0.900389** | **2/0/3** | 5 | 0.939784 |
| 5 | 2 | 0.881745 | 1/0/1 | 5 | **0.819095** |
| 7 | 3 | **1.013418** | **0/0/3** | 3 | 1.008471 |

**Interpretation matters:** ell=3 retains a favorable aggregate direction but
its 2000-bootstrap 95% interval spans 1 (0.7806–1.0124), and 3/5 trigger
cases actually worsen. ell=5 fails trigger-vs-control enrichment once again;
ell=7 worsens all eligible trigger rows. These are too-small conditional samples
to claim a robust deployed performance advantage.

The model now credits early stopping **only after a genuine PUBLIC
factor-producing continued-fraction/GCD witness**. Changed modular constants
are again slightly MORE expensive per executed phase round for every subgroup.
The original scout wins remain valid but must not be treated as a population
resource estimate.

Among all 30 common-classical-unsolved rows, policies relative to
never-transform have modeled CCX ratios: always=0.954642,
trigger-only=0.985584, conservative ell3=0.990161. The JSON records extra
public preprocessing costs and factor success; CCX and classical operations
are not commensurate. Reduced quantum work on a classically solved transformed
row is not itself a quantum speedup.

Independent width receipt: 18-bit clean-ancilla arithmetic retains 57 coherent
qubits; at 36 phase bits wide peak **93** vs recycled **58** (37.63% lower).
The width saving is QPE recycling, **not** the Dark Star transform.

**No QPU jobs were submitted.** Authenticated Phoenix topology, quantum
fidelity/runtime improvement, RSA-2048 performance and altered Shor asymptotics
remain unestablished. Next experiment should move to a larger fresh 20–24-bit
population to avoid the bounded classical-preprocessing saturation seen here,
with a pre-committed public selector and matched success-adjusted costs.


## 2026-10-14 — Analytically bounded full-QPE tails at n17/n18; primary trigger fails, classical rho wins

**Research lead and originating direction: Chase Lunsford / CaMaLabs.** Next preregistered zero-QPU numerical/mathematical falsification completed. Previous positive and negative QRR/Dark Star milestones remain preserved, especially 96-case n17 ell5 trigger-enrichment FAIL, 144-case n18 classical-first v2 ell3 trigger 2 improves/3 worse, ell5 enrichment FAIL, ell7 negative, n18 40-survivor public multi-exponent ladder **no benefit** over unconditional cube on triggers and locked control FAIL, and three tiny n10 full-outcome QPE successes offset by trivially classical factorization.

Evidence:
- Freeze: `docs/DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_PREREG.md` commit **`6093fda1f1e6aba3c9b1081f90cf256a9cb66a6d`**, BEFORE new runs/sample results.
- Script: `hardware/dark_star_tail_bounded_qpe_classical_survivor.py`, commit `1de30c3d4b83ae3cf7342cd885882ffd29c2e7cf`; no post-data code/seed changes.
- Actual four-job experiment **PASS**: https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677647156 (4/4 success), no QPU.
- Independent complete immutable-artifact verification/preservation **PASS**: https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677791142, all eight JSON receipts committed at `results/dark_star_ptp/dark_star_tail_bounded_n{17,18}_{trigger,control}.json`, including ALL publicly screened classical-positive Ns, exact sample order, both bases, all phase stages and complete model uncertainty intervals.
- Full report `docs/DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_RESULT.md`.

FROZEN new sample: SHA-ranked n17 and n18 synthetic prime-pair semiprimes, split by **public N mod 3 trigger/control**, with prior sample Ns excluded by public identifier alone. The first TWO publicly B31-stage1/power2-classically-unresolved Ns per group were retained, **8 distinct selected Ns from 21 publicly scanned**, of which 13 were already solved by public B31 cascade. No true factor/order influences public choice or classical factor test. The cumulative **B47 → fixed-seed bounded Pollard rho → full prime trial** ledger later FACTORED **all 8** selected B31 survivors by **public Pollard rho**. Thus NOTHING remains for real quantum factoring at this toy size.

Methodological new win: for exact ideal eigenphase mixture, 4-shot staged-QPE precision 4,6,…,34/36, all Q≤2^12 phase outcomes fully scored by FFT; above that, **65 centered phase outcomes per eigenphase** were explicitly evaluated. The omitted probability was bounded mathematically via its complement, with general bound ≤1/(2W−1)=1/63 at fixed W=32 (observed maximum stage omitted mass around 0.003118). Factor-producing acceptance is public CF denominator d even≤N + pow(base,d,N)==1 + actual nontrivial gcd. Two endpoints for each base: probability of factor extraction by cap and expected generic logical CCX per successfully factor-producing session with hypothetical restarts; bounds propagate **monotonically** through stage stopping. Floating-point roundoff was controlled by numerical tolerances, **not formally directed-rounding verified**. Nine tiny exact-full-FFT predefined control stage probabilities were confirmed within computed windows; all four independent CI validation jobs passed.

| bits | group | N | plain order→cube order (validation only) | mathematical ideal-model cube/plain successful-CCX ratio band | class |
|---|---|---|---|---|---|
| 17 | trigger | 84479 | 10098→3366 | [0.758107,0.805213] | model cube win |
| 17 | trigger | 99851 | 4830→1610 | [0.688894,0.722965] | model cube win |
| 17 | control | 69721 | 616→616 | [1.034223,1.050892] | **model cube LOSS** |
| 17 | control | 114391 | 6264→2088 | [0.760431,0.798302] | model cube win |
| **18** | **trigger** | **195473** | 47817→15939 | UNDEFINED, zero public valid factor-producing d | **factor incapable** |
| **18** | **trigger** | **256043** | 20930→20930 | UNDEFINED, zero public valid factor-producing d | **factor incapable** |
| 18 | control | 235687 | 39060→13020 | [0.768253,0.846631] | model cube win |
| 18 | control | 186751 | 1404→468 | [0.703023,0.720285] | model cube win |

**Primary n18 trigger locked cohort FAILED to establish a factor-producing cost benefit.** Both selected moduli have **empty public valid factor-producing denominator sets**, so their actual factor-production probability is identically zero under the specified public CF verifier, even if hidden validation order shrinks. The raw generic omitted-tail algorithm intentionally produces loose theoretical upper success bounds despite empty valid sets; straightforward public set-emptiness tightens the bound to [0,0] for those cases, with no fabricated success. Of 8 total, 5 analytically bounded cube model wins, 1 loss and 2 factor-incapable. These were all trivially classically factored, and the sample is far too small to generalize.

Independent logical phase recycling peak: **88→55** at n17 and **93→58** at n18 from one phase ancilla reuse with unchanged arithmetic workspace; NOT a physical-qubit saving claim or part of cube benefit. No new number-theory theorem, hardware speed/fidelity, fault-tolerant resource figure, RSA-scale factoring or real classical-plus-quantum speedup shown.

**Next useful step:** carry the frozen analytic-tail bound and public factor-denominator *empty set* zero certificate to a larger 20–24bit public semiprime population, with a frozen stronger classical budget, a proper locked holdout, numeric interval precision diagnostics and explicit classical wall-clock/operations separate from logical CCX; avoid QPU charges until a genuine hardware-relevant advantage is supported.


## 2026-10-14 — 20-bit v3 public-survivor manifest frozen before outcome scoring

The next independent Dark Star falsification moved to a **disjoint 20-bit
semiprime frame** `524288 <= N <= 1048575` and a publicly selected
classical-survivor design. The protocol was committed before hidden orders,
ideal-QPE outcomes, or resource comparisons were evaluated:

- `docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_PREREG.md`
- `hardware/dark_star_n20_public_survivor_v3.py`
- `results/dark_star_ptp/dark_star_n20_public_survivors_v3_manifest.json`
- manifest-freeze GitHub Actions **38677771046: SUCCESS**, zero QPU.

A frozen SHA256 rank and public-base rule, public repeated-squaring/GCD and
bounded Pollard p−1 stage-one B31, and strict no-resampling condition generated
**72 distinct surviving N** (12 per ell × trigger/control). The **293 publicly
screened** semiprimes include **221 already factored classically**; all screen
receipts were preserved in the committed manifest, not discarded.

Public manifest SHA256:
`a952fa4b57496136b29df7a3aca54a4361d4ec6ed5e0ee76c796602d5e840782`.

The resource scoring is frozen to a **4096-common-random-eigenphase estimator**
for r>4096 and exact validation-order enumeration for r<=4096, with a
public-only factor-producing continued-fraction predicate, not a hidden-order
shortcut. It is **nearest-bin-only ideal model sampling**, not exact full-QPE
distribution or QPU measurements; the preregistration explicitly records the
approximation and uncertainty bound before seeing any result.

The separate coherent-width claim remains **103 wide -> 64 recycled** peak
logical qubits under generic 20-bit clean-ancilla arithmetic, independent of
Dark Star. Prior selected-scout gains, n17/n18 mixed/negative population
evidence and the non-improvement of multi-exponent ladder vs always3 in earlier
trigger panels remain in force; this new holdout must be allowed to falsify
further selector claims. **No IBM Runtime paid use is authorized.**


## 2026-10-14 — Completed disjoint n20 v3 public classical-survivor holdout: narrow pass, broader uncertainty

**Successful fully reproducible milestone:** frozen public survivor manifest
`a952fa4b57496136b29df7a3aca54a4361d4ec6ed5e0ee76c796602d5e840782`
was committed **before** validation orders or quantum outcomes. Six independent
zero-QPU jobs completed and the strict all-72-row hash-matched merge succeeded
([Actions run 38677893149](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677893149)).
The complete result and all raw per-panel receipts were committed:

- `docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_PREREG.md`
- `docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_RESULT.md`
- `results/dark_star_ptp/dark_star_n20_public_survivors_v3_manifest.json`
- `results/dark_star_ptp/dark_star_n20_v3_full_holdout.json`
- six `results/dark_star_ptp/dark_star_n20_v3_ell{3,5,7}_{trigger,control}.json`.

**Classical-first gate:** 293 20-bit synthetic semiprime N candidates
publicly screened, **221** factored by the frozen cheap B31 public baseline;
**72 distinct classically unsolved** N (12 per ell/group) were scored.
This is a *conditional classical survivor* study, not a random-semiprime
population-average factoring claim.

The frozen ladder-versus-plain **trigger** ratios for model expected logical
CCX per successful factor-producing staged session were:

| Public-N stratum | Both factor-successful / 12 | ladder/plain | improved/tied/worse | bootstrap 95% CI |
|---|---:|---:|---|---|
| ell3 trigger | 9 | **0.832899** | 7/0/2 | [0.7723,0.9061] |
| ell5 trigger | 10 | **0.799052** | 8/0/2 | [0.7443,0.8702] |
| ell7 trigger | 9 | **0.806628** | 7/0/2 | [0.7443,0.8825] |

Every trigger stratum preserved modeled factor-production coverage and had a
strict improving majority among **both-positive comparable** cases; the
prespecified directional trigger gate passed. **Do not misread 'ell5 trigger'
or 'ell7 trigger' as evidence for the exponent ell=5/7**: these are
N-residue strata, and the public ladder preferentially chooses the cube
whenever N%3==2.

**Indispensable simpler baseline:** ladder/always-cube successful-session
ratios in the three trigger strata were **1.000000**, **0.994597**, and
**0.965400**. Ell3 ladder is identically cube, and ell5/ell7 row-bootstrap
95% intervals **include parity**. Thus the frozen broad gate technically
passes but a general **additional multi-exponent advantage over cube is
not established**. Do not erase prior negative ell5-enrichment, ell7, or
multichoice results.

**Numerical limitation was preregistered, not retrofitted:** true-order
eigenphases were exhaustively enumerated for r<=4096; for larger r the
nearest-bin ideal QPE probability uses 4096 seeded phase samples per stage,
not exact all-bin QPE. Worst-case 95% per-stage sampling error bound
±0.02122 is not an aggregate ratio error bound. The case bootstrap does not
measure phase-simulation variance. Verify near-parity ladder/always-cube
effects under independent frozen phase seeds and higher sample budget
before relying on them.

Independent generic 20-bit arithmetic logical width: **103 wide -> 64
recycled** peak (**37.86% fewer**); 63 coherent arithmetic logical qubits
remain. Zero IBM QPU jobs and no paid runtime. No QPU speed/fidelity,
physical fault-tolerance or RSA-scale claim.
