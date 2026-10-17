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


## 2026-10-14 — Independent 8192-phase numerical convergence confirms conditional v3 direction

After the successful 72-case n20 public-classical-survivor holdout, a
**separately preregistered independent numerical check** tested whether
the finite-phase eigenvalue sampling could be creating the apparent
ladder-versus-baseline resource effect.

- Preregistered BEFORE new outcomes:
  `docs/DARK_STAR_N20_PHASE_CONVERGENCE_PREREG.md`
- Six-panel independent 8192-seed sampler:
  `hardware/dark_star_n20_phase_convergence.py`
- GitHub Actions [38678433078](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38678433078): six shards + integrity merger **SUCCESS**;
  all 72 frozen N/base pairs and zero QPU jobs verified.
- Complete result:
  `docs/DARK_STAR_N20_PHASE_CONVERGENCE_RESULT.md`.
- All original per-panel and independent receipts committed separately:
  `results/dark_star_ptp/dark_star_n20_phase_validation_ell{3,5,7}_{trigger,control}.json`.

The independent **8192-phase** draws used a different frozen SHA salt on
the SAME N/sample, with exact r-enumeration for r<=8192. Neither public
selector nor factors/orders used to choose N were altered.

| Public-N trigger group | ladder/plain original 4096 | independent 8192 | ladder/always3 original | independent 8192 |
|---|---:|---:|---:|---:|
| ell3 | 0.832899 | **0.837287** | 1.000000 | **1.000000** |
| ell5 | 0.799052 | **0.799469** | 0.994597 | **0.995238** |
| ell7 | 0.806628 | **0.806123** | 0.965400 | **0.965520** |

The main **conditional modeled ladder versus plain** directional effect
is numerically stable at these two seeds/sample caps: all three trigger
panels preserve comparable case coverage and improving/worsening tallies;
all changes in aggregate ratio are <0.005 absolute.

**Important negative boundary preserved:** ladder versus simple always3
is **identical** in the ell3 trigger stratum. In ell5 trigger, the
near-parity ladder/always3 ratio stays slightly under 1 but one
individual comparison reverses from 2 improved /7 tied /1 worsened to
**1 improved /7 tied /2 worsened** under the new phase seed. Therefore
reliable *additional* value beyond always-cube is **not established**.
This is a stronger numerical diagnostic, not an independent new N
population or an all-bin exact QPE distribution. Original row-bootstrap
uncertainties for ell5 and ell7 ladder/cube comparisons include parity.

An individual 8192-sample per-stage ideal-nearest-bin Bernoulli
estimator has worst-case 95% Hoeffding absolute p uncertainty ~0.015;
this does not bound the final stopped-session CCX ratio. All numbers
remain logical resource models, not QPU measured runtime/fidelity,
physical-fault-tolerant resources, or RSA-2048 factoring.


## 2026-10-14 — New N22 classical-survivor policy holdout: cube replicates, ladder vs cube fails

**Research lead and original idea: Chase Lunsford / CaMaLabs.** Frozen the public-only N22 sample selection and the ladder-vs-unconditional-cube test before quantum order/model scoring; executed and completed an independent four-job zero-QPU holdout. Preserve all prior milestones and negative evidence: the 96-row n17 and 144-row n18 classical-first negative ell5/ell7 directions, 40 B31-survivor failed broad ladder superiority, 12-case exact full-phase distribution (only three factor-capable toy cases), 8-case rigorous all-bin omitted-tail model (primary n18 trigger factor-ineligible), and n20 72-case numerical-convergence study with near-parity ladder/cube.

**Immutable evidence:**
- Preregistered protocol `docs/DARK_STAR_N22_SELECTOR_VS_CUBE_PREREG.md` commit **`51b9584865081f6f829a7b5a592b72b7f687acad`**.
- Public-only freeze `results/dark_star_ptp/dark_star_n22_public_manifest.json`, commit **`b9326ab1a77eb50b24f9d145b5f68807e4752d92`** BEFORE scoring, SHA256 selected rows **`290a964bff4fc9ec4474d9fbd6e29fda111143113f93a1274cfafc94a8f02d98`**.
- Experimental runner `hardware/dark_star_n22_selector_vs_cube.py`; original manifest freeze plus four scoring jobs [GitHub Actions **38694538017**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694538017) all **SUCCESS**, exact public frozen case/choice verification, zero QPU, no paid runtime.
- Independent strict original-artifact verifier [Actions **38694776139**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694776139) **SUCCESS**. Four full raw JSON saved under `results/dark_star_ptp/dark_star_n22_{trigger,control}_seed_{A,B}.json` in commit `5e0f89d1a0204d340efb4b644380be24cf9936ca`. Interpretive report `docs/DARK_STAR_N22_SELECTOR_VS_CUBE_RESULT.md`.

**Sampling/classical wins:** 22-bit, 2^21≤N<2^22, distinct prime-pair semiprimes. Public N%3 trigger/control, six selected N per group; SHA-ranked, no order/factor-based sample selection. **31 publicly screened**, **19 already factored by frozen public B31 GCD/power2/Pollard p−1**, leaving **12 distinct B31 classical survivors** in frozen new cohort. Then cumulative PUBLIC B47/rho up to 64 iterations/seed completely factored all 12 additional N (**5 B47**, **7 rho**). No practical factoring value remains under this trivial classical budget.

**Frozen PRIMARY ladder vs simple always3, successful-session generic logical CCX:**
- CONTROL (where ladder chooses ell5 in 3 cases, ell7 in 3): independent 8192-eigenphase seed A ratio **0.965595**, seed B **0.965751**; success coverage always 6/6; **3 improved, 0 tied, 3 worsened** under BOTH seeds; same N win/loss signs. Between-N descriptive bootstrap 95% CI seed A **[0.8368,1.0854]** crosses parity.
- **PREDECLARED MAJORITY BENEFIT GATE FAILS**, despite ~3.4% lower aggregate weighted model cost. A single N=2750971 worsened ~25%, N=3230443 improved ~27.7%. No general public multi-exponent selector advantage beyond always3 established.
- TRIGGER: by construction ladder==always3 for all six, both seed ratios **1.000**, **0/6/0** improvement/tie/loss, correct identity and required negative selection control.

**Secondary N22 cube/plain ideal-model checkpoint:** trigger model cost-per-success ratios **0.786726** and **0.784368** under the two seeds, **6/6 paired improvements** with factor-producing model coverage preserved. Control: always3/plain ~0.9493 with **2 improve/4 worsen**; ladder/plain ~0.9167 with **2 improve/4 worsen**. Every N later classically factored by the stricter public cascade, so these effects are hypothetical logical-CCX *ideal nearest-bin QPE model* costs, NOT end-to-end factoring runtime or real hardware speedup. Numerical phase-sampling error for ratios is not formally bounded by the per-stage Hoeffding number; 2 seeds are only numerical replication.

**Independent phase recycling width:** at 22-bit generic clean-ancilla reversible arithmetic workspace 69 coherent logical qubits, wide peak 113 vs phase recycled peak **70** (43 or 38.05% fewer). No exponent-dependent width credit, no surface-code or physical-QPU resource claim.

**Next gate:** deploy mathematical ideal-QPE outcome-tail intervals (separate previously validated algorithm), not merely nearest-bin sampling, on an independently preregistered fresh larger-bit subset, then broaden sample without private-order conditioning. Distinguish theoretical QPE resource trends, classical factoring effort and true device capability. Never spend QPU funds based on current toy factoring evidence.


## 2026-10-14 — Fresh 22-bit all-outcome-head QPE with analytic tail and sampled-phase bounds; primary cube claim inconclusive

**Research lead and original quantum research direction: Chase Lunsford / CaMaLabs.** Independently preregistered and executed a next-step *FRESH disjoint* n22 classical B31 survivor holdout, now replacing nearest-bin-only *point estimates* with **all 65 nearest-centered outcome-bin probabilities per eigenphase**, mathematical omitted-bin mass bound `≤1/63`, and separate conservative simultaneous 99% phase-sampling uncertainty.

- Freeze: `docs/DARK_STAR_N22_FULL_OUTCOME_BOUNDED_PREREG.md`, commit `d06f4d948db24a4e7d357ab6bbb19e04a98219b0`, prior to selection/outcomes. PUBLIC-only sample artifact `results/dark_star_ptp/dark_star_n22_full_tail_public_manifest.json`, committed `2788bbe9760b815513a5d4f3f1bafe3686a70e92` BEFORE scoring by successful [manifest-freeze CI 38696615295](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696615295), sample SHA256 `d0cfd98eab0b92bc07c39a896e2e0039c3e065f6c6521c525dbefd676c2e49ff`. The public manifest excludes earlier 12 n22 samples, freezes N/a/exponent and public B31 ledger, NO validation factors/orders/quantum outcomes.
- Model: `hardware/dark_star_n22_full_tail_qpe_holdout.py` uses numba-accelerated PUBLIC CF denominator factor certificates, exact FFT all measurement outcomes for m≤12; for m>12 all 65 centered bins, analytic residual upper bound 1/63; 16,384 seeded eigenphase numerators for orders r>16,384 and exact r otherwise, Hoeffding/union 168-stage simultaneous 99% **conditional statistical** head-error epsilon `0.017834315`. Four staged ideal shots at m=4,6,…,44. These are **not exact all-QPE distribution or formally certified directed-rounding deterministic bounds** at all stages. No private factor/order enters CF success or public selection. Public factor certificate precomputation is classical work and can itself factor N; this cost is disclosed, never counted as free quantum advantage. No QPU jobs.
- Actual CPU-only scorer [GitHub Actions 38696858911](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696858911): **2/2 scoring jobs SUCCESS**, every frozen row, 21-stage complete receipts and strict public factoring checks. Independent original-artifact verifier/preservation [CI 38697122538](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38697122538) **SUCCESS**; exact original trigger/control JSON `results/dark_star_ptp/dark_star_n22_full_tail_{trigger,control}.json` committed `9d69c5bc19181f3096c65eabbf236e8e7046209c`. Full report `docs/DARK_STAR_N22_FULL_OUTCOME_BOUNDED_RESULT.md`.
- CI-only failures transparently recorded: combined freeze [38696682342](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696682342) failed to re-commit an already independently frozen public manifest; first score-only [38696809528](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696809528) shallow clone could not verify previous commit ancestry; corrected fetch-depth only. First preservation check [38697049370](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38697049370) accidentally counted the manifest itself among JSON receipts; corrected fixed filenames only. **No change to selection, sampling seed/size, W, alpha, online CF mathematics, factor/model endpoints after data.**

Frozen new public classical selection: **7 candidate semiprimes screened**, **3/7 factored by public B31**, **4 distinct B31 survivors** (two trigger N%3=2; two control N%3=1). After selection, stronger PUBLIC classical B47 solved 3, complete public prime trial solved 1; **all 4 solved classically**. Approximate logical model resources have no practical factoring value.

| Public stratum | N | order plain→cube validation only | PUBLIC good CF-denominator count plain/cube | cube/plain 99%-phase-sampled + analytic-tail CCX/success ratio band | conclusion |
|---|---:|---:|---:|---|---|
| **PRIMARY trigger** | **3623549** | 1809870→603290 | 1/3 | **[0.357458, 1.989375]** | **INCONCLUSIVE** |
| **PRIMARY trigger** | **3351017** | 836580→278860 | **0/0** | undefined | **factor-incapable**, strict public verifier cannot factor under either base |
| Control | 3910213 | 1931510→1931510 | 1/1 | [0.412419, 2.489615] | INCONCLUSIVE |
| Control | 2895517 | 718984→718984 | 2/2 | [0.475893, 2.136414] | INCONCLUSIVE |

**Primary preregistered gate FAILS/does not establish cube benefit**: it required TWO factor-capable model cube wins in frozen trigger; one comparison crosses parity and one has zero public factor-producing denominators despite order reduction. No certified cube win or certified loss on other cells at frozen statistical precision; all four are classically solved. No posthoc narrower reporting or favorable resampling. The previous n20/n22 approximate nearest-bin-only positive directional trends and earlier negatives remain preserved as method-specific evidence but **cannot outweigh this stronger inconclusive test**.

**Independent recycled-width checkpoint n22:** generic clean-ancilla arithmetic 69 coherent logical workspace qubits, textbook 44 phase qubits = 113 wide peak vs 70 phase-recycled peak (43 / 38.05% fewer simultaneous logical qubits). Separate from cubic order transform, NOT fault-tolerant physical cost or actual IBM QPU savings.

**Next conditional gate:** only after pre-registering genuinely new independent sample and strengthened statistical/analytic accuracy, evaluate full-outcome vs nearest-bin mechanism while disclosing all public classical factor recovery. No paid QPU experiment warranted by current data.


### Independent n22 full-outcome implementation cross-check — 2026-10-15 UTC

An entirely separate mathematical implementation of the SAME frozen four-case
22bit tail-bounded full-outcome QPE protocol independently completed:

- Independent implementation:
  `hardware/dark_star_n22_full_tail_bounded_qpe.py`
  (different public even-d certificate recurrence, vectorized 65-bin head
  and compiled Euclidean CF mask from the original scorer).
- Numerical computational run:
  [GitHub Actions 38697019918](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38697019918),
  both trigger/control jobs **SUCCESS**, all 4 frozen N scored, no QPU.
- The run's first automatic receipt commit encountered a Git **add/add
  rebase conflict**, because the original implementation had already
  committed results under the same canonical filenames. This is **not a
  scientific scoring failure**. No force push occurred.
- Independent numerical original-artifact reconciliation:
  [GitHub Actions 38697316318](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38697316318)
  **SUCCESS**. It validated the same public manifest SHA, four exact N/a,
  validation-only orders, public CF-good-denominator counts, and modeled
  factor-success intervals between **two separate implementations**.
  Independent receipts are preserved without overwriting originals at:
  `results/dark_star_ptp/dark_star_n22_full_tail_independent_{trigger,control}.json`.

**Independent confirmation, not a new population:** the original and separate
implementation both found the exact same primary trigger outcome: N=3623549
cube/plain conservative logical CCX-per-success band approximately
**[0.357458,1.989375]**, inconclusive; N=3351017 has **zero**
public factor-producing denominators under both bases despite reducing
validation order 836580→278860, hence successful-session ratio undefined.
Control N=3910213 gives **[0.412419,2.489615]** and N=2895517
**[0.475893,2.136414]**, both inconclusive. All four were independently
factored classically.

This independently preserves the numerical **win** (a separately coded
public certificate/full-outcome-tail/staged-cost method agrees on frozen
numbers) **and** the scientific negative: no preregistered n22 trigger
cube advantage survives these conservative full-outcome probability
intervals; 113→70 modeled logical-qubit width remains solely phase
recycling. Zero QPU or paid IBM Runtime.


## 2026-10-15 — Frozen same-four n22 precision-only audit: 3/3 narrower, 1 conditional ideal-model cube win

**Research lead: Chase Lunsford / CaMaLabs.** Completed preregistered **PRECISION-ONLY on reused N22 four-case public sample**, not a new independent holdout. Earlier original n22 full-outcome-head trial [38696858911](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696858911) had 3 inconclusive cube/plain model ratio bands and 1 provably public-CF-factor-incapable trigger. Its original preregistered primary benefit gate FAILED and remains failed as a historical result. All 4 were classically factored by public B47 or complete prime trial; public factor-producing CF certificate generation is also classically factor-recovering work and never free. Earlier positive/negative n17, n18, n20 and n22 findings remain preserved.

- Frozen methodological protocol **before numerical run**: `docs/DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_PREREG.md` commit `8c77ea5991b9990b7fab57ffda27fdf16e6383ef`, reusing original immutable public N/base SHA `d0cfd98eab0b92bc07c39a896e2e0039c3e065f6c6521c525dbefd676c2e49ff`. Same four Ns/bases and same strict public factor-producing CF denominator rule, 4 staged shots/m=4,6,…,44 and n22 abstract logical CCX costs. No quantum hardware/QPU.
- New model `hardware/dark_star_n22_numerical_precision_audit.py` commit `890cc65d0c19ec96b0befae1300517e0e1658130`: exact ALL-QPE-bin FFT through m=18 (rather than12); above that 65 geometric-sum centered output probabilities/eigenphase with analytically limited tail ≤1/63; **131072** shared-seed uniformly sampled eigenphases/stage (8× old) or exhaustive eigenphases when r≤131072. Empirically observed omitted mass bounded separately using **Maurer–Pontil variance-sensitive empirical Bernstein** 2-sided stage bound, simultaneously 99% nominal under IID uniform draws, union budget 672 for N×base×stage×head/tail×two-sides. CPython PRNG not a certified random source; floating trig values not directed-rounding proof. These are **confidence intervals conditional on numerical and sampling assumptions**, not rigorous hardware or complete deterministic-QPE bounds.
- Actual two-group full research run [CI 38730414791](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730414791) **2/2 success**; original exact raw JSON independently verified and preserved in [CI 38730702345](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730702345) **SUCCESS**, saved `results/dark_star_ptp/dark_star_n22_precision_audit_{trigger,control}.json` without altering the old receipts. Verified full [result](DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_RESULT.md).

| Frozen reused 22bit N | Original 99%-head/tail cube/plain cost band | Higher precision band | Finding |
|---:|---|---|---|
| **3623549** (trigger) | [0.357458,1.989375] | **[0.718747,0.857407]** | **conditional model cube win**, but NOT independent validation |
| **3351017** (trigger) | UNDEFINED, public denominator empty | **UNDEFINED** | **factor incapable**; original failed primary not erased |
| **3910213** (control) | [0.412419,2.489615] | **[0.923670,1.105982]** | inconclusive |
| **2895517** (control) | [0.475893,2.136414] | **[0.942183,1.078764]** | inconclusive |

**NEW NUMERICAL-PRECISION MILESTONE:** all **3/3 originally factor-capable** comparisons have narrower intervals (ratio widths about **11.77×, 11.39×, 12.16×** smaller), exceeding frozen precision-method ≥2/3 gate. One previously uncertain reused trigger now shows **14.3–28.1% fewer modeled logical CCX per successful ideal-QPE factor**, conditional on the confidence assumptions. There are still **two inconclusive controls**, and **one provably factor-incapable trigger**. The original two-case trigger success claim DOES NOT now pass in retrospect. Sample wasn't expanded or randomly redrawn, so no new population inference. All 4 were classically factored, and classical good-denominator prep has its own public factor recovery.

Independent n22 phase recycling width remains **113→70** abstract simultaneous logical qubits, distinct from transformed modular order; no physical, fault-tolerant, device-fidelity, runtime or RSA cryptanalytic result. The next properly falsifiable experiment would require a **brand-new frozen public sample** run under this unchanged higher-precision protocol, with true classical preprocessing overhead properly separated from gate-model CCX.


## 2026-10-15 — Fresh n22 high-precision independent holdout passes narrow cubic model gate; reverse-SynthID transfer assessed

**Research lead/original work:** Chase Lunsford / CaMaLabs. Proceeded beyond the prior N22 precision-only reanalysis on the SAME four cases by independently preregistering a genuinely NEW public B31 survivor sample **before seeing any new outcome**. Also inspected **Alosh Denny's** `aloshdenny/reverse-SynthID` image-watermark spectral research, attribution and noncommercial research license, with a separate methodological-transfer memo `docs/REVERSE_SYNTHID_TRANSFER_AUDIT.md`. No SynthID code, image-watermark bypass, carrier scoring or adapted hyperparameters were inserted in the frozen Dark Star experiment.

- Frozen protocol `docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md`, commit `ddf910cf187b11d1f800c2d4a65d0473cbfd4035`; public-only manifest in `results/dark_star_ptp/dark_star_n22_precision_fresh_public_manifest.json` committed `67ec6bcdd8cd91d033663c7fab27a646b9ac052f` strictly **BEFORE** validation factor/order or QPE scoring. New selected public SHA `5c18715c4448069e6231645e180e216b7e591e15a149cbc12d486fe9b9664570`, **eight** disjoint n22 N, excluding **all sixteen** used in prior N22 experiments, without private-order/factor-based selection.
- [CI frozen public selection + scoring 38808625980](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38808625980): **3/3 jobs SUCCESS** (public freeze, trigger, control), zero IBM/QPU usage. Reuses **EXACT same** phase-precision method: all outcomes via FFT m≤18, 65 centered bins/eigenphase for m>18 and analytic omitted-tail ≤1/63, 131072 uniform SHA-seeded phase draws/stage if order>131072 otherwise exhaustive, variance-adaptive empirical Bernstein 99%-simultaneous *statistical* stage bounds. 1344 union-test budget correctly accounts for eight Ns; no posthoc method or seed change. Staged factor-producing public-CF and generic abstract CCX-per-success model unchanged.
- [Independent untouched-original-receipt preservation CI 38809052306](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38809052306): **SUCCESS**. Verified frozen sample SHA, all 8 genuinely novel public Ns, B31 screens, strict public factor correctness, identity and QPE interval invariants; exact original raw JSON saved `results/dark_star_ptp/dark_star_n22_fresh_precision_{trigger,control}.json`. Complete result `docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_RESULT.md`.
- Public classical baseline: **25 screened Ns**, **17 factored with B31**; first four B31-surviving N in each group selected. ALL **8** selected were then factored by public B47 (1) or bounded fixed-seed Pollard rho (7). Thus **zero practical quantum factoring workload** left and no physical speedup claim. Model's *public* exhaustive factor-certificate enumeration itself entails major classical work that can recover factors, never free QPU overhead.

| Group | N | Validation order a→a³ | 99%-conditional model cube/plain logical CCX per factor-producing success | Finding |
|---|---:|---:|---|---|
| **TRIGGER primary** | **2620559** | 1294452→431484 | **[0.788770,0.914991]** | cube model WIN |
| **TRIGGER primary** | **2622779** | 621180→207060 | **[0.781293,0.915851]** | cube model WIN |
| **TRIGGER primary** | **2489897** | 414286→414286 | UNDEFINED; zero public factor-producing CF denominators | factor incapable, retained |
| **TRIGGER primary** | **3511889** | 116622→38874 | **[0.805697,0.852538]** | cube model WIN |
| Control | 2322043 | 94500→31500 | **[0.805949,0.853348]** | model cube WIN |
| Control | 2207089 | 1093178→1093178 | UNDEFINED | factor incapable |
| Control | 2556181 | 1350→450 | UNDEFINED | factor incapable despite shorter order |
| Control | 3202981 | 644→644 | UNDEFINED | factor incapable |

**FIRST independent high-precision model replication: frozen PRIMARY TRIGGER gate PASSES** by predeclared criterion (>=3/4 both-factor-capable, >=3/4 bounded model cube wins, no cube coverage loss). This gives stronger narrow evidence for an **idealized conditional algebraic/abstract logical CCX mechanism** than the earlier SAME-case audit. Factor-producing coverage remains a serious weakness (four of eight Ns can never produce factors under the frozen verifier). Independent CONTROL sample has only one factor-capable/model-win row of four, all others incapable. **All eight are trivially classically factored**; no real quantum advantage, RSA-scale algorithm or hardware result. Recycled n22 analytic peak logical width remains **113→70**, solely due to iterative phase-register reuse, not the cube transform.

**External reverse-SynthID review:** Alosh Denny's reverse-SynthID focuses on image-watermark Fourier residuals and *cross-color phase consensus*, using `|mean exp(iφ)|` across nuisance backgrounds to suppress content-specific frequency artifacts. The transferable research-design concept is **multi-condition phase-coherence plus shuffled-phase / matched-noise null controls**, and clean model-by-resolution bookkeeping, NOT automatically a quantum modulus/order invariant or factoring oracle. User-facing README claims of robust detector/bypass do not establish universality; GitHub issues report model-dependent failures/false positives. Its `LICENSE` is research/noncommercial with explicit attribution and commercial-use limits. Do not copy source, profiles or bypass code; independently preregister a new synthetic-control robustness pilot if desired. Full externally attributed rationale `docs/REVERSE_SYNTHID_TRANSFER_AUDIT.md`. **Nothing from SynthID contaminated the frozen primary outcome.**

Next gate: larger newly frozen public population, strict classical budget accounting and genuine phase/noise controls. Conditional ideal-QPE/generic CCX interval benefits are NOT measured QPU runtime/fidelity/physical-qubit savings and do not establish practical factoring speedup.


## 2026-10-16 — QPE cross-reference phase consensus pilot and OPEN-only real QPU fail-closed hardware attempt

**Lead and original quantum research: Chase Lunsford / CaMaLabs.** User authorized real hardware only with verified **IBM Quantum Open Plan**, NEVER paid runtime. Existing reversible Shor15 N15 source and `ibm_runtime_guard.assert_open_plan_submission` reviewed. IBM Quantum 2026 documentation confirms Open Plan offers free device access within limited rolling usage. No QPU assumptions substituted for actual device receipts.

**Preregistered pilot** `docs/QRR_CROSS_REFERENCE_COHERENCE_AND_OPEN_QPU_PREREG.md` commit `33393fafa10ee21dbf8c08f0a9dd91a63547e1c2`. Inspired by Alosh Denny's `aloshdenny/reverse-SynthID` cross-condition spectral coherence but all original independent implementation; see credited licensing/transfer audit `docs/REVERSE_SYNTHID_TRANSFER_AUDIT.md`. No original third-party code, watermark bypass routines or data copied.

**Synthetic cross-reference FFT phase-consensus test PASSED limited signal+null gate:** CPU-only [GitHub Actions 38987863052](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38987863052) SUCCESS; original JSON preserved `results/dark_star_ptp/qrr_spectral_phase_consensus_pilot.json`. Two toy validation *known* QPE orders r4 and r6, 256-bit outcome bins, 8 independent 2048-shot histogram blocks, fixed harmonic k=r, 32 signal replicates, 128 training shuffled nulls, 64 independent test controls each. Circular mean Fourier phase coherence detects 32/32 signal replicates even at 35% white shot contamination; permutation null FPR 3/64 for r4, 2/64 for r6 and white-noise FPR 1/64 each. **CRITICAL NEGATIVE: stable fixed-bin apparatus artifact creates 64/64 = 100% false-positive** for BOTH r4/r6 at the same threshold. So phase-coherence is a repeatability metric, NOT a factor, order oracle or robust detector of authentic quantum physics. The chosen frequency depends on KNOWN synthetic validation order; it does not infer unknown order on real RSA keys. No QPU or practical speedup.

**Real Open-only device attempt correctly BLOCKED before submission:** [workflow 38987891370](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38987891370) and [manual-ready guard workflow 38987984332](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38987984332) both complete as fail-closed preflight: GitHub Actions did NOT receive `IBM_QUANTUM_API_KEY` and has no saved local account; current `results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json` is `PREFLIGHT_BLOCKED`, `submission_performed=false`, `job_id=null`. This is **zero actual QPU jobs, zero hardware data and zero QPU execution cost**, not device validation. Main protected script `hardware/qrr_ibm_open_only_real_qpu_pilot.py` uses an Open Plan exact active-instance confirmation twice, immediately before at-most-one Sampler submission; single matched real N15 circuit pair (5-qubit recycled and 8-qubit wide), 64 shots/circuit and max_execution_time=30 sec, native gate/depth limits, no simulator or paid fallback. User's Ubuntu saved IBM account may work when run locally; GitHub Actions requires a protected `IBM_QUANTUM_API_KEY` repo secret. No key should be pasted in chat, committed or logged. Manual-only workflow_dispatch is now available; no recurring QPU trigger.

[Full report](QRR_SPECTRAL_COHERENCE_OPEN_QPU_STATUS.md). Historical n22 conditional cubic ideal model wins, negative factor-production coverage, 113→70 independent abstract logical phase recycling and all classically solved public semiprimes remain preserved. A real IBM N15 Shor demonstration would test phase reuse, **NOT cubic Dark Star order reduction** because ord_15(2)=4 and gcd(4,3)=1. Prior larger small-N IBM-target runs compiled millions of CZ and are unsuitable for Open Plan real-hardware factoring; no paid QPU authorization and no modern RSA-scale factoring claim.

**Next step requires credential availability, not a new algorithm**: execute single real N15 matched circuit only after verifying active instance plan=open and valid API token/saved local account. Report actual job id+raw counts if succeeded; do not describe a simulated numerical signal as QPU proof.


## 2026-10-16 — FIRST VERIFIED REAL IBM Fez OPEN PLAN QPU Shor15 recycled-vs-wide success, proper factors 3×5 measured

**Research lead/original program: Chase Lunsford / CaMaLabs.** Hardware credential repaired and checked without disclosure. Fresh [safe IBM account-only credential test run 38994675557](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38994675557) VERIFIED nonempty correct-format Platform API key, IBM service authenticated successfully and Open Plan instance available; **zero QPU** consumed in that prerequisite. The original one-shot, PRE-BOUNDED `hardware/qrr_ibm_open_only_real_qpu_pilot.py` then passed both live active-instance plan==`open` guards, once after backend selection and again **immediately before** actual SamplerV2 submission. NO paid runtime, simulation or silent fallback. Real [GitHub Actions run **38994722997**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38994722997) **SUCCESS** with actual IBM Fez QPU returned `status=MEASURED_REAL_QPU`, backend `ibm_fez`, real QPU job ID **`db9dod1gv2cc73e5c410`**, original 64 measured bitstrings per arm. **This is REAL device execution, not an ideal simulator.** The complete unchanged raw [JSON](../results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json) including all counts, native transpilation and live Open Plan receipt was preserved by original CI commit `e6d41302d3786957bee27f734c580e438e32c311`. Full [scientific result](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md).

| Actual IBM Fez one-shot metric | 1-phase-bit recycled | 4-phase-bit wide |
|---|---:|---:|
| Original simultaneously live logical circuit qubits | **5** | 8 |
| Real transpiled native CZ | **55** | 87 |
| Real transpiled depth | **180** | 221 |
| QPU shots | 64 | 64 |
| **Proper public Shor GCD-factor recovery 3×5** | **49/64 = 76.5625%** | **38/64 = 59.375%** |

Original measured bitstrings recycled `1000:18, 1100:15, 1101:1, 0100:16, 0000:14`; wide `1000:11, 1011:2, 1100:8, 1101:1, 0000:21, 0100:19, 0110:1, 0010:1`. Two circuits **×64 shots**, one real Open Plan Runtime Sampler job, `max_execution_time=30` seconds. Structurally 3 fewer logical qubits (37.5% fewer vs 8), transpiled 36.78% fewer native CZ (55 vs87), 18.55% less depth (180 vs221). Measured **+17.1875 percentage points** higher observed proper-factor shot rate in this run; **NOT independently established generic hardware fidelity improvement** because 64 shots/arm, different physical layouts, noise, drift and transpiler conditions. The backend's compiled Qiskit circuit width 156 is the device-size representation, not number of active logical qubits; raw receipt contains the actual 5 vs8 mapped positions. Factors 3,5 of N15 trivial classically.

**CRITICAL BOUNDARY:** This REAL QPU test demonstrates actual 5-vs-8 logical-qubit phase recycling and proper factor recovery on a tiny real modular-multiplication QPE circuit. It does **NOT** test Dark Star cubic preconditioning: N15,a2 has r=4 and `gcd(r,3)=1` so cubic transformation cannot shorten order. It does NOT confirm earlier n22 ideal-CCX/polynomial modular arithmetic scaling, actual RSA speedup or physical fault-tolerance. Prior independently frozen 22-bit conditional model trigger wins and all negative zero-factor-capability/classical factor controls remain fully recorded. No additional paid QPU or second device study launched. Next needs separate preflight/preregistration to target cubic mechanism with genuinely hardware-feasible, public-classically audited semiprime and matched layouts/shot budgets.


## 2026-10-16 — N35 public cube full-residue IBM Fez native compilation ~61% lower CZ/depth; real-QPU feasibility FAILS

**Research lead/original CaMaLabs quantum work: Chase Lunsford.** Following the genuinely REAL IBM Fez free-Open-Plan N15 phase-recycling factor-recovery milestone, the N35 public cubic-order mechanism was tested against the **native IBM Fez target COMPILER only (ZERO QPU jobs)**. The preregistered [N35 4-bit frozen public cube native preflight](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_PREREG.md), commit `bc14c01e87b3847b6edea9d633aeb6539a20bbad`, fixes N35,a2,b8, 4 QPE bits, both wide/recycled, seed8776, HLS `1_clean_kg24`, optimization2, live `ibm_fez` target, and native feasibility caps **CZ<=800 and depth<=2000 for EVERY baseline/cube arm**. True order **12→4** is validation-only. Proper half-order factor witness publicly preserved `2^6 mod35=8^2 mod35=29`; gcd(29±1,35) yields 7/5, classically trivial.

[Original ZERO-QPU GitHub Actions run 38995707019](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995707019) **2/2 architecture jobs SUCCESS**, each compiling both bases via public-order-independent full **64-state modular permutation** (no secret order or 12-state orbit lookup), exhaustive semantics and fixed transpiler seed. The [original untouched binary-JSON artifact preservation CI 38995864891](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995864891) **SUCCESS** after a CI-only failed attempt [38995789970](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995789970) with wrong artifact-relative copy path, fixed without changing experiments. Original receipts: `results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_{recycled,wide}.json`, complete [result report](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md).

| Frozen four-bit N35 native target comparison | Base2 order12 | Cube8 order4 | Cube reduction |
|---|---:|---:|---:|
| Recycled `ibm_fez` CZ | 8455 | **3325** | **60.674%** |
| Recycled native depth | 17108 | **6595** | **61.451%** |
| Wide `ibm_fez` CZ | 7946 | **3081** | **61.226%** |
| Wide native depth | 17193 | **6616** | **61.519%** |
| Original logical qubits | recycled11 / wide14 | recycled11 / wide14 | same within architecture |

**Recorded native compiler win:** Cubing makes exactly **two of the four** QPE controlled modular-power rounds identity, completely eliminating them from the full-register permutation path. Coherent unitary semantics are validated with *public base only*; native resource benefit exceeds just ideal-QPE numerical cost trend. **Recorded failure:** even the best cube arm uses **3081 CZ and 6616 depth**; EVERY baseline/cube arm fails frozen **800 CZ / 2000 depth** hardware feasibility bounds. There was **ZERO actual QPU use** in this study; a target backend compilation does not mean real QPU ran. **DO NOT submit generic full-residue N35 circuits to the free device on these results.**

The full-permutation compiler is public/order-independent yet NOT scalable generic modular arithmetic (exponential truth-table synthesis). The cheaper separately available 12-cycle affine orbit encoding is order-dependent compiled toy hardware and must not be silently substituted as equivalent. Next prioritize zero-QPU public reversible arithmetic-efficient multiplication redesign or separately preregistered explicitly compiled N35 toy proof; fixed-precision CZ/depth alone does not certify success per factor, noisy-device fidelity or RSA factoring benefit. The earlier real N15 hardware milestone remains intact and distinguishable.


## 2026-10-16 — N35 public reversible-arithmetic replacement compiler: cubic halves internal CZ but 0.86–1.73M CZ FAILS real-QPU feasibility

**Research lead: Chase Lunsford / CaMaLabs.** Follow-up to [N35 public cube full 64-state permutation target compiler](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md): despite cubic validation order r12→r4 and 61% lower CZ/depth with the full-residue permutation method, all four earlier 4bit circuits FAILED frozen ≤800 CZ/≤2000 depth hardware gate. No QPU was used. New [preregistered arithmetic-based replacement](QRR_N35_ARITHMETIC_REPLACEMENT_PREREG.md) was frozen commit `fad3b278da40d7dd12c6e06fcae201eb6380e72a` BEFORE native compiler scoring. The goal was to replace the 64-state *truth-table synthesis* with existing general n-bit reversible shift-add modular multiplication, full clean accumulator/uncomputation and invalid-state identity. The new [original identity-pruned implementation](../hardware/qrr_n35_public_modarith_identity_pruned_preflight.py) consumes only PUBLIC N and base powers: baseline a=2 controlled multipliers [2,4,16,11], cube a=8 [8,29,1,1]. Skip m==1 identity rounds without true order or orbit oracle; cube removes two of four rounds, baseline none. Uses existing `generic_modarith_shor.py` classical full-residue semantic checks and eager controlled IntegerComparator/DraperQFTAdder compatibility decomposition (`ibm_shor35_generic_modarith_preflight_explicit.py`). The classical shadow test is NOT complete quantum gate-level equivalence proof.

[GitHub Actions 38996345928](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996345928): **4/4 native Fez target compiler jobs SUCCESS**, no QPU, four-bit QPE, seed8776, optimization level1. [Independent original-artifact preservation and verification CI 38996529069](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996529069): **SUCCESS**, original receipts committed `results/ibm_shor35_modarith_identity_pruned/qrr_n35_public_modarith_{recycled,wide}_{plain,cube}.json`, unchanged; [full result report](QRR_N35_ARITHMETIC_REPLACEMENT_RESULT.md).

| N35 public-base arm, 4 phase bits | Base2 original order12 | Cube8 order4 | Cube benefit INTERNAL to arithmetic compiler |
|---|---:|---:|---|
| Recycled native CZ | **1,732,072** | **859,632** | −50.37% |
| Recycled native depth | 4,766,896 | 2,370,305 | −50.28% |
| Wide native CZ | **1,733,136** | **860,151** | −50.37% |
| Wide native depth | 4,763,959 | 2,372,924 | −50.19% |
| Logical application qubits | 26 recycled /29 wide | 26 recycled/29 wide | unchanged within architecture |

**Recorded negative finding:** Although replacing the full-permutation truth table with genuinely n-bit modular arithmetic makes the construction structurally generic, native compilation of nested controlled QFT adders and comparators exploded to 0.86–1.73 **MILLION** CZ and 2.37–4.77 **MILLION** depth. The previous order-independent full-residue direct-transposition method was much cheaper at this 6bit scale (cube 3325 CZ recycled /3081 CZ wide), though the compared compiler optimization levels differ (old2,new1), so treat cross-method contrasts as descriptive. NONE of the four new circuits passes the **frozen ≤800 CZ & ≤2000 depth** device gate; primary hardware feasibility FAILS, absolutely ZERO QPU submissions and no Open Plan allowance consumed. Cubing still saves ~50% *internally*, but the reversible-arithmetic lowering is the bottleneck. No applied factoring/hardware-speedup or new mathematical theorem.

**Next stage:** Purpose-built in-place ripple-carry/Toffoli modular constant adder avoiding generic nested multi-controlled QFTAdder, with independent tiny-reversible-gate semantic controls BEFORE another four-bit run; report any negative tests without relaxing hardware thresholds. Original real IBM Fez Open Plan N15 phase-recycling proper-factor success remains intact and separate from untested on-QPU cubic preconditioning.


## 2026-10-16 — Primitive N35 Toffoli/ripple single controlled multiplier: 128/128 actual emitted gate semantics PASS, hardware CZ gate FAIL

**Research lead / originating quantum methodology: Chase Lunsford / CaMaLabs.** Following the full N35 public order-independent permutation native Fez compilation positive model-cost reduction but failed device hardware gate, and the general n-bit nested QFT-adder modular arithmetic's 0.86–1.73 MILLION CZ native compilation failures, initiated the next explicit **X/CX/CCX/Toffoli-only reversible ripple and constant-add modular multiplication kernel** experiment. This was preregistered `docs/QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_PREREG.md`, commit `8e4031f2ca9e4efac853058d45625a1d8807106f`, before running any native costs. ZERO QPU permitted or used.

- Original public-only [`hardware/qrr_n35_single_modmul_ripple_toffoli.py`](../hardware/qrr_n35_single_modmul_ripple_toffoli.py) explicitly implements unsigned constant carry recurrence, reversible clean comparators, descending suffix-bit incrementers and clean multi-control Toffoli v-chains, modular wrap/subtract/uncomputation, and six weighted-add controlled multiplication/controlled swap/inverse erase. NO QFT, hidden orbit, precomputed order or secret factor. Controls off and invalid y>=35 must act as identity.
- **Verified structural win:** Both publicly fixed N35 single-multiplier kernel arms `a=2` and `a³=8` passed **ALL 128/128 actual emitted primitive quantum gate computational-basis tests** (all 64 work inputs and both control bits), **EVERY one of 23 scratch/accumulator/flag ancillas exactly restored to zero**. 30 logical circuit qubits total, original primitive gate totals 1964 base2 vs2062 base8. This is stronger evidence than prior classical-only shadow arithmetic but still ideal Boolean gate semantic proof, NOT QPU/noise proof.
- First [CI 38996961616](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996961616) failed **after** the gate-level proofs because the backend read used locally-saved IBM credentials unavailable to GitHub; fixed only encrypted API key target-read wiring in commit `1e17faef6abeddbeeb2b9d8d6236ca900defce7e`, NO changed arithmetic or algorithm. The unchanged [second CI 38997012532](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997012532): **2/2 SUCCESS** independent base jobs, same IBM Fez *target* metadata, Qiskit2.5.2, optimization1, transpiler seed8776. No Sampler/Estimator QPU calls. [Independent untouched receipt audit CI 38997085447](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997085447) **SUCCESS**, original numerical JSON committed `b064ced6f503b499457d9e01e30f130dc5bb7fb5`: `results/ibm_shor35_ripple_toffoli_kernel/qrr_n35_toffoli_ripple_single_mul_base{2,8}.json`. Full [verified result](QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_RESULT.md).

| N35 ONE full-residue controlled multiplier | Public a2 | Public cube a8 |
|---|---:|---:|
| Actual primitive gate-level cases | **128/128 pass** | **128/128 pass** |
| Total X/CX/CCX gates | 1964 | 2062 |
| Logical qubits | 30 | 30 |
| **IBM Fez compiled native CZ** | **27,929** | **29,822** |
| **Compiled native depth** | **59,947** | **63,922** |
| Frozen feasibility CZ≤800 AND depth≤2000 | **FAIL** | **FAIL** |
| Real QPU jobs | **0** | **0** |

**Critical new negative interpretation:** cube8 single controlled multiplication costs **6.78% MORE CZ** and **6.63% MORE depth** than base2 when compiled with the same primitive arithmetic. The cubic power-order 12→4 effect cannot magically reduce ONE modular multiplication's cost; its prior four-phase-round benefit came from two of four public powers becoming identity in the cube schedule `[8,29,1,1]`, compared to plain `[2,4,16,11]`. This new single-multiplier kernel is much simpler than previously controlled QFT-based arithmetic, but different work scopes make raw per-method 1-round-to-4-round CZ ratios misleading. **Neither single controlled modular multiplication is acceptable for another real QPU hardware run** (over 34× CZ threshold and >29× depth threshold). No free Open Plan runtime consumed. Recycled hardware N15 original 49/64 proper-factor success remains independently preserved.

Next gate: factorized constant-specific modular arithmetic, reuse carry ancillas and reduce heavy multi-control chains, with a new frozen small-resource test BEFORE full Shor QPE or user-authorized hardware. Do not silently substitute order-dependent orbit compilation or weaken CZ≤800/depth≤2000 posthoc.


## 2026-10-16 — Public N35 cached enable controls cut REAL-TARGET compiler CZ 33%; 128/128 gate proof PASS, hardware feasibility FAIL

**Research lead: Chase Lunsford / CaMaLabs.** Continue the original reversible full-residue N35 modular-multiplication program, preserving the previous independently verified N15 real IBM Fez Open-only recycled QPE factor recovery and the N35 negative public-permutation and general-arithmetic reports. The immediately preceding [explicit single controlled X/CX/CCX Toffoli/ripple kernel](QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_RESULT.md) had gate-level proofs 128/128 (all 64 six-bit y values × both control states; every 23 ancillary bits uncomputed) with IBM Fez compiler results base2 CZ27929 depth59947, cube8 CZ29822 depth63922. Both FAILED frozen **CZ<=800 and depth<=2000** hardware criteria. No device run.

**Frozen before new scoring:** [QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md), commit `bffed30fb4c7db1a5b6c92437c06b94ebf9b81a7`. ONE new intervention, preserving the exact same prior verified reversible comparator/modadd/Toffoli arithmetic functions: compute `active=phase AND valid` once, compute/reverse `enable=active AND work[i]` for each of six forward and six inverse modular additions, use `[enable]` instead of repeatedly applying three-element control `[phase,valid,work[i]]`, and use `active` for the coherent controlled register swaps. Adds two **clean** control ancillas, so 30→32 logical qubits. No private factors/order, handwired order-orbit, new gate decomposition, QFT, alternate transpiler seed or layout tuning.

[Original matched 2/2 CPU proof + IBM Fez-target only compilation CI **39005624438**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005624438) SUCCESS, `qiskit~=2.5.2`, runtime~=0.47.0, opt level1, seed8776. **ALL 128 actual emitted X/CX/CCX gate-input controls×residues pass for BOTH a=2 and cube a³=8, every one of 25 aux qubits cleaned**; no Sampler, real quantum runtime or hardware execution. The [independent original CI receipt audit/preservation **39005699941**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005699941) SUCCESS and saved **unchanged original JSON files** `results/ibm_shor35_ripple_cached_controls/qrr_n35_cached_enable_single_mul_base{2,8}.json`. Full [experiment result](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_RESULT.md).

| N35 full six-bit ONE controlled modmul, Fez ISA COMPILER ONLY | Old unlatched | New cached | Benefit |
|---|---:|---:|---:|
| Base2 primitive source X/CX/CCX |1964|**1536**|−21.8%|
| Base2 native CZ |27929|**18719**|**−32.98%**|
| Base2 native depth |59947|**42335**|**−29.38%**|
| Cube8 primitive source X/CX/CCX |2062|**1578**|−23.5%|
| Cube8 native CZ |29822|**19912**|**−33.23%**|
| Cube8 native depth |63922|**44381**|**−30.57%**|
| True ideal gate-level proof |128/128|**128/128**|all helpers zero|
| Logical circuit qubits |30|32|two new clean ancillas|
| Frozen <=800CZ / <=2000depth |FAIL|**FAIL**|zero real QPU|

**Verified engineering success:** ~33% lower native CZ and 29–31% lower compiled native depth in *both* fixed public arms, traceable to shared enabled controls. **Verified hardware limitation:** even smallest arm 18719 CZ/42335 depth remains **23.4×** / **21.2×** frozen hardware criterion, so not feasible for free Open QPU experiment; ZERO actual QPU jobs, free or paid runtime. Cube remains **more expensive per SINGLE multiplier** than base2 (19912 vs18719 CZ), consistent with no claim about order-shortening benefit until multi-round QPE tests. Different fixed-layout qubit count (32 vs30) means this is an honest target-native compiler engineering ablation, NOT a controlled hardware fidelity comparison, practical factoring result or fault-tolerant asymptotic claim.

**Next scientific move:** preregister/freeze a separate **constant-specific modular carry/prefix circuit** to reduce the repeated wrap comparator and high-fan-in Toffoli v-chain overhead. Repeat independent actual-gate 128-state tests and immutable CZ/depth native target audit before considering a full 4-bit factoring pipeline, and never silently weaken prior device thresholds or substitute order-encoded affine toy circuits. 


## 2026-10-16 — N35 low-prefix carry and public threshold stripping: verified extra 33–36% native CZ saving, device gate still FAIL

**Research lead / originating program: Chase Lunsford / CaMaLabs.** New fixed zero-QPU arithmetic optimizer [frozen preregistration](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_PREREG.md), original pre-scoring git commit **`ca7d523a1c2b0e752d7c69b5c73a416964a11622`**, designed after the prior [N35 cached active/enable control](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_RESULT.md) passed full ideal gate-level proofs but still failed hardware feasibility. Old source baseline base2 CZ18,719 depth42,335; cube8 CZ19,912 depth44,381; 32 logical qubits, 25 returned-clean ancillas. Frozen limit CZ≤800 native / depth≤2000 for EVERY arm and NO QPU submission.

New original [`hardware/qrr_n35_public_prefix_carry_single_modmul.py`](../hardware/qrr_n35_public_prefix_carry_single_modmul.py) retains old controlled multiplier, active+enable logic, validity check, clean accumulator and Toffoli source primitives. A SINGLE combined candidate replaces controlled constant suffix-ripple increment with a per-output-bit prefix-carry toggle while lower input bits are still unchanged (from highest to lowest), and strips known trailing zeros of public comparison thresholds. Does **not** use N35 true orders, factors, affine orbit or a precomputed full truth table. Only X/CX/CCX actual source gates, no Sampler/Estimator.

[Original 2/2 independent native CPU target-compiler jobs **39006320227**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006320227) SUCCESS, Qiskit~=2.5.2, IBM Fez TARGET read-only, opt1, seed8776. Each arm **PASSED direct emitted-gate subroutine verification for every 16 public modular-add constants ×(35 valid enableON +64 enableOFF)=1,584/1,584**, AND complete controlled multiplier public y=0..63 × control{0,1} **128/128 ideal-gate cases per arm**, every **25 helper qubits clean**. [Independent unchanged original JSON audit/preservation CI **39006395142**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006395142) SUCCESS, receipts `results/ibm_shor35_public_prefix_carry/qrr_n35_public_prefix_carry_base{2,8}.json`. Full [report](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md).

| IBM Fez TARGET compile of ONE full-residue public N35 multiplier | Old cached base2 | New base2 | Old cached cube8 | New cube8 |
|---|---:|---:|---:|---:|
| Source X+CX+CCX primitive gates |1536|**1817**|1578|**1883**|
| Source CX |445|**1033**|445|**1077**|
| Source CCX |1063|**756**|1105|**778**|
| Native CZ |18719|**12517**|19912|**12680**|
| Native depth |42335|**32312**|44381|**33138**|
| Logical qubits |32|32|32|32|
| Real QPU jobs |0|**0**|0|**0**|

**Verified new engineering win:** base2 native CZ **−33.13%**, depth **−23.68%**; cube8 native CZ **−36.32%**, depth **−25.33%**, same Qiskit target settings, with all 3,424 additional total public arithmetic/whole multiplier ideal emitted-gate cases passed across two arms. A source gate count INCREASE accompanies native cost reduction due to fewer CCX (Toffoli) and more cheaper CX (CNOT). Both public prefix carry and public threshold shortening were changed **TOGETHER**; no attribution of percent savings to one alone.

**Failed real-device gate still immutable:** best base2 case native **12,517 CZ and 32,312 depth**, respectively **15.65× and 16.16×** 800/2000 heuristic limits *for just ONE multiplier*. **ZERO QPU execution, free runtime or paid runtime consumed**. No whole four-round quantum circuit or practical factoring success was measured. Even the cube8 solitary multiplier remains slightly more expensive than base2 (CZ12,680 vs12,517); earlier cubic order r12→r4 gain arose in multiround public modular powers [2,4,16,11]→[8,29,1,1] making two rounds identity. Prior successful real IBM N15 phase-register recycling milestone and all negative N35 reports remain independently intact.

**Next stage:** compare comparator/carry optimization components separately under new frozen experimental protocols or design a shared-carry/uncompute network to eliminate repeated high-fan-in Toffoli controls. No automatic transition to a QPU or larger four-phase-bit Shor run until separate feasibility and public factor-production control gates pass.


## 2026-10-16 — Isolated prefix-carry vs public threshold-shortening ablation: four real-target compilations, clear attribution, positive cost interaction

**Research lead/attribution: Chase Lunsford / CaMaLabs.** Prior full public N35 controlled modulo35 primitive arithmetic with cached control passed 128/128 exact emitted-gate cases and full helper cleanup on both public base2 and cube8 (old native Fez target CZ18,719 /19,912; depth42,335 /44,381). The later two-component combined prefix carry+threshold-shortening optimization reached CZ12,517 /12,680, depth32,312 /33,138, but we could not honestly credit either component alone. [New frozen preregistration](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_PREREG.md), commit `79c1934c162b39c253597305cf42b3459738f0dd`, before scoring; 2 frozen components separately (prefix_only and threshold_only) × 2 bases (2,8) = **FOUR controlled native-target-only compiler jobs**, same Qiskit~=2.5.2, runtime~=0.47.0, Fez target, optimize1, seed8776, same 32 application qubits and cached enable logic. The public arithmetic full-residue multiplier `hardware/qrr_n35_prefix_threshold_component_ablation.py` uses no hidden order/factor/orbit.

[Original **4/4 successful GitHub Actions trial 39007742612**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007742612) **ZERO QPU**: every arm passed **16 distinct public modular constants ×(35 valid enabled+64 arbitrary disabled)=1584/1584 actual X/CX/CCX gate cases**, plus **128/128** full-control six-bit residue multiplier ideal gate outputs, invalid states identity, unchanged control and **all 25 ancillas returned zero**. Native ISA transpilation succeeded all four. [Independent untouched original artifact audit/preservation **39007830864**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007830864) **SUCCESS**, preserved original `results/ibm_shor35_prefix_threshold_ablation/qrr_n35_component_{prefix_only,threshold_only}_base{2,8}.json`; no re-execution of science, no device runtime. [Full method/result report](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_RESULT.md).

| Native Fez TARGET compilation; ONE controlled N35 multiplier | Cached reference base2 | Prefix ONLY base2 | Threshold ONLY base2 | Both base2 | Cached reference cube8 | Prefix ONLY cube8 | Threshold ONLY cube8 | Both cube8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Native CZ |18719|**14392**|18010|**12517**|19912|**14948**|19344|**12680**|
| Native depth |42335|**38007**|39868|**32312**|44381|**39590**|42472|**33138**|

**Attribution:** Prefix-carry-only saves native CZ **23.12% base2 /24.93% cube8**, while public-threshold-only saves **3.79% base2 /2.85% cube8**; both save native depth as well. **Nonadditive combined native cost residual**, `both - (prefix_only + threshold_only - reference)`, = **−1,166 CZ /−3,228 depth** for base2; **−1,700 CZ /−4,543 depth** for cube8. Hence retained full-combined original circuit beats naive sums of isolated improvements in this fixed compiler; no implication about physical hardware interference or universal/large-N performance. Primitive source counts can rise while native CZ falls due to large reduction in CCX and increase in CX. Original examples: prefix_only a2 1973 primitive (1085 CX/860 CCX/28X), threshold_only a2 1456 (421 CX/1007 CCX/28X), combined a2 1817 (1033 CX/756 CCX/28X).

**Engineering proof gate PASS four-for-four; immutable real device gate FAIL ALL.** Even previous best full combined **12,517 CZ /32,312 depth** is much larger than **800 CZ /2,000 depth**, so no full four-phase Shor test or IBM free/paid QPU run authorized. These were *read-only target* CPU compilations only, not actual device execution or new factoring progress. The genuinely measured IBM Fez real Open-only N15 phase recycling milestone remains independently true and recorded. N35 classically factors trivially.

**Next:** preserve both components in future verified baseline and attempt a preregistered reuse/shared-carry or modulo wrap reduction under the same X/CX/CCX + all-ancilla-clean gate-level test; address remaining native Toffoli synthesis cost before building four-phase Shor, with ZERO automatic QPU fallback.


## 2026-10-17 — N35 shared forward-carry/reverse-borrow uncompute: 8192+1584+128 true gate proofs pass; compiled native CZ 56% WORSE

**Research lead: Chase Lunsford / CaMaLabs.** Previous N35 full-register arithmetic trials had [verified best](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md) single public controlled modular multiplier costs on read-only `ibm_fez` native target **a2 CZ12517/depth32312**, cube a8 **CZ12680/depth33138**. Earlier independently [isolated prefix vs threshold optimization](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_RESULT.md) showed prefix-only much stronger than public threshold-only, and the combination favored. All remain beyond frozen real-QPU CZ<=800/depth<=2000 cutoff; no N35 QPU use.

The next proposed change was [frozen before results](QRR_N35_SHARED_CARRY_REUSE_PREREG.md), commit `c3b61efe87ab2ce6725e739a84c295a20777ab57`: compute **one reused clean enabled low-bit carry chain**, update all sum bits, **uncompute the stored carries from the updated output via reversible subtract-k borrow recurrence**, in the existing six clean carry bits rather than recalculating comparator for each sum bit. Exactly one candidate; same original public N35 one-multiplier cached-enable full-residue circuit, 32 application qubits, IBM Fez target read-only, Qiskit~=2.5.2/runtime~=0.47.0, opt1, seed8776, no private order or orbit, no synthetic eigenphase, and strictly NO real QPU submission.

Original new [zero-QPU two-arm CI **39060426103**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060426103): **2/2 SUCCESS as correct compiler/test execution**. Both base2 and cube8 passed **8192/8192** emitted X/CX/CCX conditional modulo64 addition cases (ALL 64 public constants×64 input states×2 control), independent **1584/1584** emitted-gate modulo35 add cases (16 public constants×99) and complete controlled-modmul **128/128** ideal emitted-gate basis input/control cases, with every **25 ancillary qubits clean** and invalid y>=35 identity. **This is a genuine arithmetic correctness gain for the candidate, NOT evidence of native resource gain.** [Independent unchanged original JSON verification/preservation **39060515347**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060515347) **SUCCESS**, archived `results/ibm_shor35_shared_carry_borrow/qrr_n35_shared_carry_borrow_base{2,8}.json` unchanged, with complete original CZ/depth/primitive gates, proofs, source provenance and no QPU. Full negative [result report](QRR_N35_SHARED_CARRY_REUSE_RESULT.md).

| Public N35 one multiplier, Fez CPU target only | Frozen old best | New shared carry | Change |
|---|---:|---:|---:|
| Original base2 native CZ | **12517** | **19552** | **+56.20% worse** |
| Original base2 native depth | **32312** | **42236** | **+30.71% worse** |
| Public cube8 native CZ | **12680** | **19895** | **+56.90% worse** |
| Public cube8 native depth | **33138** | **43075** | **+29.99% worse** |
| Original logical application qubits | 32 | 32 | unchanged |
| New candidate full ideal gate proofs | baseline prior PASS | **both 8192+1584+128 PASS** | no garbage |
| New real IBM QPU submissions | 0 | **0** | free/premium protected |

**Recorded negative engineering result:** The shared-carry forward-and-reverse cleanup works exactly, but its conditional carry/borrow network creates substantially MORE native two-qubit costs and depth on `ibm_fez` than repeated public carry-prefix comparators. Frozen **engineering improvement gate FAILED** for both arms; frozen **CZ<=800/depth<=2000 QPU gate FAILED** too. No real quantum runtime used. Preserve the old best combined prefix/threshold method, and treat this as verified falsification of the current sharing implementation rather than user-facing hardware progress. Do not weaken gates, rerun different seeds or silently promote an order-specific orbit toy as equivalent.

**Next fixed research question** should address public-constant arithmetic/condition complexity in a separate protocol; e.g. a purpose-built single-control Toffoli constant adder reducing the high-fan-in carry AND/OR chains or a special sparse public constant policy. Keep original real IBM Fez Open Plan N15 phase-recycling success intact and separate. No RSA-scale hardware factoring claim.


## 2026-10-17 — N35 disjoint public threshold-prefix comparator: all 42,672 true gate cases PASS but native CZ 74–79% WORSE

**Lead / attribution:** Chase Lunsford / CaMaLabs. Follow-up to previous N35 full-residue public prefix carry+shortened ripple benchmark and failed shared forward-carry/reverse-borrow implementation. The **verified best** before this study remains [base2 12517 native CZ / depth32312, cube8 12680 CZ / depth33138](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md) on IBM Fez **CPU native target compilation only**, with 32 logical source qubits/25 clean helpers and 128 correct emitted-gate input cases each. Our prior [shared-carry/borrow](QRR_N35_SHARED_CARRY_REUSE_RESULT.md) passed ideal gate correctness but compiled **56–57% worse**, so a truly new fixed comparator ablation was warranted.

**Frozen preregistration** [QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md](QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md), initial commit `c5c79510139d28ec8da4788ec0a13fc19f7fd054` before CPU scoring. **ONE explicit new method**, [`hardware/qrr_n35_disjoint_prefix_comparator_single_modmul.py`](../hardware/qrr_n35_disjoint_prefix_comparator_single_modmul.py), substitutes bit-prefix **disjoint public threshold minterms** for only the old ripple comparator. For each 1-bit of public threshold t, the source register x is below t if the first differing bit is zero and all higher x bits match t; these cases are mutually exclusive. Primitive X/CX/CCX multi-controlled XORs implement the predicate with temporary negative literal inversions immediately undone; trailing-zero public input shortening, original constant prefix carry arithmetic, cached enable, full modular multiplier and all uncomputation retained. No orbit, secret factors/order or synthetic eigenphase.

**First source CI [39070941123](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39070941123) reached a test assertion error only:** actual comparator 42,672 input cases vs prereg mistakenly counted 21,336; omitted factor 2 for checking both initial predicate flag states. No gate disagreement, native compilation or QPU submission. Exact [prereg and assertion-only correction](QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md) documented before successful native compilation; no algorithm changed. [Corrected experiment GitHub Actions **39071031851**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071031851) **2/2 SUCCESS**: actual direct emitted X/CX/CCX gate-basis comparator proofs **42,672/42,672 per base** (240 comparator circuits over width1–6, all public threshold values, geq/lt, enable0/1 and initial flag0/1), **16 public modular-add constants ×99 =1,584/1,584** source gate cases per base, full N35 six-bit residue+control multiplier **128/128** gate-basis cases per base, all **25 helper bits returned zero**, invalid residues/disabled inputs identity. Qiskit~=2.5.2/runtime~=0.47, live read-only IBM Fez target, opt1, transpiler seed8776, 32 source logical qubits, zero Sampler/Estimator. [Independent original-artifact audit+preservation CI **39071126315**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071126315) **SUCCESS**; original untouched output JSONs `results/ibm_shor35_disjoint_prefix_comparator/qrr_n35_disjoint_comparator_base{2,8}.json` committed. Full [verified report](QRR_N35_DISJOINT_PREFIX_COMPARATOR_RESULT.md).

| N35 single controlled multiplier, IBM Fez ISA TARGET ONLY | BEST original shortened ripple | NEW disjoint minterm | CZ increase |
|---|---:|---:|---:|
| Public base2 native CZ | **12,517** | **21,839** | **+74.47%** |
| Public base2 native depth | **32,312** | **49,751** | +53.97% |
| Public cube8 native CZ | **12,680** | **22,727** | **+79.24%** |
| Public cube8 native depth | **33,138** | **51,441** | +55.23% |
| Source logical qubits | 32 | 32 | none |
| Source primitive CCX base2/base8 | 756 / 778 | 1225 /1268 | more expensive multi-controls |
| Actual IBM QPU jobs | 0 | **0** | No free or paid runtime |

**RESEARCH NEGATIVE:** Completely correct minterm comparator is markedly WORSE on real backend ISA compiler costs than original public shortened-ripple comparator. Immutable engineering gate FAILED for both public arms; prior best is retained. Hardware gate **CZ<=800 native and depth<=2000** also failed by large margin even before assembling four QPE rounds, so **ZERO quantum device execution and ZERO Open/Paid Plan Runtime**. No real N35 factor measurement, practical cryptographic break, novel factoring theorem or hardware performance improvement. The original genuine N15 IBM Fez Open Plan phase recycling 49/64 vs wide 38/64 remains separately preserved.

**Next research gate:** If pursuing further optimization, isolate the cost of public constant modular correction or an alternative low-overhead Toffoli/control decomposition on one multiplier with a fresh frozen validation/provenance protocol. Preserve prior best and both rigorously negative shared-carry and disjoint comparator results; no automatic hardware job without strict verified Open Plan and feasible native circuit.


## 2026-10-17 — Verified new best N35 phase-exact relative-phase carry comparator: −26% native CZ / −33% depth; hardware gate still FAIL

**Attribution / research lead:** Chase Lunsford / CaMaLabs. Preserve the real IBM Fez Open Plan N15 recycled-phase-register Shor pilot independently (actual QPU, N15 factors; NOT a cubic preconditioning demonstration). N35 public a2/cube8 remains classically trivial, CPU-native-target preflight only; original phase-register recycling and public cubic observations are preserved separately.

**Frozen original best** immediately before this test: public full six-bit controlled modular multiplication with prefix-carry addition and public shortened-ripple unsigned comparator, one multiplier not four-bit Shor, 32 source logical qubits and 25 clean helpers, IBM Fez read-only target, Qiskit~=2.5.2/runtime~=0.47, opt1 seed8776; `results/ibm_shor35_public_prefix_carry/qrr_n35_public_prefix_carry_base{2,8}.json` verified native compiler base2 **12517 CZ/depth32312**, cube8 **12680 CZ/depth33138**, prior true basis proof 128/128.

**Scientifically important null before win:** [original prereg for relative-phase clean multi-control V-chain](QRR_N35_RELATIVE_PHASE_CLEAN_VCHAIN_PREREG.md). After a gate-name inverse test-harness repair, [CI original 39072419676](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072419676) passed **1022/1022 exact phase-aware clean local V-chain gates**, **1584/1584 phase-aware modular additions** and **128/128 phase-aware full multipliers**, but emitted **0 RCCX in either complete kernel**: earlier enable-control caching eliminated all control fan-in≥3. Compiled native CZ/depth were **exactly identical to original best**, engineering win FALSE, QPU gate FAIL. That source CI reported FAILURE due to deliberately requiring RCCX to appear in the full target, rather than misreporting the local correct but globally unused optimization as a win. [Independent original source-artifact null audit/preservation 39072844818](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072844818) SUCCESS, committed unchanged `results/ibm_shor35_relative_phase_vchain/qrr_n35_relative_phase_clean_vchain_base{2,8}.json`, no quantum runtime used.

**Distinct ONE-component prereg before scoring:** [`QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md`](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md), git **`bf8868224f565a8e9cfa9a98b384c192f0350369`**, fixes two public base arms, same modadd, valid predicate, 32 source qubits, same targets and seed, but substitutes **Qiskit relative-phase RCCX** for **temporary carry-compute CCX gates INSIDE the public shortened-ripple comparator** and uses exact RCCX inverse when uncomputing carry in reverse order, with semantic predicate output flag controlled by unchanged exact original `multi_x`. Never substitute a relative-phase gate for a semantic target flip. Qiskit named inverse `rccx` in this setting, so actual quantum `Operator` matrix is checked for inverse identity, not assumed based on naming.

The [new original source `hardware/qrr_n35_relative_phase_ripple_carry.py`](../hardware/qrr_n35_relative_phase_ripple_carry.py) interprets **ACTUAL emitted operator matrices** as monomial basis permuting amplitudes, multiplies **complex quantum phase** through every emitted X/CX/CCX/RCCX gate and requires final amplitude **+1** for EVERY tested clean-input basis state: standalone comparator **42,672/42,672**, each of 16 public modular-add constants over 35 enabled+64 disabled values **1,584/1,584 per base**, full N35 six-bit work input y=0..63 and control c=0,1 **128/128 per base**, original work/controls correct and all 25 helpers zero. Thus these are genuine ideal quantum-semantic phase-correctness tests, NOT just classical output truth tables and NOT physical gate fidelity.

[**Source original 2/2 zero-QPU CI 39072693905**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072693905) SUCCESS, read-only IBM Fez TARGET, fixed Qiskit versions, optimization1 seed8776, NO Sampler/Estimator/JOB, original source gate distributions **base2 {CX1033, RCCX596, X28, exact CCX160}, cube8 {CX1077, RCCX616, X28, exact CCX162}**; the compared old source exact CCX counts 756/778. [**Independent untouched original results audit+preservation CI 39072788179**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072788179) SUCCESS, committed original JSON under `results/ibm_shor35_relative_phase_ripple/qrr_n35_relative_phase_clean_vchain_base{2,8}.json` (folder and receipt revision distinguish it from the earlier V-chain null). Full [report](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md).

| One public N35 controlled multiplier, IBM Fez CPU TARGET only | Old verified best | NEW phase-exact comparator | Change |
|---|---:|---:|---:|
| Original base2 native CZ | 12,517 | **9,263** | **−26.00%** |
| Original base2 native depth | 32,312 | **21,772** | **−32.62%** |
| Cubic base8 native CZ | 12,680 | **9,426** | **−25.66%** |
| Cubic base8 native depth | 33,138 | **21,933** | **−33.81%** |
| Application logical qubits | 32 | **32** | unchanged |
| Phase-aware emitted-gate basis proof | prior bit-only PASS | **42,672 +1,584 +128 PER BASE exact complex +1 amplitude PASS** | true quantum phase proof |
| Actual IBM QPU jobs | 0 | **0** | strictly CPU-only |

**FROZEN ENGINEERING GATE PASSED 2/2:** clear matched same-target native CZ & depth reductions without relaxing clean-ancilla, full-residue or phase correctness, and 596/616 real RCCX gates are present in both full kernels, unlike the initial null intervention. **FROZEN HARDWARE GATE FAILED 2/2:** even smallest 9263 CZ and depth21772 still exceed 800CZ/2000depth by **11.58× and 10.89× respectively, for ONE multiplier only**. No IBM physical N35 test, Open Plan free hours or paid runtime. No generic factoring/cryptographic advantage claim, no complete four-QPE-round resource estimate from this single multiplier, and no asymptotic theorem. Existing full four-round public-cubic comparisons remain a separate scope.

**Next gate:** explore further phase-exact native comparator cost optimization with full direct complex-unitary proofs, or revisit four-bit QPE only if one-kernel resource path becomes technically credible; never weaken QPU thresholds or hardcode N35 multiplicative orbits. Preserve successful milestone alongside both original null/negative controls.
