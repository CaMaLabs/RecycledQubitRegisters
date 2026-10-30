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


## 2026-10-17 — RCCX active/enable cached controls: exact quantum phase proof PASS; base2 8542 CZ/19819 depth WIN, cube8 depth regression; engineering gate FAILED

**Research lead Chase Lunsford / CaMaLabs.** Continuation of phase-exact N35 full-six-bit work arithmetic. The previous independently verified [public shortened-ripple comparator RCCX temporary carry program](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) passed all full/coherent gate-phase checks and compiled native `ibm_fez` CPU target to **base2 9,263 CZ depth21,772 and cube8 9,426 CZ depth21,933**, same 32 logical source qubits, 25 clean helper qubits. Both N35 examples remain far beyond unchanged real-QPU feasibility CZ<=800/depth<=2000. The actual IBM Fez Open Plan N15 phase-recycling pilot remains a different, genuine QPU milestone, not evidence for public N35 cubic quantum factoring.

**Preregistered BEFORE scoring:** [`QRR_N35_RELATIVE_PHASE_CACHED_LATCH_PREREG.md`](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_PREREG.md), original commit `5537b57907162795ead8f64c74d21c3e0cda07ac`, freezes EXACT ONE new change: substitute Qiskit `RCCXGate()` and its ACTUAL inverse for the 26 standard source CCX gates comprising 2 `active=phase&valid` cached latch build/cleanup and 24 `enable=active&work[i]` build/cleanup across 6 forward+6 inverse modular weighted additions. Preserve original coherent semantic target gates, same public full-residue arithmetic/comparator RCCX carries, 32 application qubits, Qiskit~=2.5.2/runtime~=0.47.0, `ibm_fez` authenticated read-only target, opt1 seed8776, no extra seed/layout selection, no true order/factors/orbit injection, zero real QPU.

**Actual source gate quantum PHASE verification (each base):** [`hardware/qrr_n35_relative_phase_cached_latch.py`](../hardware/qrr_n35_relative_phase_cached_latch.py) extracts exact `Operator(inst.operation)` complex monomial basis mapping and requires final amplitude **+1** and exact output on **8/8** separate RCCX→controlled semantic CX→inverse latch cases, **42,672/42,672** untouched comparator phase-cases, **1,584/1,584** untouched public modulo35 adder phase-cases and **128/128** full controlled multiply y0..63×control0/1 phase-cases, with ALL 25 helpers returned zero. Exact local matrix inverse `Operator(RCCX.inverse())·Operator(RCCX)=I`. New source FULL RCCX actually increases **596→622** base2 and **616→642** cube8, with exact CCX decreasing **160→134** and **162→136**, proving the 26-latch intervention exercised.

[Original both-public-base source GitHub Actions CI **39074215604**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074215604) **2/2 SUCCESS** for tests, original pinned Fez CPU-native compiler and independent CI source JSON invariants. [Independent untouched ORIGINAL JSON artifact audit/preservation CI **39074317133**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074317133) **SUCCESS**, saved `results/ibm_shor35_phase_cached_latch/qrr_n35_phase_cached_latch_base{2,8}.json` EXACT original files. Full [report](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_RESULT.md).

| ONE N35 multiplier Fez CPU TARGET only | Frozen old phase-correct | New relative cached latch | Outcome |
|---|---:|---:|---:|
| Base2 native CZ | 9,263 | **8,542** | −7.78% GOOD |
| Base2 compiled depth | 21,772 | **19,819** | −8.97% GOOD |
| Cube8 native CZ | 9,426 | **9,328** | −1.04% GOOD |
| Cube8 compiled depth | **21,933** | 22,005 | +0.33% WORSE |
| Logical application qubits | 32 | 32 | unchanged |
| Complete emitted quantum phase proof | 128/128 +1 | 128/128 +1 | PASS |
| Real IBM QPU jobs | 0 | **0** | no Runtime |

**Correct strict interpretation:** the two-arm frozen engineering PASS requiring **BOTH** native CZ AND depth improvements for **BOTH bases FAILED** due to the cube8 depth regression, even though base2 is the new lowest-cost single kernel. All static/phase correctness controls PASSED. **Both immutable physical device gates FAIL:** even base2 8542 CZ and depth19819 remain 10.68× /9.91× frozen thresholds 800/2000, before any four-phase Shor QPE; zero QPU free/paid runtime, no N35 hardware factor recovery, no RSA-scale claims.

**Next objective:** isolate active-only vs enable-only RCCX substitutions as distinct fixed arms under a precommitted frozen A/B protocol, to determine which latch family drives the cube depth regression and whether one can pass the two-arm gate. Do NOT postselect a base, adjust frozen seed, relax device gate or hide this mixed result.


## 2026-10-17 — Isolated active-only vs enable-only relative-phase cached control: 4/4 exact phase proofs PASS; active-only two-base gate PASS

**Research lead Chase Lunsford / CaMaLabs.** Continue the previously independently verified phase-exact temporary comparator RCCX public N=35 whole 6-bit residue controlled modular multiplier. The frozen original **neither** cached-latch baseline remains same read-only `ibm_fez` Qiskit~=2.5.2/runtime~=0.47.0, opt1 seed8776, source width32 (25 clean auxiliaries), base2 native CZ **9263**, depth **21772**; cube8 CZ **9426**, depth **21933**. Previous [both active+enable RCCX cached latch study](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_RESULT.md) successfully replaced exactly 26 source CCXs and demonstrated base2 8542CZ/19819depth improvement, but cube8 native depth **WORSENED** from21933→22005 despite CZ9426→9328. Strict both-base engineering gate therefore failed; no QPU.

**Precommitted before new native scores:** [QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_PREREG.md](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_PREREG.md) original commit `ebbafc19911a073149d30c3728f9bdc70d8f5928`, exactly **four frozen arms** with unchanged public modular arithmetic, 32 qubits, original phase-aware comparator and uncached actual semantic output gates: base2/cube8 × (`active_only`, where 2 active-compute/erase CCXs are RCCX/inverse, OR `enable_only`, where 24 per-term enable-compute/erase CCXs are RCCX/inverse). Both/Neither baseline source receipts remain unchanged. No factors, precomputed orbits, true multiplicative order or secret data entered the circuit; fixed original CPU Fez target/seed/opt without extra tuning, and no physical IBM quantum Runtime use.

**Exact quantum-phase source proofs:** New [`hardware/qrr_n35_relative_phase_latch_families.py`](../hardware/qrr_n35_relative_phase_latch_families.py) interprets the actual emitted X/CX/CCX/RCCX operator matrices, including complex quantum phase, not a classical shadow: **8/8 local latch plus 42,672/42,672 comparator, 1584/1584 full controlled public modulo35 adder, and 128/128 complete controlled multiplier cases per arm**, exactly final +1 complex phase, full-residue enabled validity/invalid input identities, all 25 helpers cleaned. Relative RCCX source count changed exactly +2 (`active_only`) or+24 (`enable_only`) vs immutable comparator RCCX baseline, no accidental source gate changes. All 4 phase and native compiler audits PASSED in original [GitHub Actions CI **39074602823**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074602823). Independent [original source-result JSON audit/preservation CI **39074706319**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074706319) SUCCESS, committed four ORIGINAL unchanged `results/ibm_shor35_phase_latch_family_ablation/qrr_n35_{active_only,enable_only}_base{2,8}.json` output receipts. Full [report](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_RESULT.md).

| Public N35 one multiplier, IBM Fez native CPU TARGET only | Base2 native CZ | Base2 native depth | Cube8 native CZ | Cube8 native depth |
|---|---:|---:|---:|---:|
| Frozen previous comparator, neither latch RCCX | 9263 | 21772 | 9426 | 21933 |
| **active_only**: phase-exact 2 source latch RCCX | **9042** | **21541** | **9156** | **21820** |
| **enable_only**: phase-exact 24 source latch RCCX | 8756 | 21007 | 9424 | **21995** (WORSE) |
| Both: phase-exact 26 source latch RCCX | 8542 | 19819 | 9328 | **22005** (WORSE) |

**FROZEN active-only two-base engineering gate PASS:** a2 CZ−2.39% depth−1.06%, cube8 CZ−2.86% depth−0.52%, against original baseline, exact output quantum phases, no qubit/ancilla changes. **FROZEN enable-only two-base engineering gate FAIL:** cube8 depth worsens +62, even though base2 gains. The combined original gate also FAILED on cube8 depth, so isolate active-only as the correct conservative common kernel improvement, not arbitrarily cherry-picked base2. Single-seed compiler topology cost proxies only, not real measured hardware fidelity or an RSA-grade quantum algorithm.

**Physical hardware gate FAIL all arms:** even smallest 8542 CZ/19819 depth and active-only cube8 9156 CZ/21820 depth are greatly above unchanged CZ≤800/depth≤2000 limits for just ONE multiplier. Absolutely no new QPU shots, free/paid Runtime, real N35 factorization, multi-four-round Shor or practical cryptanalytic advantage claim. Preserve the original real IBM Fez N15 Open Plan phase recycling milestone independently. Next step could preregister multi-seed robustness before selecting preferred common kernel for full-scope compiler mapping, or explore reducing exact semantic Toffoli costs; never relax device-gate threshold or inject public-orbit hardcoding.


## 2026-10-17 — N35 active-only relative-phase control-latch 8-seed robustness FAIL: base2 5/8, cube8 1/8 paired native CZ/depth wins

**Lead / attribution: Chase Lunsford / CaMaLabs.** Previously [phase-aware relative-phase comparator carry](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) produced correctly interpreted quantum-phase+1 full-residue N35 one-controlled-multiplier native Fez target costs **base2 CZ9263/depth21772** and cube8 **CZ9426/depth21933**. [Active-only temporary phase-aware latch ablation](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_RESULT.md) independently proved base2 **CZ9042/depth21541** and cube8 **CZ9156/depth21820** at one frozen compiler seed8776 with 32 original logical qubits, 25 clean ancillas, 8 local RCCX probe+42672 comparator+1584 modular-add+128 full emitted-gate exact complex-phase cases per base. All were **CPU compilation against read-only IBM Fez native target metadata**, **ZERO real QPU free/paid Runtime**. Previous failed shared-carry, disjoint comparator and phase-v-chain null controls remain unchanged.

Preregistered BEFORE any new scores: [`QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_PREREG.md`](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_PREREG.md), original freeze git commit **`0836b38892e0069a718ec0e47d3a3567f3db29a0`**, exactly **8 transpiler seeds [11,37,101,409,8776,12011,20261,45673]** with fixed Qiskit~=2.5.2, IBM Runtime SDK~=0.47.0, read-only `ibm_fez` same backend target object, optimization1, paired source baseline `neither` and `active_only` per seed and base = **32 native CPU compiler runs**. Two independent jobs base2/cube8, no seed searching, no modified arithmetic, no true multiplicative order, precomputed orbit or private factors. **Frozen robustness acceptance: BOTH public bases ≥6/8 paired seeds with strictly improved CZ AND depth, negative median paired CZ/depth delta and exact previous 8776 anchor; device gate CZ≤800, depth≤2000 still separate and prohibitive.**

[New source `hardware/qrr_n35_active_only_multi_seed.py`](../hardware/qrr_n35_active_only_multi_seed.py) executed **before backend read** the true Qiskit-emitted quantum `Operator` complex-phase checks per base: local RCCX latch **8/8**, comparator **42,672/42,672**, modular adder **1584/1584**, original full controlled 6-bit multiplier `neither` **128/128**, phase RCCX `active_only` full controlled multiplier **128/128**. Outputs were public modulo35 for valid y, identity on invalid y and control0, exact final **+1 quantum phase** on every case, all 25 auxiliaries clean, source 32 logical qubits, only +2 RCCX/−2 exact CCX under active latch. Both original source jobs **successfully compiled all 32**, including reproducing seed8776 results byte-for-byte numerically (no target anchor drift). **Original [source GitHub Actions run 39080813622](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080813622) overall marked FAILURE due ONLY to a POSTCOMPILATION auditor dictionary typo**: auditor requested `device_feasible_active_only` but original source stored `device_feasible_active`. It uploaded both valid full `COMPILE_SUCCESS` original source-receipt artifacts; do not hide the failure or rerun seeds opportunistically.

[**Independent original-artifact audit/preservation GitHub Actions 39080960758**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080960758) **SUCCESS**, downloaded original source-run artifact files without a single new compiler call, verified original target native ops, all 32 exact CZ/depth pairs, all complex-phase and clean-helper proof receipts, all 8 seed timestamps/list in order, immutable old JSON controls, historical seed8776 match, predeclared robust gate/medians and failed QPU gate; committed original untouched JSONs at `results/ibm_shor35_active_only_multi_seed/qrr_n35_active_only_multiseed_base{2,8}.json`. Complete original seed table and honest provenance in [report](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md).

| Matched native-ISA CPU seed sensitivity, active-only minus original neither | Public base2 | Public cubic base8 |
|---|---:|---:|
| Exact matched seed pairs compiled | 8/8 | 8/8 |
| Native CZ strictly improved seeds | 6/8 | 2/8 |
| Native depth strictly improved seeds | 6/8 | 3/8 |
| **BOTH CZ and depth strictly improved in same seed** | **5/8** | **1/8** |
| Median paired native CZ delta | **−218.5** (favorable) | **+106.5** (WORSE) |
| Median paired native depth delta | **−541** (favorable) | **+346.5** (WORSE) |
| Frozen ≥6/8 jointly better and negative both median deltas | **FAIL** | **FAIL** |
| Frozen seed8776 old and new exact reproductions | **PASS** | **PASS** |
| CZ≤800 AND depth≤2000 QPU device preflight | **FAIL ALL EIGHT** | **FAIL ALL EIGHT** |
| Real IBM QPU jobs / free+paid runtime | **0** | **0** |

**Evidence/interpretation:** The previous seed8776 active-only improvement was real but **NOT ROBUST across seeds or both bases**. Favorable base2 medians are not enough: 5/8 joint improvements fail strict frozen 6/8; cube8 *median regression* and 1/8 joint improvement are particularly strong warnings against universal gate-cost claims or postselected placement. Compiler seed variability is NOT device-noise data or physical quantum reliability. Do not switch to a different seed, relax pass criteria or call this a quantum advantage. The original positive algorithmic and real N15 hardware records remain intact; keep comparator-only original as the reliable *common reference* and preserve conditional seed8776 active-only result.

**Next:** preregister future arithmetic/semantic phase-preserving optimizations with paired multiseed native-ISA comparisons from the outset, include at least both N35 public bases, and do not consider a full four-phase QPE QPU experiment until a separately credible physical feasibility gate and explicit active IBM Open Plan authorization.


## 2026-10-17 — N35 public bit/carry parity fusion: 8192 exact constant-adder quantum-gate cases PASS, but 8-seed two-base native robustness FAIL

**Research lead and attribution:** Chase Lunsford / CaMaLabs. The previous verified N35 public six-bit full-residue **single controlled multiplier** with phase-exact temporary comparator RCCX and old public high-to-low prefix carry addition, `hardware/qrr_n35_relative_phase_ripple_carry.py`, passed all actual emitted complex-phase gate tests, used 32 logical qubits with all 25 auxiliaries cleaned, and compiled on the IBM Fez native CPU target (Qiskit~=2.5.2 / runtime~=0.47, opt1 seed8776) at **base2 CZ9263/depth21772**, **cubic base8 CZ9426/depth21933**. The later isolated active latch had attractive seed8776 results but [rigorous eight-seed audit](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) found **NOT robust** (5/8 base2,1/8 cube8 paired joint CZ/depth wins). The real N15 IBM Open Plan QPU phase recycling experiment remains separate; ALL N35 experiments herein are read-only Fez target **CPU native transpilation, ZERO real QPU jobs or paid/open quantum runtime**.

**Frozen prior to scoring** new [`QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_PREREG.md`](QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_PREREG.md) git **`b516cff92d3786504069f513f5bb4f7f999f4657`**, one component only: in the existing public conditional `+k mod64` six-bit arithmetic, when bit j of public k is set AND lower public bits of k are nonzero, the old output bit toggles by `1 XOR [carry>=t]`; replace two controlled XOR flips with **ONE** controlled `carry<t` comparator XOR via unchanged phase-exact public threshold predicate `geq=False`. All other bit/carry situations unchanged. The original comparator-only `neither` reference built first; patch only `best.constant_add_from_prefix_carry` for new candidate, preserving same original `verified.build(base)`, N35 complete six-bit work state, cached controls, full modular wrap, RCCX phase-correct temporary predicate carry and 32-source-qubit/25 clean auxiliary widths. The source is [`hardware/qrr_n35_fused_constant_carry_multiseed.py`](../hardware/qrr_n35_fused_constant_carry_multiseed.py). Neither real order/factors nor precomputed orbits enter the circuit.

**Actual emitted quantum `Operator` complex-amplitude phase/ancilla proof PASS before backend read** per base: **8,192/8,192** six-bit controlled public constant additions for ALL k0..63, x0..63 and enable0/1, all carry/scratch clean, final complex amplitude+1; **42,672/42,672** original public comparator cases; **1,584/1,584** 16 public modulo35 additions (35 enabled valid+64 disabled arbitrary per k), both full comparator-only **128/128** and modified fused **128/128** public controlled 6-bit multiply inputs, every 25 auxiliary qubits clean and final phase+1. Source intervention genuinely used: original base2 source CX1033→**982** (−51), X28→**130** (+102); cube8 CX1077→**1022** (−55), X28→**138** (+110); source RCCX596/616 and exact CCX160/162 unchanged. Fewer source CX do NOT entail fewer native CZ/depth.

**Preregistered robust comparison across exact same eight seeds `11,37,101,409,8776,12011,20261,45673`** with matched old/new per seed and base = **32 complete native IBM Fez TARGET CPU compilations**. Source jobs [**39082263845**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082263845) **2/2 SUCCESS**, both original per-job independent scientific audits passed (unlike earlier audit-key typo), all seed rows archived. Old `neither` seed8776 EXACTLY reproduced previous original base2 CZ9263/depth21772 and cubic8 CZ9426/depth21933 (target comparability PASS). [Independent source artifact audit/preservation CI **39082382115**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082382115) SUCCESS, downloaded original source-job JSONs **without rerunning science**, verified all 32 matched metrics, all semantic exact-phase checks, immutable baseline and predeclared failure, then committed UNCHANGED original receipts `results/ibm_shor35_fused_constant_carry_multiseed/qrr_n35_fused_constant_carry_base{2,8}.json`. Full [report with ALL EIGHT paired-seed rows each](QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_RESULT.md).

| Original `neither` vs fused public arithmetic, 8 paired CPU native Fez seeds | base2 | cubic base8 |
|---|---:|---:|
| Matched 8/8 source/candidate seed compiles | 8 pairs | 8 pairs |
| Source CX removed | **51** | **55** |
| Source extra X (temporary comparison inversions) | +102 | +110 |
| Native CZ lower in individual seeds | 4/8 | 6/8 |
| Native depth lower in individual seeds | 5/8 | 3/8 |
| **Native CZ AND depth jointly lower in same seed** | **3/8** | **2/8** |
| Median paired native CZ delta (candidate−original) | **−31** | **−169** |
| Median paired native depth delta | **−15** | **+170.5 (worse)** |
| Frozen ≥6/8 joint-wins and both median deltas negative | **FAIL** | **FAIL** |
| Exact archived historical old seed8776 native CZ/depth | PASS | PASS |
| CZ≤800 AND depth≤2000 hardware feasibility | FAIL all 8 | FAIL all 8 |
| Actual IBM QPU jobs / Open+paid Runtime use | **0** | **0** |

**VERIFIED NEGATIVE ROBUSTNESS:** Public constant bit/carry fusion is EXACTLY reversible and coherent ideal arithmetic on all tested clean-input computational basis states; removes 51/55 semantic CX but **fails** strictly preregistered placement-robust multi-seed gate on BOTH base2 and cube8, with cubic depth **median regression**. Although old seed8776 individual new values base2 CZ8906/depth21167 and cube8 CZ9261/depth21876 improve, these are not robust and must not be promoted after viewing seed scores. Original source+receiver receipts and this negative ablation remain part of CaMaLabs history. No actual N35 QPU, no full four-round Shor, no factor measurement or cryptographic quantum advantage. Existing immutable device heuristic CZ≤800/depth≤2000 exceeded on every one of 32 compiled one-multiplier circuits; hardware remains PROHIBITED for this experiment.

**Next disciplined step:** consider more substantive public-constant modular-correction arithmetic methods or controlled-Toffoli reductions with fixed matched two-base multi-seed benchmarks and exact quantum-phase (not bit-only) proofs before compilation; retain current verified phase-aware comparator `neither` as the common clean baseline. Preserve original N15 real Open Plan demonstration separately, no paid fallback.


## 2026-10-17 — Eight-seed original workflow closure: postcompile audit fixed; green 2/2 rerun exactly reproduces 32/32 negative robustness results

**Chase Lunsford / CaMaLabs attribution.** Follow-up on the original fixed active-only N35 eight-matched-seed, two-public-base, phase-exact CPU IBM Fez **TARGET** experiment and independently verified **negative** robustness gate; [full original and reconciliation result report](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md). Initial source run [39080813622](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080813622) completed all 32 science compilations and exact source quantum operator proofs, saving original JSON, but was marked RED when a downstream audit referenced the nonexistent `device_feasible_active_only` field rather than the source's actual `device_feasible_active` field. The [original independent immutable-source-artifact verification 39080960758](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080960758) had already proved the measured negative finding without recompilation. The historical red run and its original JSON remain preserved.

**End-to-end cleanup now COMPLETE:** GitHub [commit `d9cfe355e9c54f0f55298edf7f93395af1097a28`](https://github.com/CaMaLabs/RecycledQubitRegisters/commit/d9cfe355e9c54f0f55298edf7f93395af1097a28) fixes ONLY the postcompilation receipt-schema lookup (`tag=="active_only"` maps to `device_feasible_active`; neither maps to `device_feasible_neither`), no algorithm, seed, backend, layout, quantum-phase check, physical device cutoff or compiler configuration changes. [Corrected FULL two-base GitHub Actions workflow **39084396945**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084396945) **2/2 GREEN SUCCESS** including all exact source phase oracle checks and **32 new matched Fez native CPU target compilations** and independent same-job postcompile invariants. All 8 seed-pair results PER base reproduce the original CZ/depth numbers and the old seed8776 anchor.

[Separate new independent original-rerun-artifact reconciliation **39084519756**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084519756) **SUCCESS**, downloaded original fresh green source-run receipts, independently checked **32/32 CZ/depth and complete Fez ISA native `count_ops`, gate size, width** against the previously archived first-run receipts, verified entire source-phase proof equality, all 8 seeds and frozen acceptance calculations. It retained new exact source JSONs under `results/ibm_shor35_active_only_multi_seed_green_rerun_39084396945/`, including `rerun_vs_prior_independent_audit.json` with SHA-256 digests/per-seed same-native-metrics evidence. This independent verification did **NOT** do another compilation. Original red sources are NOT overwritten.

**Final scientific conclusion UNCHANGED:** baseline vs active-only 8 paired seeds, **base2 5/8**, **cubic base8 1/8** jointly lower native CZ AND depth; frozen >=6/8 for BOTH bases FAIL. Base2 median paired CZ -218.5 and depth -541; cube8 medians +106.5 CZ and +346.5 depth (regression). Hardware CZ<=800 AND depth<=2000 FAILS every circuit. **ZERO QPU jobs, Open free/paid quantum runtime or shots**. This newly green end-to-end CI is a workflow repair and independent reproducibility confirmation, NOT a newly successful robust optimization, quantum hardware measurement, full QPE result, or cryptographic advantage.


## 2026-10-17 — Verified N35 public OR-carry phase-exact eight matched seeds: 8/8 CZ wins each base, but cubic 5/8 joint robustness fails

**Research lead/originating work:** Chase Lunsford / CaMaLabs. New public N35 full six-bit register one controlled modular multiplication engineering test. Reuses independently proven [relative-phase temporary carry comparator](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) and original complete work/acc + source latch unitary, with real complex-amplitude **+1** clean-ancilla gate proofs, against IBM Fez **CPU-only native hardware TARGET** compilation. Prior verified baseline 8776 base2 **CZ9263/depth21772**, public cubic8 **CZ9426/depth21933**, all 25 helpers clean, 32 logical qubits; original source JSON remains unchanged. Previous single-seed active-only latch improvement was **not** robust at 8 fixed seeds: base2 5/8, cube8 1/8 strict both-metric wins; all previous negative/null outcomes remain preserved. The original real IBM N15 Open Plan phase-register recycling pilot is separate; N35 here is not a real QPU/factoring run.

**Freeze before new computation:** [`QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_PREREG.md`](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_PREREG.md) initial git **`51f7fa7cbeb72c83ac03f3f90dcbedb763a81eea`**, exactly one public arithmetic source change and EXACT eight matched seeds `[11,37,101,409,8776,12011,20261,45673]`, both public bases, same read-only `ibm_fez` target metadata within each job, `qiskit~=2.5.2` / `qiskit-ibm-runtime~=0.47.0` optimization level1, original vs candidate seed-paired, no seed/layout tuning. Preregistered robust gate requires **BOTH bases ≥6/8 matched seed pairs strictly lower in BOTH native CZ/depth**, negative median paired deltas, exact 8776 historical anchor. Separate **frozen real hardware preflight CZ≤800 AND depth≤2000** and strict ZERO QPU job policy.

New [`hardware/qrr_n35_or_carry_multi_seed.py`](../hardware/qrr_n35_or_carry_multi_seed.py) replaces ONLY public `b_i=1` comparator carry `x OR prev = x XOR prev XOR (x AND prev)` (**two CX + RCCX**) with exact Boolean `x OR prev = prev XOR (x AND NOT prev)` (**one CX + two temporary X on previous carry + RCCX**) during carry construction and literal **reverse actual RCCX adjoint** on cleanup. The public threshold, full 6-bit work arithmetic, invalid code identity, cached-control layout, source-register width, semantic target CCX, phase-aware comparator register and modular correction remain unchanged; no order, secret factors, precomputed orbit or private oracle. The actual new source is **base2 171 rewritten carry steps**, CX1033→**691**, X28→**712**, RCCX596 unchanged, CCX160 unchanged; cube8 **180 steps**, CX1077→**717**, X28→**748**, RCCX616 unchanged, CCX162 unchanged. All modified OR sites genuinely exercised on whole arithmetic.

**Mandatory source proof BEFORE backend read:** 4 public Boolean identity input checks and actual Qiskit RCCX inverse matrix identity, per public-base **42,672/42,672 actual emitted-gate comparator complex amplitude phase+1 cases**, **1,584/1,584 mod35 public constant addition cases** from all16 distinct public constants, **128/128 original full six-bit controlled multiplier cases and 128/128 new full cases**, correct modular work for all64 six-bit residues/control bits, invalid/disabled identity, control unchanged, **all25 helper qubits zero**, exact output quantum amplitude **+1** in every case. The interpreter follows actual `Operator(inst.operation)` matrices; this is a source coherent ideal quantum-unitary basis validation, not just a classical truth-table and NOT noisy-QPU fidelity.

[**Original two-arm 2/2 successful GitHub Actions 39095494407**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095494407) compiled all **32** native CPU Fez target circuits (8×2 bases×2 candidates), complete source phases, and original detailed CI audit successfully. [**Independent original-artifact audit/preservation CI 39095605020**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095605020) **SUCCESS**, downloaded original source run JSON files rather than recompiling, checked original 32 resource pairs, exact old seed8776 controls, all complex-phase proofs/seed stats and frozen physical gate, and committed **unchanged source JSON** receipts `results/ibm_shor35_or_carry_multi_seed/qrr_n35_or_carry_multiseed_base{2,8}.json`. Full [public result and every paired-seed table](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md).

| Eight matched seed pairs, candidate minus original same target | Base2 | Public cubic8 |
|---|---:|---:|
| **Native CZ strictly lower** | **8/8** | **8/8** |
| Native depth strictly lower | 6/8 | 5/8 |
| **BOTH CZ and depth strictly lower on same seed** | **6/8** | **5/8** |
| Median paired native CZ delta | **−359** | **−277** |
| Median paired native depth delta | **−419** | **−278.5** |
| Frozen ≥6/8 strict same-seed joint win | **PASS** | **FAIL** |
| Exact historical seed8776 original native compiler costs | **PASS** | **PASS** |
| New original seed8776 native CZ/depth | **8311 / 19981** | **9141 / 21528** |
| Hardware CZ≤800 AND depth≤2000 | **FAIL every seed** | **FAIL every seed** |
| Real IBM QPU/free+paid Runtime consumed | **ZERO** | **ZERO** |

**FROZEN TWO-BASE ROBUST ENGINEERING GATE FAILS** because cube8 only improves both CZ and depth in 5/8 seeds, one below 6/8; do NOT call this two-base robust simply because *all 16* matched paired CZ counts improved (a useful narrower finding) and median depth improved in each. Base2 6/8 joint pass. 8776 candidate costs are valid matched CPU resource improvements, with new base2 CZ8311 (lower than old independently verified two-latch CZ8542), but new native depth19981 still higher than that older two-latch depth19819; no claim of universal Pareto gain. Cubic depth occasionally regresses up to +637, base2 up to +554. Original Qiskit placement seeds influence compiled topology but do not measure device readout/gate noise.

**Unchanged REAL QPU gate FAIL** at least an order of magnitude: even best base2 new 8311CZ/depth19981 vs old preflight 800CZ/2000depth for ONE multiplier, and none of 32 actual native CPU circuits satisfy. N35 not run on QPU, no QPU shots, paid runtime, free runtime, factor recovery, RSA/ML-KEM impact, full four-QPE-bit protocol, novel factoring algorithm or general quantum speedup. Preserve completed positive and negative results with CaMaLabs attribution, and investigate further **paired seed phase-safe arithmetic topology** rather than selecting favorable compiler seeds.


## 2026-10-17 — N35 ZERO-CX De Morgan temporary OR comparator: exact phase 8/8 matched two-base native CZ+depth wins; real-QPU gate still FAIL

**Research lead / original work Chase Lunsford / CaMaLabs.** The latest separately [independently audited one-CX OR-carry N35 public comparator](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md) previously produced **8/8 paired native CZ reductions** per base, but **base8 only 5/8 joint native CZ+depth wins**, FAILING the frozen >=6/8 two-base matched-seed robust gate. Keep old original comparator-only source `hardware/qrr_n35_relative_phase_ripple_carry.py` and previous one-CX source `hardware/qrr_n35_or_carry_multi_seed.py` unchanged, along with previous negative shared-carry/fused-carry/disjoint comparator and null control-latch receipts; preserve the real IBM Fez Open Plan N15 recycled-phase-register demonstration as a separate real QPU finding (not cubic preconditioning).

**New hypothesis preregistration [`QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_PREREG.md`](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_PREREG.md)** was committed **BEFORE** results in git **`7aa1940b277e895e93932a45a119a6bd28a3d630`**. ONE public comparator carry re-synthesis: replace `OR(x,p) = p XOR (x AND NOT p)`, using a CX+temporary phase RCCX, with **De Morgan `OR(x,p) = 1 XOR (NOT x AND NOT p)`**, emitting **NO source CX** on public OR carry steps, 5 X around one RCCX compute and exact inverse for uncompute. All other public N35 six-bit full-residue controlled multiplication, exact semantic target flips, threshold shortening, constant adder, temporary active/enable controls, 32 source logical qubits and 25 returned-zero ancillas unchanged. No injected orders, private factors, hardcoded orbit, or input-conditioned truth table.

[New source `hardware/qrr_n35_demorgan_zero_cx_or_multiseed.py`](../hardware/qrr_n35_demorgan_zero_cx_or_multiseed.py) first proved the Boolean identity 4/4 and true Qiskit RCCX operator inverse, then **ACTUAL emitted Qiskit complex-amplitude unitary gate interpretation BEFORE backend read**: unsigned comparator **42,672/42,672** every threshold/width/flag/control, public mod35 additions **1,584/1,584** for all 16 constant k, full public controlled N35 multipliers **128/128 EACH for THREE variants** (original, old one-CX OR, new zero-CX De Morgan). All work and controls correct, source operand semantics valid, **all 25 helpers returned zero**, quantum final phase **+1** on every clean-input basis test. Emitted source base2: 171 OR steps, one-CX→DeMorgan CX691→**349** / X712→**1,738**, RCCX596/CCX160 unchanged; cube8: 180 OR steps, CX717→**357** / X748→**1,828**, RCCX616/CCX162 unchanged. All three sources width32.

**48 authenticated IBM Fez native TARGET CPU compilations, no actual device execution:** 2 public bases×8 preregistered integer transpiler seeds `[11,37,101,409,8776,12011,20261,45673]`×3 exact candidate circuits (original/oneCX/new), Qiskit~=2.5.2, runtime~=0.47.0 SDK, optimizer1, same native backend target snapshot within each job. **New phase-safe zero-CX circuit improves BOTH native CZ and depth against the immediately previous one-CX comparator in ALL 8/8 matched seeds for EACH public base; it ALSO improves both vs old original in 8/8 per base** (16/16 matched JOINT CZ+depth wins vs each reference). Old original and previous one-CX exact historical seed8776 anchors match.

| IBM Fez CPU-native N35 ONE controlled multiplier metric | Original base2 | Prior oneCX base2 | **NEW De Morgan base2** | Original cubic8 | Prior oneCX cubic8 | **NEW De Morgan cubic8** |
|---|---:|---:|---:|---:|---:|---:|
| Seed8776 native CZ | 9,263 | 8,311 | **7,993** | 9,426 | 9,141 | **8,758** |
| Seed8776 native depth | 21,772 | 19,981 | **18,604** | 21,933 | 21,528 | **20,575** |
| Joint matched seed CZ & depth wins vs prior oneCX | — | — | **8/8** | — | — | **8/8** |
| Median paired CZ new−oneCX (8 fixed seeds) | — | — | **−318** | — | — | **−326** |
| Median paired depth new−oneCX | — | — | **−1,262** | — | — | **−1,287** |
| Source qubits / helper bits clean | 32/25 | 32/25 | **32/25** | 32/25 | 32/25 | **32/25** |
| Real IBM QPU jobs, any runtime | 0 | 0 | **0** | 0 | 0 | **0** |

**FROZEN TWO-BASE ENGINEERING ROBUSTNESS: PASS (8/8 joint in each arm; ≥6/8 required, both medians negative, all proofs passed).** Compared to immutable original seed8776: base2 native CZ **−13.71%**, depth **−14.55%**; cube8 CZ **−7.09%**, depth **−6.19%**. Additional compared with immediately prior one-CX: base2 CZ−3.83%/depth−6.89%; cube8 CZ−4.19%/depth−4.43%. Seedwise original tables in [full independently audited report](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md).

**Provenance without obscuring CI:** Original [source experiment CI **39096222447**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39096222447) completed all exact phase checks and all 48 CPU-native ISAs successfully, uploaded original `COMPILE_SUCCESS` result JSON; GitHub overall marked FAILURE **only** due downstream auditor key typo `demorgan_zero_cx_full_multiplier_phase_proof` instead of actual `demorgan_full_multiplier_phase_proof`. No physics/circuit gate failure, original failed audit preserved. Separate [independent original-artifact verification and byte-preserving archive CI **39096402446**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39096402446) **SUCCESS**, rechecked original input proof, all seed-pair counts and old original/OR artifact numeric anchors, saved exact untouched `results/ibm_shor35_demorgan_zero_cx_or/qrr_n35_demorgan_zero_cx_base{2,8}.json` with no recompile.

**QPU feasibility still unequivocally FAILS** on ALL 48 native CPU target compiles. The best new observed CZ7,993/depth18,604 remains **~9.99× CZ and ~9.30× depth** the immutable N35 single-multiplier preflight **CZ≤800/depth≤2000**, and a full four-QPE-bit Shor circuit has NOT been assembled/tested from this kernel. **Zero IBM QPU jobs, zero free runtime and zero paid runtime**, no real N35 factoring evidence, crypto break or quantum speedup. This is a verified controlled native circuit **compiler optimization** under one target/SDK version and 8 seeds, not a general theorem or noise-fidelity observation.

**Next research target:** Use this *robust two-base* De Morgan comparator as the new candidate baseline; preregister honest matched multi-seed comparison of further public modular correction / exact semantic Toffoli reductions with exact complex-phase tests, no QPU submission before hard cutoffs and new authorization.


## 2026-10-17/18 — N35 source-bit negated OR-carry comparator: exact phase, robust 8/8 and6/8 vs original; De Morgan remains preferred

**Research lead / attribution:** Chase Lunsford / CaMaLabs. Real IBM N15 Open Plan phase-register-recycling experiment remains an independent measured tiny factoring pilot, not a public cubic-order-reduction QPU result. N35 arithmetic here is fully public, 32 source logical qubits, 25 initially clean/returned-clean auxiliary, no factors/order/orbit hardcoded, one controlled multiplier only. **ALL IBM Fez results are read-only target metadata for CPU compilation; ZERO real quantum jobs, free Open Plan Runtime, or paid runtime**. Prior [phase-exact relative-comparator best](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) native fixed seed8776 costs base2 **CZ9263/depth21772**, cubic base8 **CZ9426/depth21933**. [Temporary active latch multiseed](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) FAILED robust two-base gate (5/8,1/8). Both prior [one-CX OR-carry](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md) and independently verified [zero-CX De Morgan OR-carry](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) source results were already in the repository and remain intact, with De Morgan showing strong 8/8 both-resource wins for both public bases.

**Preregistration frozen before source run:** [QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_PREREG.md](QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_PREREG.md) commit **`c4032f83db9e91d0986a16ab545f6f9465bcad20`**. A distinct one-CX public threshold-complement bit1 OR-carry Boolean identity `x OR p = x XOR (~x AND p)` implements compute with `CX(x,cur); X(x); RCCX(x,p,cur); X(x)` and exact reverse `X(x); RCCX.inverse(x,p,cur); X(x); CX(x,cur)`, instead of the previous one-CX candidate which inverted prior p. No semantic target or public prefix-carry/modular correction change; full comparator clean-carry unitary requires **complex amplitude phase +1**, not merely a Boolean mapping. The [original source `hardware/qrr_n35_or_carry_polarity_matched_seeds.py`](../hardware/qrr_n35_or_carry_polarity_matched_seeds.py) independently proved BOTH ORIGINAL and NEW **42,672/42,672** emitted-gate comparator cases and **1,584/1,584** modulo35 constant-adder cases and **128/128** full controlled multiplier cases **PER BASE PER DESIGN**, all 25 ancillas zero, phase +1, identity on invalid y or disabled control, application width32. Source base2 CX1033→691, X28→712, RCCX596 and CCX160 unchanged; cube8 CX1077→717, X28→748, RCCX616 and CCX162 unchanged. Exactly public 171/180 OR-carry steps source optimized. Qiskit native target optimization1, pinned qiskit~=2.5.2/runtime~=0.47.0, prereg eight matched seeds `[11,37,101,409,8776,12011,20261,45673]`; **32 actual CPU target compiles**.

[Original source GitHub Actions **39099579484**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099579484) **2/2 SUCCESS**, including source quantum-phase proofs, 32 native compiles and per-source audit. [Separate independent original artifact preservation audit **39099703212**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099703212) **SUCCESS**, fetched immutable original artifact JSON, verified all 32 gate counts/depths, pre-registered seed list, phase proof receipts, frozen baselines, exact old seed8776 reproduction and 8/8 +6/8 joint tests WITHOUT new science re-run; committed original unmodified `results/ibm_shor35_or_carry_polarity_seeds/qrr_n35_or_carry_polarity_base{2,8}.json`. Full eight rows and honest independent study in [result](QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_RESULT.md).

| New source-X negated OR carry versus matching ORIGINAL comparator source, Fez CPU target | Public base2 | Public cubic8 |
|---|---:|---:|
| Exactly matched transpiler seeds | 8/8 | 8/8 |
| Joint native CZ AND depth improvements | **8/8** | **6/8** |
| Median paired native CZ delta candidate−original | **−464.5** | **−311.5** |
| Median paired native depth delta candidate−original | **−1362** | **−1053.5** |
| Source old seed8776 exact reproduced | YES | YES |
| Seed8776 new native CZ/depth | **8945 /20616** | **9104 /20762** |
| Strict prereg 6/8 plus negative medians gate | **PASS** | **PASS** |
| Native CZ<=800 AND depth<=2000 device gate | **FAIL ALL** | **FAIL ALL** |
| Actual QPU jobs / Open or paid runtime | **0** | **0** |

**Engineering result:** legitimate two-base **ROBUST improvement relative to original baseline**, with phase/ancilla exactness and 32 source compiles, BUT it does NOT displace the stronger independently verified zero-CX De Morgan design: seed8776 [De Morgan](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) original phase-exact CPU target costs **base2 CZ7993/depth18604** and cube8 **CZ8758/depth20575**, each lower than this source-X one-CX variant at that seed, and De Morgan recorded 8/8 joint matched savings vs earlier one-CX candidate on both bases. No direct single-run three-arm comparator study is claimed here beyond archived independent experiments.

**Hardware gate unchanged and FAILED** for every new source circuit, still many thousands native CZ and depth tens thousands for ONE controlled N35 modmul. No real hardware N35 QPE/factor test, RSA cryptanalysis or practical quantum advantage. **Next:** use De Morgan as a new frozen common strong baseline and test phase-correct active-only latch *as a separate eight-seed paired intervention*, or explore public controlled constant arithmetic with exact phase and hardware gates held fixed. Preserve positive/negative/null prior original records.


## 2026-10-17/18 — De Morgan plus active-only temporary RCCX latch: exact quantum phase PASS, two-base seed robustness FAIL (3/8, 5/8)

**Research lead / attribution:** Chase Lunsford / CaMaLabs. Following the independently [phase-aware De Morgan zero-CX OR carry](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md), strongest validated dual-public-base architecture (8/8 native CZ+depth joint wins vs previous one-CX OR on BOTH bases, source exact complex phase+1, all helper bits clean), we froze a [new eight-seed matched active-only cached latch ablation](QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_PREREG.md), prereg original git **`47a6a1d80b704df7469795127f2c9ba69fffdae9`** BEFORE compiler results. Separate older [active-only multiseed study](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) failed both-base robust gate; this new one tests the **interaction with De Morgan**. All tests here: N=35 public bases2/cube8, ONE six-bit full-residue controlled multiplier, 32 source qubits/25 clean ancillas, Qiskit~=2.5.2/runtime~=0.47.0, read-only authenticated IBM Fez native TARGET on CPU, optimization1, exactly fixed seeds `[11,37,101,409,8776,12011,20261,45673]`, **ZERO physical QPU jobs, shots, paid or Open/free runtime**.

ONE source intervention: keep De Morgan public comparator/carry, constant prefix adder, modular correction, public validity check, work/acc swap, semantic target flips and 24 cached enable latch CCX exactly unchanged. Convert ONLY 2 temporary `active = phase AND valid` cache latch CCX calls to `RCCXGate()` and its EXACT inverse. Source operator distributions: base2 old `{CX349,RCCX596,X1738,CCX160}`→new `{CX349,RCCX598,X1738,CCX158}`; cube8 `{CX357,RCCX616,X1828,CCX162}`→`{CX357,RCCX618,X1828,CCX160}`. The source [`hardware/qrr_n35_demorgan_active_latch_matched_seeds.py`](../hardware/qrr_n35_demorgan_active_latch_matched_seeds.py) uses actual `Operator(inst.operation)` quantum monomial amplitudes, demanding exact output complex phase **+1**, correct public six-bit residue behavior and zero scratch. Before target READ, per base: **4/4 Boolean De Morgan identities and RCCX actual inverse matrix**, **8/8 local active controlled-probe phase checks**, **42,672/42,672 comparator cases**, **1,584/1,584 public modular addition cases**, **128/128 original AND128/128 active-only complete multiplier cases**, every one of all **25 helper qubits returned ZERO**, correct invalid/disabled identity and coherent ideal source mapping.

[Original source GitHub Actions run **39100095129**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100095129) **2/2 SUCCESS**, all phase checks and **32 native Fez CPU target compiles** complete; old historical seed8776 source baseline exactly reproduced original independently preserved De Morgan CPU measurements. [Independent original artifact audit/preservation **39100203559**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100203559) **SUCCESS**, copied the two original 8-seed raw JSON receipts WITHOUT rerunning, independently checked every numeric cost/source phase proof, all frozen paired seeds and hardware gates, committed `results/ibm_shor35_demorgan_active_only/qrr_n35_demorgan_active_only_base{2,8}.json`. Full seed-by-seed scientific report [QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_RESULT.md](QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_RESULT.md).

| Matched Fez native CPU target, 8 De Morgan old vs +2 active cache RCCX | Public base2 | Public cubic base8 |
|---|---:|---:|
| Total paired seeds | 8/8 | 8/8 |
| **BOTH CZ and depth strictly improve same seed** | **3/8** | **5/8** |
| CZ-only improvement seed count | 5/8 | 6/8 |
| Depth-only improvement seed count | 3/8 | 5/8 |
| Median paired CZ delta new-old | **−138** | **−131** |
| Median paired depth delta new-old | **+112.5** (WORSE) | **−379** |
| Original historical seed8776 exact reproduced | YES | YES |
| Original De Morgan seed8776 CZ/depth | 7993 /18604 | 8758 /20575 |
| Candidate +active seed8776 CZ/depth | **8225 /19554** (WORSE) | **8036 /19202** (better ONE layout) |
| Frozen ≥6/8 both-win and both negative-median engineering gate | **FAIL** | **FAIL** |
| Frozen hardware CZ≤800 AND depth≤2000 | **FAIL ALL** | **FAIL ALL** |
| Actual IBM QPU jobs / paid/free runtime | **0** | **0** |

**Scientifically rigorous negative combination:** the attractive cubic seed8776 saving **CZ−722/depth−1373** cannot justify a robust 2-base architecture upgrade, because cubic only 5/8 joint wins, base2 only3/8 with median depth regression, and earlier controls already warned about seed-sensitive cached active variants. Preserve valid seed8776 conditional outcome but keep **original De Morgan-only phase-exact comparator** as strongest pre-registered two-base robust design under fixed eight-seed CPU compiler evidence; no hardware execution claim. Single register N35 remains classically trivial; these gate-cost resource proxies do not demonstrate real factoring, new theorem, or cryptanalytic quantum advantage. Immutable CZ≤800/depth≤2000 still far above actual compiled output even for one multiplier, so **strict zero QPU**.


## 2026-10-18 — Verified 2-base 8-seed robust N35 public single-bit carry bypass: 8/8 base2 + 7/8 cubic8 joint wins, 46 source CX eliminated, zero QPU

**Research lead / originating program:** Chase Lunsford / CaMaLabs. All N35 quantum cost results below are authenticated **READ-ONLY IBM Fez native hardware-target CPU transpilation**, NEVER physical quantum device runs. Genuine prior N15 IBM Fez Open Plan recycled phase-qubit factoring experiment is separately preserved and is NOT a demonstration of N35 cubic order reduction. The N35 test remains ONE six-bit full-residue reversible controlled multiplier a2/cube8, not four-round quantum phase estimation, RSA cryptanalysis, practical quantum advantage or a new factoring theorem.

**Baseline selection:** The strongest independently verified prior 8-seed TWO-BASE robust comparator is [phase-exact De Morgan zero-CNOT OR ripple carry](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md), with source 32 logical qubits/25 clean auxiliaries. Old original at seed8776 base2 **CZ7993/depth18604** and cube8 **CZ8758/depth20575**; old original source `CX349/RCCX596/X1738/CCX160` base2 and `CX357/RCCX616/X1828/CCX162` cube8. Prior [DeMorgan plus phase RCCX active-only latch](QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_RESULT.md) had only 3/8 base2 and5/8 cubic joint native CZ/depth improvements, FAILED frozen two-base robustness. Our new test does NOT use that favorable isolated cubic8776 or a weak original ripple as reference.

[Frozen BEFORE new scoring](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_PREREG.md), original commit **`57d884d65a9c425794ee7fd6459afc54213d0224`**, exactly same public a2 and cube8, eight integer compiler seeds **[11,37,101,409,8776,12011,20261,45673]**, Qiskit~=2.5.2/IBM SDK~=0.47, read-only Fez target, opt1, exact source truth/complex quantum-phase and 32 logical/25 cleaned helper invariants, 6/8 **joint native CZ AND depth strictly lower** required for BOTH bases, plus negative median paired CZ/depth and exact historical8776 anchor; immutable physical heuristic CZ<=800/depth<=2000, zero-QPU under all circumstances.

**ONE new public constant-specific arithmetic identity**, in [`hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py`](../hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py): while computing controlled `+v mod64` descending from highest output bit j to lowest, the lower j bits are UNCHANGED. Generic carry comparison is `x_low_j >= 2^j - (v mod 2^j)`. If the known PUBLIC value `v mod 2^j == 2^(j-1)`, this comparator is simply **original source bit x[j−1]**. Replace computing/uncomputing its 1-bit flag and two CNOT with **unchanged exact `multi_x(controls+[x[j−1]],target[j])`**. All other De Morgan/RCCX/adjoint temp carries, valid/work/acc/controls/inverse and public modular arithmetic identical. Exactly **23 public-constant bypasses** in EACH a2/cube8 one-multiplier full circuit: **46 source CX gates eliminated** without changing X, exact CCX or RCCX counts, register width, public validity behavior, all 25 scratch zero or source quantum phase.

**ACTUAL emitted quantum operator proof BEFORE touching IBM target** (2 independent jobs): **320** public constant/low-source bit algebra identity cases across all 64 possible v and all j1..5 where shortcut qualifies; **4** Boolean De Morgan identities+true `RCCX.inverse()*RCCX=identity` operator; **42,672/42,672** unchanged De Morgan comparator actual Qiskit X/CX/CCX/RCCX complex-phase cases, all threshold widths/polarities/control and original flag states, carries zero; **1,584/1,584** public modulo35 modular-add exact source phase cases EACH for old AND new; **128/128** full 6-bit controlled multiplier exact output and **final complex amplitude +1** EACH for old AND new for both bases, including invalid y>=35 identity and disabled control0, every one of **25 helpers clean**. Source counts baseline a2 CX349→new303, cube8 CX357→new311, exact source RCCX/CCX/X unchanged. Mapping therefore coherent on tested clean-ancilla subspace in ideal circuit model, NOT measured noise fidelity. Both original seed8776 numeric anchors EXACTLY reproduce previously archived same-native target results; all 32 native CPU compiles (8 seeds ×2 public bases ×2 designs) succeeded with independent result self-audit.

[Original successful 2/2 source-run CI **39105116012**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105116012) and [independent original artifact audit/permanent original-result preservation **39105265764**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105265764) are BOTH **SUCCESS**. Independent archival fetched unaltered native source-run artifact JSONs, checked all 32 original CZ/depth numbers, complex+1 phase proof, source 23 bypasses/46 CNOT, 8776 anchor, frozen 6/8 gate and physical failure; **never reran compiler or arithmetic**. Two unchanged original result JSONs now under `results/ibm_shor35_one_bit_carry_bypass_multiseed/qrr_n35_one_bit_carry_bypass_base{2,8}.json`. Full [16-row matched seed table](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md) available.

| N35 matched read-only Fez native CPU target compiler, candidate minus SAME-SEED robust De Morgan baseline | Public base2 | Public cubic8 |
|---|---:|---:|
| Matched fixed eight-seed full kernel pairs | 8/8 | 8/8 |
| Strict native CZ lower seeds | 8/8 | 8/8 |
| Strict compiled depth lower seeds | 8/8 | 7/8 |
| **BOTH CZ and depth lower on same seed** | **8/8** | **7/8** |
| Median paired signed CZ delta | **−352.5** | **−341** |
| Median paired signed native depth delta | **−911** | **−1448** |
| Full original seed8776 CZ/depth | 7993 /18604 | 8758 /20575 |
| Full candidate seed8776 CZ/depth | **7887 /18221** | **7802 /18449** |
| Strict prereg ≥6/8 TWO-resource both-base robustness | **PASS** | **PASS** |
| Real IBM native CZ≤800 and depth≤2000 | **FAIL all 8** | **FAIL all 8** |
| Actual IBM QPU jobs, free/paid quantum Runtime | **0** | **0** |

**Honest cubic regression preserved:** seed409 cubic8 improves CZ 8222→8156 but worsens depth 19715→19775 (**+60**). Thus **7/8 not 8/8 joint**, and the report includes ALL eight seeds instead of cherry-picking best. The source CX change is identical 46 for both bases; observed CZ/depth changes vary significantly with target mapping. At seed8776 base2 7993→7887 CZ (−1.33%) and depth18604→18221 (−2.06%); cube8 8758→7802 CZ (−10.92%) and depth20575→18449 (−10.33%), but these are just one of eight frozen layouts.

**FROZEN TWO-BASE ENGINEERING ROBUSTNESS GATE PASSED** (8/8 base2, 7/8 cubic8, both paired medians negative; unchanged exact hardware source and anchors). Mark this a reproducibly favorable source-level public constant-adder simplification relative to the previously strongest robust De Morgan comparator **for this public toy N35 and fixed Qiskit backend target**, without extrapolating to an asymptotic factoring speedup, physical fidelity or private RSA scales. **SEPARATE HARDWARE GATE FAILED ALL 32**: even the lowest observed candidate native CZ base2 **7676** and cube8 **7604**, depth base2 **18220** and cubic **18449**, far exceed CZ800/depth2000 even before full four QPE rounds. **ZERO IBM Fez real N35 jobs, free/paid runtime or live factor recovery**. Preserve real N15 hardware milestone separately.

**Next research step:** retain this exact verified robust De Morgan+public one-bit carry bypass as a new public CPU gate engineering baseline; preregister any further constant-specific arithmetic/control-fusion optimization and compare eight identical source/target seed pairs BEFORE scoring, with full operator phase+1, all helper cleanup and two-base strict gate, no QPU without separate explicit authorization and feasible complete QPE circuit.


## 2026-10-18 — Signed public constant correction: phase-exact robust base2 8/8 matched CZ+depth wins, cube8 4/8 and two-base gate FAIL

**Lead / attribution:** Chase Lunsford / CaMaLabs. Preserve previous real IBM Fez N15 Open-only phase-register-recycling result as independent genuine hardware milestone (NOT a public cubic order reduction demonstration). The subsequent N35 public base2 and cubic8 controlled modular multiplier resource sequence remains **zero-QPU IBM Fez TARGET CPU compilation only**, one full-six-bit residue controlled multiplier PER base, not a full four-QPE-round factoring run or cryptographic quantum advantage. All previous positive, null and negative reports remain unchanged.

**Important actual checkpoint discovered at intake:** Since the prior conversation, [`QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md`](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md) had become the latest **two-base eight-seed-ROBUST best**: De Morgan zero-CX relative-phase clean comparator carries, public one-bit carry bypass eliminating 46 source CX /23 original redundant comparisons, all 25 helper qubits clean and exact output complex phase+1 on complete 6-bit work/control input space. Source code `hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py`; independently audited old JSON `results/ibm_shor35_one_bit_carry_bypass_multiseed/qrr_n35_one_bit_carry_bypass_base{2,8}.json`. At historical seed8776 old **base2 CZ7887/depth18221**, old **cube8 CZ7802/depth18449**; 8/8 base2 and7/8 cube8 strict native CZ&depth joint wins against earlier De Morgan baseline across seeds [11,37,101,409,8776,12011,20261,45673]. We **did not** revert to previous active-latch 5/8,1/8 nonrobust reference.

**New preregistration BEFORE any new score:** [`QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_PREREG.md`](QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_PREREG.md), frozen initial git commit **`5879cfba912a066c46c299dbd632cbfcb19293e0`** and pre-compilation existing historical cube8 anchor clarified `d50556e63f7f1128d85c558566014f2070349963`. Only ONE alternative public modular-adder representation: for `k≤17`, retain best original `+k` then flagged `−35`; for `k≥18`, publicly set `d=35−k` and use clean `flag=(enable & x<d)`, controlled `−d mod64`, flagged `+35 mod64`, then uncompute flag with `enable & final_x≥35−d`. No public/private factoring oracle, true period, group orbit hardcoding or additional qubits. Both a2 and cube8 include exactly **seven** high-k conditional additions and five unchanged additions. Source `hardware/qrr_n35_signed_constant_correction_multiseed.py` imports original one-bit/De Morgan source and uses same genuine 32 logical qubits/25 clean helpers. **Hard device preflight unchanged CZ≤800 AND depth≤2000, no hardware submission permitted**. Eight fixed matched compiler seeds/opt1/Fez target and strict 6/8 joint two-metric gate for BOTH public bases.

[**Original two-arm native CPU-source run 39108692489**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108692489) **2/2 SUCCESS**, same pinned Qiskit~=2.5.2/runtime~=0.47.0, each arm FIRST passed **3366/3366** classical public signed modadd/clean-flag identities across all k1..34, **42672/42672** ACTUAL emitted `Operator(gate)` phase-aware comparator cases, **1584/1584** direct original AND signed modular-add emitted-gate cases each, and **128/128** complete original AND signed full six-bit public multiplier inputs each, output complex amplitude exactly **+1** and all 25 helpers returned zero; same source width32, correct identity control0/invalid y≥35. All target read/CPU compilation AFTER semantic checks, no Sampler/Estimator/real IBM device job. Original source emitted gates:
- Base2 prior `CX303/RCCX596/X1738/CCX160` → signed `CX292/RCCX556/X1608/CCX155`.
- Cube8 prior `CX311/RCCX616/X1828/CCX162` → signed `CX315/RCCX608/X1788/CCX163`. Source structure reduction is markedly more favorable on base2.

**Every original eight-seed matched ISA CPU compile (32 original outputs):**

| Signed variant MINUS identical-seed existing robust one-bit source | Public base2 | Cubic base8 |
|---|---:|---:|
| Seeds with strictly lower native CZ | **8/8** | **5/8** |
| Seeds with strictly lower native depth | **8/8** | **4/8** |
| Both CZ AND depth strictly lower in same seed | **8/8** | **4/8** |
| Median paired CZ change | **−394** | **−80** |
| Median paired depth change | **−1133** | **−173.5** |
| Worst paired CZ REGRESSION | none, maximum delta **−34** | **+713** |
| Worst paired depth REGRESSION | none, maximum delta **−697** | **+820** |
| Historical seed8776 original anchored exactly? | **YES** | **YES** |
| Seed8776 original CZ/depth | 7887 /18221 | 7802 /18449 |
| Seed8776 signed CZ/depth | **7345 /16858** | **8199 /19269** |
| Frozen per-base ≥6/8 joint wins + negative medians | **PASS** | **FAIL** |
| Real-QPU feasibility CZ≤800 & depth≤2000 | **FAIL all seeds** | **FAIL all seeds** |
| IBM real QPU jobs/free+paid runtime | **0** | **0** |

**Scientific result:** public signed correction is robustly better **only on base2 (8/8 joint two-metric wins)**; cubic8 is NONROBUST 4/8 and notably regresses at seed8776 CZ +397, depth +820. The **PREDECLARED BOTH-base engineering gate FAILS**. A positive base2 arithmetic ablation may be retained separately, but cannot be promoted to a two-base generic cost gain or full cubic Shor advantage. Compiler seed placement remains sensitive, and native gate counts are target-CPU resource proxies, not real quantum hardware noise/fidelity/period-finding data. No actual N35 factoring/QPU shots or RSA/ML-KEM implications.

[**Independent original-source JSON audit+archive 39108827186**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108827186) **SUCCESS**: downloaded original run artifacts (no re-experiment) and checked 32 exact native CZ/depth pairs against original log, whole source quantum-phase proofs, unchanged robust one-bit references for all eight seeds, signed branch count 7, frozen seed8776 anchor, medians and strict positive/negative two-base feasibility; committed original untouched JSON `results/ibm_shor35_signed_constant_correction/qrr_n35_signed_correction_base{2,8}.json`. Full honest seed-by-seed study in [result report](QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_RESULT.md).

**Next proposed research gate:** Rather than base-dependent ad-hoc sign selection or lucky single seed, design an explicitly public, *operation-local* source-cost deterministic rule selecting either signed or original representation per k, freeze it independent of backend outputs, then compare both public bases against untouched 8-seed robust one-bit source with exact emitted-gate complex-phase proofs and strict matched 6/8 two-metric criterion. Do not auto-submit QPU even for promising CPU gains; unchanged 800/2000 single-kernel preflight still fails by a large factor.


## 2026-10-19 — N35 public source-only signed modular correction selector: 8/8 matched native CZ AND depth wins per base, phase-exact, zero QPU

**Lead / original research program: Chase Lunsford / CaMaLabs.** Existing independently preserved public six-bit N35 phase-exact one-bit carry bypass + De Morgan zero-CX comparator remains the scientifically fair **strong two-base robust ORIGINAL reference**, original eight-seed per-base receipts under `results/ibm_shor35_one_bit_carry_bypass_multiseed/`, seed8776 IBM Fez ISA target CPU cost **base2 native CZ7887/depth18221; cube8 CZ7802/depth18449**, 32 source logical qubits and all 25 helpers clean. True N15 real IBM Open Plan recycled-phase pilot is separate; N35 classical trivial factor 5×7 remains hardware **no-go** under fixed CZ≤800/depth≤2000 heuristic.

Last [signed k>17 correction attempt](QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_RESULT.md) passed source quantum-phase correctness but had 8/8 base2 and **only 4/8 cube8** matched CZ+depth wins. This new protocol did NOT change the base to that weaker signed version or cherry-pick favorable seeds. [Original preregistration](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_PREREG.md) initial commit **`9292116e31aefa6e2309c03a32488835ea55bdeb`** before target scoring, commits to **ONE public operation-local deterministic gate-cost selector**: for each 34 possible public nonzero add constants k, synthesize both original positive correction and mathematically equivalent signed underflow correction using the same verified relative-phase and public one-bit carry methods, then calculate Qiskit *SOURCE-ONLY* two-qubit proxy **S = CX + 6×CCX + 3×RCCX** (X cost0). Choose signed if and ONLY if strict S_signed<S_positive; ties positive. Entire 34×2 source-gate cost table frozen and computed BEFORE IBM backend read; no base, true multiplicative order, factors, input orbit, optimizer seed, QPU backend metadata, or real hardware cost consulted.

**Observed source-rule result (no post-result tuning):** signed for ALL odd public k1..33, positive for ALL even k2..34, the SAME mapping on both public full multipliers. Base2 uses **six** of twelve weighted signed corrections, cube8 **seven** of twelve; all actual source gates counted and preserved. Quantum-operator actual complex amplitude interpreter, BEFORE backend read, **PASSED per public base**: **3366/3366** arithmetic/underflow cleanup identities across all k and valid/disabled x; unchanged standalone comparator **42672/42672** emitted-gate complex +1 cases; **6732/6732** actual *both* positive/signed public modadd emitter/complex-phase cases (34×2×99); **128/128 original AND 128/128 new** six-bit controlled full-residue multiplier basis cases, phase+1 and all 25 helper qubits returned zero. **32 logical source qubits unchanged**. Actual full kernel emitted gate source base2 old {CX303,RCCX596,X1738,CCX160}→new **{CX275,RCCX520,X1508,CCX148}**, cube8 old {CX311,RCCX616,X1828,CCX162}→new **{CX284,RCCX538,X1528,CCX151}**.

[**Source experiment GitHub Actions 39367204317**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367204317) **2/2 SUCCESS**, Qiskit~=2.5.2/runtime~=0.47 native read-only `ibm_fez` target, optimizer1, same original eight fixed matched seeds **[11,37,101,409,8776,12011,20261,45673]** ×2 public bases×two kernel versions=**32 true CPU native compiler runs**, no QPU. Same previous original baseline read-only target seed8776 reproduced EXACTLY. [**Independent original-artifact audit and preservation CI 39367462324**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367462324) **SUCCESS**, downloaded and verified actual original unchanged JSONs for 34 gate choices, all original source operator semantic proof counts, **32 exact native CZ+depth/count_ops**, each original eight-seed base matched to preceding one-bit-bypass archived results, 8776 anchors and frozen hardware fail, and committed untouched original JSON bytes under `results/ibm_shor35_static_gate_sign_selector/qrr_n35_static_sign_selector_base{2,8}.json`. Full [report with ALL original paired-seed rows](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md).

| IBM Fez CPU TARGET, one public full six-bit N35 controlled multiplier | Old strong robust base2 | NEW base2 | Old strong robust cubic8 | NEW cubic8 |
|---|---:|---:|---:|---:|
| Fixed seed8776 CZ | 7887 | **6871 (−12.88%)** | 7802 | **7315 (−6.24%)** |
| Fixed seed8776 native depth | 18221 | **16626 (−8.75%)** | 18449 | **16286 (−11.72%)** |
| **Strict native CZ AND depth jointly better paired seeds** | - | **8/8 PASS** | - | **8/8 PASS** |
| Median paired CZ (candidate−original) | - | **−703.5** | - | **−766.5** |
| Median paired depth (candidate−original) | - | **−2148** | - | **−2341** |
| Application logical qubits / clean auxiliaries | 32 / 25 | **32 / 25** | 32 / 25 | **32 / 25** |
| QPU feasibility CZ≤800 and depth≤2000 | FAIL | **FAIL** | FAIL | **FAIL** |
| Quantum hardware jobs / free or paid IBM Runtime | 0 | **0** | 0 | **0** |

**Predeclared two-base engineering gate VERIFIED PASS (8/8 each):** strong full-emitted-operator ideal +1 quantum phase proofs, genuine public SOURCE-only deterministic selection, no unauthorized order/orbit shortcuts, same strong baseline, two public bases, negative paired medians and entire fixed seed list. The eight seed IDs were already used in earlier research, so this does not prove generalization to fresh unseen placements, versions or actual device noise. **Separate true-QPU feasibility gate STILL FAILS ALL 32 native CPU compiles** by order-of-magnitude margins (one kernel still 6871+ CZ and depth16000+), before full Shor QPE; ZERO real Open/paid hardware runtime. No novel theorem, practical quantum factorization or RSA-scale speedup. This is an engineering resource reduction, not a real quantum shot result.

**Recommended next falsification:** retain this new exact original positive milestone and run a separately preregistered **fresh held-out transpiler seed cohort**, using same frozen 34-k map/weights, phase oracle, CPU ISA target and original one-bit reference. Avoid tuning any weights, base, seed or compiler after checking score; never promote device use without actual free/Open Plan verification, original user authorization, and full device feasibility.


## 2026-10-19 — N35 source-only public sign selector FRESH seed holdout independently confirms 8/8 base2 and 7/8 cube8 paired native wins, zero QPU

**Lead/original research: Chase Lunsford / CaMaLabs.** First preserve as separate positive milestone the [34-public-k SOURCE-only weighted two-qubit cost sign selector original 8-seed research](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md), original frozen protocol/JSON unchanged: choose signed-vs-original correction for every public k1..34 by **Qiskit SOURCE-only S = CX + 6CCX + 3RCCX** (ties original) before Fez target read, selecting signed all odd k, original positive all even k. Both public a2 and cube8 full 6-bit residue controlled ONE-modular-multiplier outputs keep 32 source logical qubits, all25 auxiliaries clean, no group order/orbit/factor shortcut. Original development cohort [11,37,101,409,8776,12011,20261,45673] yielded **8/8 strict native CZ AND depth wins each base** against independently preserved original robust De Morgan 1-bit bypass, Qiskit2.5.2/runtime0.47 Fez native target CPU compile opt1. Old vs new seed8776 a2 **CZ7887/depth18221→CZ6871/depth16626**, cubic8 **CZ7802/depth18449→CZ7315/depth16286**. Previous fixed high-k signed correction was a true cube8 4/8 negative and remains preserved; N15 actual Open Plan QPU recycled phase pilot separate.

**Fresh independent falsification:** [preregistered fresh 8-seed holdout protocol](QRR_N35_STATIC_GATE_SIGN_FRESH_SEED_HOLDOUT_PREREG.md), frozen **`f1ad7917459fe43f0106662d0ec214d7a103b903`** BEFORE any new outcome, exact fresh seeds **[1729,3137,5003,7919,10103,13007,20011,31799]**, disjoint from eight original development seeds, with old seed8776 separately compiled as an ANCHOR that does NOT count in fresh median or 6/8 win score. SAME untouched source-algorithm and public gate weight choice; BEFORE backend read verify **ALL 34 signed/positive gate count vectors/proxy scores and signed choices identical** to independently archived originals, same original/candidate full source gate distributions, public inputs all 64 residues and controls, **3,366 signed arithmetic identity +42,672 actual comparator phase +6,732 actual both per-k source operator complex-phase +128 original full multiplier +128 candidate full multiplier quantum phase+1 checks PER BASE**; every source auxiliary clean25. These tests all PASSED without target compiler information; both source circuits unchanged 32 qubits, no order/factors/precompiled subgroup oracle.

[Original fresh-holdout experiment GitHub Actions **39368270962**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39368270962) **2/2 SUCCESS**: source proof passed first, then READ-ONLY `ibm_fez` target native ISA CPU compilation, **9 seed pairs per base×2 bases×2 source circuits =36 CPU compilations**, optimization1/Qiskit SDK same, 8776 old+selected EXACT historical anchor reproduced. No IBM quantum processor job, Sampler, Estimator or paid/free Runtime. [Independent original-artifact audit/preservation CI **39368456367**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39368456367) **SUCCESS**, fetched actual original source-run JSONs without rerunning science, independently verified **36 exact original native CZ/depth/count_ops, full phase proofs and source table equality, frozen eight fresh seeds, separate anchor and physical gate**, committed original untouched JSON to `results/ibm_shor35_static_sign_selector_fresh_holdout/qrr_n35_static_sign_fresh_holdout_base{2,8}.json`. Full [original fresh holdout report and all pairs](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md).

| FRESH eight-seed matched native IBM Fez CPU source-only public N35 sign selection | Base2 | Public cubic base8 |
|---|---:|---:|
| **Strict lower CZ AND depth in SAME FRESH seed** | **8/8 PASS** | **7/8 PASS** |
| Fresh native CZ improved | 8/8 | 7/8 (one equal CZ) |
| Fresh native depth improved | 8/8 | 8/8 |
| Median candidate−original native CZ | **−1,075** | **−798.5** |
| Median candidate−original native depth | **−2,891.5** | **−2,389.5** |
| Fresh prereg ≥6/8 + both negative medians | **PASS** | **PASS** |
| 8776 archive source+target anchor (separate from holdout) | **PASS** | **PASS** |
| Source quantum phase and 25 clean aux | **PASS** | **PASS** |
| Native CZ≤800 AND depth≤2000 REAL QPU preflight | **FAIL ALL** | **FAIL ALL** |
| Real IBM QPU jobs and any free/paid Quantum Runtime | **0** | **0** |

**Important negative seed kept:** cubic8 FRESH seed13007 old native **CZ7507/depth18257**, selected **CZ7507/depth17149**: depth improved, **CZ exactly equal**, so predeclared TWO-resource strict win correctly **FALSE**, yielding 7/8 rather than falsely claiming 8/8. ALL OTHER fresh paired seed outcomes improve both. **Combined old+fresh distinct transpiler seed cohorts:** base2 16/16 and cube8 15/16 native strict matched joint wins at one SDK/Fez target, not statistically independent real hardware trials.

**Conclusion:** Unchanged public deterministic 34-k sign choice now provides stronger native compiler placement robustness on the stated old and fresh seed cohorts than any previous static N35 arithmetic candidate, with all operator amplitudes +1 and clean-ancilla proofs preserved. It remains a quantum *ISA RESOURCE* engineering advance, NOT an asymptotic factoring theorem, cryptanalysis breakthrough, whole-four-QPE-stage N35 Shor run, or live quantum-device performance. Every one of all 36 CPU native compiled individual multipliers STILL violates immutable 800 CZ/2000 depth feasibility by many-fold. Strict **ZERO real Open/paid QPU use**. Preserve current verified new-best native/holdout milestone before exploring further public modular-correction structural optimization. Real N15 Open Plan phase-recycling pilot remains independently attributed and preserved.

**Next scientific direction:** use this frozen exact-phase/full-residue source selector as baseline for a preregistered truly new arithmetic lowering that removes a full modular comparator/conditional correction network or reduces live helper count, or test another public modulus under a fair generic source protocol. Test matched **new seed holdouts from the outset**; do NOT tune public source weights from Fez compiler score and do NOT attempt full QPU unless separately expressly authorized with verified Open Plan and native feasibility.


## 2026-10-19 — N35 complement-conjugated public constant inner adder: 16,384 source quantum cases PASS, but 1/8 matched Fez native wins per base (robust engineering FAIL)

**Research lead / original program: Chase Lunsford / CaMaLabs.** The latest old source was NOT the earlier 9k or 12k native CZ kernel; the independently verified [N35 public operation-local source sign selector](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md), validated again on [eight FRESH seed holdouts](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md) (8/8 both-metric wins base2, 7/8 cube8), with immutable seed8776 one-multiplier original base2 **6871 CZ/depth16626**, cubic8 **7315 CZ/depth16286**. Old k1..34 positive-versus-signed source-only map `S=CX+6CCX+3RCCX` (X unweighted, ties positive) remains unchanged and archived. All experiment costs are IBM Fez TARGET native **CPU compiler** outputs, not QPU runs, shot fidelity or real N35 factoring. Original real IBM Open Plan N15 phase recycling milestone independently preserved.

**New preregistration froze source method, seeds and acceptance BEFORE compilation:** [`QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_PREREG.md`](QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_PREREG.md), git `0c28980f7d507feebcece395cfd17bf63095dee4`. New source `hardware/qrr_n35_complement_constant_source_selector.py` proposes literal bit complement **`C(x)=63-x`** around the original one-bit-bypass controlled `-v mod64` adder, using `C(C(x)-v)=x+v mod64` on ALL public 6-bit x and both source enables; no change to outer modulo35 wrap/underflow correction, source-k positive/signed map, comparator, cached controls, 32 application qubits, 25 clean auxiliaries, multipliers a2/cube8 or precomputed orbit/order/private factors. For each publicly known mod64 `v=0..63`, source-only Qiskit gate count S chooses conjugation iff strictly cheaper than original direct (ties/zero direct), independently of compiler, target, base and residual x.

**BEFORE Fez target read**, both independent jobs rigorously verified actual Qiskit-emitted complex-phase `Operator` semantics: **16,384/16,384** direct and conjugated `+v mod64` six-bit enabled/disabled basis cases, every carry/scratch clean and final complex amplitude+1; **3,366** public arithmetic identities; old De Morgan comparator **42,672/42,672** signed/flag/control/threshold phase+1; old and newly re-encoded **6,732/6,732** each whole public-k positive+signed controlled modulo35 adder basis cases; both original AND candidate complete controlled multiplier **128/128** six-bit work×control basis cases each public arm, all 25 helpers clean, exact complex phase+1. Source-k decision and all 34 source proxy vectors exactly matched original archived receipts, meaning no post-hoc switching. Public v-source selector selected conjugation on **27 public constants [15,23,27,28,29,30,31,39,43,44,45,46,47,48,51,52,53,54,55,56,57,58,59,60,61,62,63]**; it was ACTUALLY used **12 of 24** inner add calls base2 and **10/24** cubic8, not a null intervention. Full source vectors CX **275→255** base2 and **284→267** cube8, RCCX/CCX unchanged, source X **1508→1392** and **1528→1428**; still 32 source qubits, all auxiliaries zero.

**Fixed native seeds (no post-result selection):** new eight **[43,127,211,887,1597,3571,8017,25013]**, disjoint from prior development+independent holdout, plus historical **8776 anchor excluded from robust numerator**. Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, read-only `ibm_fez`, optimization1, same target/seed within each previous-strong-source-vs-new-source pair; **36 total CPU native ISA compiles**. [**Original two-base source run 39376281237**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39376281237) **2/2 SUCCESS**, all source complex-unitary and full native count audits PASS; original source-run JSONs independently recovered and **byte-preserved by [CI 39376484723](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39376484723), SUCCESS, NO recompilation** at `results/ibm_shor35_complement_constant_selector/qrr_n35_complement_constant_selector_base{2,8}.json`. Full [report with EVERY matched seed and native metric](QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_RESULT.md).

| Frozen FRESH native placement comparison, candidate minus original latest BEST selected source | Public base2 | Cubic base8 |
|---|---:|---:|
| 8 new-seed ORIGINAL/CANDIDATE matched pairs | 8/8 | 8/8 |
| Strict joint native CZ AND depth improvements | **1/8** | **1/8** |
| CZ-only strict improvements | 3/8 | 2/8 |
| Depth-only strict improvements | 1/8 | 2/8 |
| Median paired native CZ delta | **+133** WORSE | **+56.5** WORSE |
| Median paired native depth delta | **+345** WORSE | **+432** WORSE |
| Original seed8776 old CZ/depth exactly reproduced | **6871/16626 PASS** | **7315/16286 PASS** |
| Seed8776 candidate CZ/depth (anchor not scored) | 6809/16088 | 7550/17498 |
| Frozen robust gate ≥6/8 and BOTH negative paired medians | **FAIL** | **FAIL** |
| Hard QPU native CZ≤800 and depth≤2000 | **FAIL ALL 9+9** | **FAIL ALL 9+9** |
| Actual QPU jobs / free+paid runtime | **0** | **0** |

**Critical verified negative:** More favorable original-source CX and X counts and correct quantum phase DO NOT consistently imply lower compiled native CZ/depth; complement-conjugation changes routing/placement enough to incur regressions under both public bases. The isolated seed8776 base2 gain is not a robust engineering pass. Never promote this implementation over latest holdout-proven source-cost sign selector or tune the selector proxy weights/seeds after looking at these negative results. No real Fez N35 jobs, no paid IBM runtime, no QPU quantum advantage. Full four-round QPE resource counts and real device gate remain out of scope.

**Next:** Seek an algebraically valid elimination of repeated temporary modulo-N wrap/borrow correction comparisons or design an in-place public constant adder with true reduction in relative-phase two-qubit operations, preregister robust matched seeds from the start. Alternatively move toward cross-modulus validation without reusing N35's known order or factors; preserve current robust source as control.


## 2026-10-20 — independent N23 full-outcome cube holdout: trigger FAIL, three control model wins

**Scientific record before moving further:** independently preregistered NEW 23bit
cube-vs-plain Dark Star full-outcome-head/tail holdout,
`docs/DARK_STAR_N23_FULL_OUTCOME_CUBE_PREREG.md`, frozen commit
`d50c62b129702e56b35f7b6a6a4ecd69d6d5240f`. Previous N22 *positive*
3/4 trigger result remains preserved and is **not** overwritten; prior
N17/N18 negative enrichment and public-selector outcomes also remain valid
on their respective method-specific populations.

**Public-only selection before model scoring:** workflow
[39509108244](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39509108244)
SUCCESS, 23bit public SHA-rank manifest
`results/dark_star_ptp/dark_star_n23_full_outcome_public_manifest.json`,
selected SHA256
`fe345f8c762b58e545cdaeb5d6f28188aa546dfbaba049c9ac58e3b0b1181b37`.
Of 21 publicly screened semiprimes, **13 already factored** via
gcd/power2/Pollard-p−1 B31; **8 new public-classical B31 survivors**
(4 trigger N mod3=2, 4 control N mod3=1) frozen with no
validation factors/orders/QPE costs exposed. All 8 eventually
**factored with PUBLIC B47/rho/trial**, no real QPU workload.

**Original eight independent matched scoring shards AND all-shard verifier
passed** [GitHub Actions 39509404291](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39509404291).
Frozen high-precision full-outcome HEAD method: 22 stages m4..46,
four ideal shots/stage, complete FFT y histograms through m18,
65 centered bins and analytic omitted tails ≤1/63 for higher m,
131072 nominal IID SHA PRNG eigenphase draws where validation
r>131072 (else exhaustive r), empirical Bernstein nominal
99%-simultaneous family **1408**. Actual public CF-denominator,
proper-GCD factor certificates and their classical CPU/modmult
ledgers preserved. Phase PRNG not a formal IID certificate and
floating math not outward-rounded; only *ideal-model* intervals.

| Public group | New N | Validation r(a)→r(a³) | Public even factor-producing CF d a/a³ | Cube/plain generic logical CCX per factor SUCCESS interval | Outcome |
|---|---:|---|---:|---|---|
| **Trigger** | 4958741 | 82565→82565 | **0/0** | undefined | **factor-incapable** |
| **Trigger** | 6535103 | 1084348→1084348 | 3/3 | **[0.941356,1.085360]** | **INCONCLUSIVE** |
| **Trigger** | 7692497 | 548310→182770 | **0/0** | undefined | **factor-incapable EVEN THOUGH order shrank** |
| **Trigger** | 6957281 | 6032→6032 | 577/577 | **[1.004388,1.017557]** | **model LOSS** |
| Control | 4316413 | 718458→239486 | 3/9 | **[0.768092,0.874714]** | MODEL WIN |
| Control | 7075567 | 586968→195656 | 6/18 | **[0.770684,0.871192]** | MODEL WIN |
| Control | 6394693 | 106488→35496 | 30/90 | **[0.799529,0.843385]** | MODEL WIN |
| Control | 6690841 | 1663321→1663321 | **0/0** | undefined | factor-incapable |

The **PRIMARY preregistered N mod3=2 trigger gate FAILS**: only
2/4 jointly factor-capable (needed≥3), **0/4 bounded cube wins**
(needed≥3), 1 bounded cube model loss, 1 inconclusive, 2 exact
factor-incapable. In the CONTROL stratum unexpectedly **3/4**
have bounded cube-model wins and 1 is factor-incapable;
controls are NOT substituted for the trigger study and the
eight selected toy keys do NOT establish that the opposite residue
is a universal predictor. This is important evidence
against the hypothesis that N mod3=2 is a reliable public
selector for useful cube-shortened order and factor witness.

**Archive all wins and nulls:** complete public selection/screen ledger,
all 8 unchanged per-job JSON and merged
`results/dark_star_ptp/dark_star_n23_full_outcome_all_eight.json`,
complete result
`docs/DARK_STAR_N23_FULL_OUTCOME_CUBE_RESULT.md`.
The unchanged generic arithmetic workspace at 23bits is 72
logical qubits, wide 118 vs one-phase-recycled 73 peak
(45 fewer, **38.14%**): a distinct phase-register recycling
effect, not Dark Star cubing, not fault-tolerant physical
qubits or actual QPU performance. **Zero IBM QPU shots/jobs,
zero paid/free Runtime.**

**Next gate:** A strictly PUBLIC and cheap N/a predictor that
does not itself factor N must survive a new independent sample,
including zero-CF-certificate negative cases, before any claims
about reliable cubic preconditioning or new hardware benefit.
Separate classical CPU work from abstract CCX; no RSA or
asymptotic factoring claim.


## 2026-10-20 — New 35-qubit N35 FULL FOUR-CONTROLLED-POWER BLOCK: phase-exact source sign selector 8/8 both-base native paired wins, QPU preflight FAIL

**Lead/originating work: Chase Lunsford / CaMaLabs.** Continuing from the independently confirmed [public source static signed modulo35 constant selector](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md) (original per-k source-only score `S=CX+6CCX+3RCCX`, signed for odd public k, original positive for even, **fresh 8/8 base2 and 7/8 cubic8 single-multiplier ISA resource wins**). We explicitly excluded the later [complement-conjugation negative](QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_RESULT.md) (both bases only 1/8 new-seed wins). Historic real IBM Fez Open Plan N15 qubit recycling demonstration is unrelated genuine hardware work, **not** real N35 factor recovery.

**Distinct pre-scoring frozen 4-control source+native trial:** [`docs/QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_PREREG.md`](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_PREREG.md), initial commit **`55ef0e4cbee5381dea331f1c31919966eb0e2b20`**. New [`hardware/qrr_n35_static_sign_four_controlled_powers.py`](../hardware/qrr_n35_static_sign_four_controlled_powers.py) builds **one actually integrated 35-qubit public modular-exponentiation BLOCK**, four phase controls, six-bit work, **25 shared initially/returned-clean helpers** (accumulator, validity, temporary carries, enable/wrap); uses the exact prior Qiskit gate-proven public source modulo35 adder for original or selected source and skips only public powers m=1. **Base2 schedule [2,4,16,11]**, four real multiplication stages; **cubic base8 [8,29,1,1]**, two real stages/two public identity stages. All select/decomposition decisions from public k and modular exponentiation alone; no hidden true period/order, factor/orbit/injected output table.

**Before any IBM backend access:** original 34×2 public k source-gate and sign-map receipts EXACTLY reproduced; original **3366 algebraic identity, 42672 quantum-phase comparator, 6732 both-sign modadd, 128+128 prior single-multiplier actual quantum gates** passed. Then BOTH original and selected **35-qubit** four-control block literal Qiskit `Operator` emitted gates were exhaustively interpreted on 16 phase control patterns ×64 six-bit y =**1024 exact +1 quantum-phase, semantic output, unchanged phase-control, all25 ancillas zero** per circuit, across two bases **4096 independently phase-checked full-block basis inputs PASS**. This validates the ideal coherent quantum modular-power unitary with clean input ancillas, NOT its noisy quantum execution or complete Shor QPE.

[Original two job experiment CI **39512264987**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512264987) **2/2 SUCCESS**, read-only IBM Fez hardware *TARGET*, Qiskit~=2.5.2/runtime~=0.47, optimization1, **EIGHT NEW** transpiler seeds [239,647,1453,3701,6211,9421,16673,27191] with matched old-selected circuits per seed and base, **32 original real CPU ISA native compilation runs**, no QPU. Four extra original one-multiplier seed8776 anchor compiles exactly reproduced old/signed values for both bases; NOT in eight-seed new count. [Independent original artifact strict audit and preservation CI **39512588036**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512588036) **SUCCESS**, verified all32 exact original `CZ/depth` scores and full Qiskit complex-phase proofs against previous immutable source receipts and predeclared strict gates, then committed unchanged original source JSON `results/ibm_shor35_four_power_sign_selector/qrr_n35_four_power_sign_source_base{2,8}.json`. Complete [report and all 16 paired rows](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_RESULT.md).

| NEW integrated four-controlled public modular powers, IBM Fez CPU native ISA only | Public base2 | Public cubic base8 |
|---|---:|---:|
| Complete 35-qubit source phase basis inputs tested for original+selected | 2048 PASS | 2048 PASS |
| All scratch bits returned zero and quantum output phase+1 | **PASS** | **PASS** |
| Public nonidentity multipliers in four control positions | 4 | 2 |
| NEW frozen matched Qiskit transpiler seeds per public base | 8 | 8 |
| **Same-seed strict both CZ AND depth wins for sign selector** | **8/8 PASS** | **8/8 PASS** |
| Median paired native CZ savings (original−selected) | **3717.5** | **1407** |
| Median paired native depth savings | **9389** | **3911** |
| Best observed SELECTED CZ among new seeds | 28528 | 14471 |
| Best observed SELECTED depth among new seeds | 65461 | 33951 |
| Frozen physical feasibility CZ≤800 AND depth≤2000 | **FAIL ALL** | **FAIL ALL** |
| Real IBM QPU jobs, free/paid quantum runtime | **0** | **0** |

**Milestone WIN:** Both public bases produce **8/8 matched CZ AND depth native reductions** using the unchanged original frozen public-source sign map even after assembling and exhaustively checking the *integrated* 4-control quantum modular-exponentiation block. Source original 35-qubit gate distributions base2 `CX1213 RCCX2374 CCX648 X6890`→selected `CX1107 RCCX2082 CCX602 X5970`; cube8 `CX625 RCCX1236 CCX329 X3612`→`CX575 RCCX1094 CCX309 X3052`. This is materially stronger provenance than extrapolating from standalone modular multipliers and validates ideal amplitude+1 across all 4096 clean-input full-block basis tests. **Hardware hard gate still FAILS by >one order of magnitude even for cube8; no inverse QFT, readout, actual quantum sampling or factoring whatsoever.** No N35 Open Plan QPU or paid QPU, and no cryptanalytic speedup, theorem, or practical RSA/ML-KEM break.

**Next stop:** To test complete Shor readout, preregister adding inverse QFT and measurement with exact source and native whole-circuit checks, but remain strictly CPU-only and do not reduce physical thresholds because of attractive compiler percentage gains. Alternatively target huge full-block arithmetic cost reductions before investing in readout/QPU. Preserve all earlier positive/negative controls and original N15 real hardware pilot separately.


## 2026-10-20 — NEW N24 public-only cube predictor holdout: reversed N%3 2/8 versus2/8 FAIL, 16/16 exact GCD half-witness invariant, zero QPU

**Research lead Chase Lunsford / CaMaLabs.** Preserve the independently frozen N22 3/4 conditional **ideal** public-cube QPE model wins, N23 fresh 0/4 *original* N%3=2 trigger FAIL (with 3/4 wins in a NON-trigger N%3=1 control), prior negative N17/18 holdouts and independent robust N35 public arithmetic sign-selector target CPU wins without conflating their distinct metrics. The new test was chosen to falsify the **posthoc inverted residue** N%3=1 on a NEW 24-bit population and to prove the exact ordinary factoring GCD witness behavior of odd cubing; no claims of real QPE or physical QPU runtime.

**Frozen BEFORE any validation orders:** [`DARK_STAR_N24_PUBLIC_PREDICTOR_PREREG.md`](DARK_STAR_N24_PUBLIC_PREDICTOR_PREREG.md), initial git commit **`cc143a71905775adcff1afd944a6af9502ee320f`**, deliberately narrow synthetic **24-bit** semiprime `N=pq`, p/q prime **2000..6000** construction frame (not representative of all semiprimes), balanced public groups **8 `N%3==1` and 8 `N%3==2`**, deterministic new SHA-rank and public coprime base from 11-prime pool, public gcd/2power/Pollard p−1 **B31 classical FIRST**. Fixed **P1** predicts `ord(a)%3==0 AND proper standard even half-order factor witness` iff `N%3==1`; primary gate demands **>=6/8** true joint positive G1 and **<=2/8** G2. Fixed descriptive **P2** predicts positive from fewer set bits in 8 successive public modular-power constants of `a³` than `a`, ties negative. Record public Jacobi sign separately, not a feature used for selection. Never select new N on p/q/order, factors, QPE outcomes, or P1 correctness.

[First manifest-only GitHub Actions 39512436774](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512436774) **SUCCESS**, committed immutable public-only selected manifest SHA256 **`d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889`** via git **`6a3eb458d63c15b57468ceafadae6c94ebe5c260`** BEFORE any order/half-witness validation: [source public manifest](../results/dark_star_ptp/dark_star_n24_public_predictor_manifest.json). Population frame 57,052 Ns; public B31 screens **11 G1 (3 already factored)** plus **12 G2 (4 factored)**, choose first 8 classical B31 survivors each; no selected validation factors or order labels in manifest. [Public original selection](../hardware/dark_star_n24_public_predictor_manifest.py) outputs only P1/P2/Jacobi, N,base,cubed base, B31 screens. All 16 distinct.

[Fresh validation source](../hardware/dark_star_n24_public_predictor_validate.py) uses frozen SHA, FIRST resolves all 16 via explicit PUBLIC post-B31 classical cascade (B47, fixed rho 64×two seeds, trial division), then uses recovered public factors to find exact orders from λ(N), validates minimality, factor-witness sets, cube order identity and halfpower residue `a^(r/2)`. **All 16/16 were FACTORED CLASSICALLY** (G1 6 Pollard rho+2 B47, G2 7 rho+1 complete trial). Standard elementary algebra: `ord(a³)=r/gcd(r,3)` and whenever r even, `(a³)^(ord(a³)/2) == a^(r/2) modN`; thus **proper gcd(a^half±1,N) witnesses unchanged for odd cube**. **All 16/16 actual numerical cases passed this invariance**, with cubic order reduced in 8/16 and factor witness usable in12/16, but only **4/16** satisfied both. This is not a new theorem or QPE gate-cost result.

[Original scoring and strict independent all-16 validation GitHub Actions **39512868715**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512868715) **SUCCESS**, zero Quantum/IBM client, no QPU. Unchanged original numerical/ledger receipt [`results/dark_star_ptp/dark_star_n24_public_predictor_validation.json`](../results/dark_star_ptp/dark_star_n24_public_predictor_validation.json) committed, with EVERY sample, factor certificate, order, P1/P2 vote and public CPU/classical accounting. [Full report](DARK_STAR_N24_PUBLIC_PREDICTOR_RESULT.md).

| New prereg 24-bit B31-survivor cohort, exact number theory necessary conditions | N%3==1 G1 | N%3==2 G2 |
|---|---:|---:|
| SHA-selected cases before outcome | 8 | 8 |
| True cube order reduces by3 | **4/8** | **4/8** |
| Proper even-order standard factor witness a/a³ | **6/8** | **6/8** |
| **Both shortened and proper factor witness (TARGET T)** | **2/8** | **2/8** |
| Frozen P1 predicted T / actual gate | predicts all YES: **FAIL** | predicts all NO; 2 positives |
| Exact plain-vs-cube halforder witness equality | **8/8 PASS** | **8/8 PASS** |
| Real QPU jobs / free/paid IBM runtime | **0** | **0** |

**Primary P1 negative:** TP2/FP6/FN2/TN6, sensitivity/specificity and balanced accuracy all0.5, raw accuracy50%; conditional fixed-group exploratory one-sided Fisher/hypergeometric tail **p≈0.7154**, no support for inverted public N mod3 signal. **P2 also negative:** TP0/FP1/FN4/TN11, sensitivity0%, accuracy68.75% vs **75% trivial always-NO baseline**, balanced accuracy≈45.83%. Jacobi sign recorded observationally (ten −1 cases have nine witnesses, 3 T positives; six +1 cases 3 witnesses, 1 T positive), not a validated selector. P1 prereg strict 6/8 gate **FAIL**. Do not claim prior N22 conditional ideal-model 3/4 win disappears or N23 control 3/4 is itself a policy proof; this fresh necessary-condition screen is not a model per-success CCX estimator.

**Interpretation and next:** odd cubic transform may change quantum phase sampling/circuit resource count but is algebraically incapable of converting an incapable standard half-order GCD witness into a capable one. Reliable cheap public N/base predictor remains unestablished. Do NOT tune P1/P2, relabel the prospective positives, discard factor-incapable cases, or treat observed shortening as QPU factoring. Return emphasis to the **N35 35-qubit complete four-controlled-power arithmetic block's independently verified 8/8 two-base paired native CPU compiler wins** documented in [`QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_RESULT.md`](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_RESULT.md). Even that is NOT hardware-feasible at fixed native **CZ<=800, depth<=2000**, and omits QFT/readout. Consider a separately preregistered full inverse-QFT and readout **CPU** compiler overhead check with exact phase correctness, or mathematically distinct reversible modular arithmetic structure and fresh matched seeds. **No QPU, free Open or paid Runtime authorized; N15 genuine Open Plan recycled-phase pilot remains separate and preserved.**


## 2026-10-20/21 — N35 35-qubit FOUR-wide QFT ideal phase outcome: strict factor 0% base2 /50% cube8, bounded 37.5%/75% with classical controls, ZERO QPU

**Attribution:** Chase Lunsford / CaMaLabs. This is the next distinct experimental step after the [independently preserved 35-qubit four-controlled-public-modular-powers + H⁴ + inverse-QFT + four terminal measurement circuit](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md) successfully compiled on IBM Fez READ-ONLY CPU target for BOTH public N35 base2 and cube8, 8/8 matched native CZ and depth reductions using deterministic public source sign selection, but **every full circuit far beyond native hardware feasibility CZ≤800/depth≤2000, ZERO QPU execution**. That prior work had verified the true QFT gate and controls but did NOT calculate quantum measurement probability or score proper factors. Preserve original N15 IBM Open Plan REAL recycled-phase hardware pilot separately; N35 4-wide has NO phase recycling and is NOT device-run.

**New mathematical ideal readout/factor recovery protocol** [`QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_PREREG.md`](QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_PREREG.md), pre-outcome frozen git commit **`0602117b47808e9edcbc7e200c1f1e8d1c5f1a1e`**. Reuse existing FULL-source exact quantum operator: all **1024/1024** phase-control×64 work clean-input basis states PER original/selected arithmetic circuit PER base yield correct public `a^c mod35` multiplication, all25 helpers clean, complex phase +1, source histograms/stages archived. Confirm work|1>, **four simultaneous phase H**, literal 16×16 inverse QFT and four terminal readout instructions. Then algebraically shrink the proven reachable clean-aux subspace to 4 phase+6 work=**10 qubits**, construct mathematical `A[k,y]=(1/16)Σ_{c:a^c mod35=y}exp(−2πi kc/16)` for k0..15,y0..63; independently check EVERY ONE of 1024 complex amplitudes against Qiskit actual ten-qubit `Statevector.evolve(QFTGate(4).inverse())`. Max abs errors base2 **9.77×10^-16** and cubic8 **1.40×10^-15**; both distributions normalized, no quantum shots. Original/selected sign source has identical ideal output probabilities, only different ISA native compiler resource costs.

Two frozen public-only postprocessors: **STRICT CF** tests every regular k/16 convergent denominator q≥2, q≤16 as candidate even period r=q; **BOUNDED** also permits multiplier m=1..4, r=mq≤64, with public `pow(a,r,35)==1` before standard proper-factor `gcd(a^(r/2)±1,35)`. Both reject k0 and q1, never use actual true period or factors in generating candidates. Uniform randomly selected four-bit phase k baseline and pre-QFT classical GCD(a±1,N)/four even exponent public scan r2,4,6,8 included to prevent inflated quantum claim. True group order r2=12,r8=4 assessed ONLY AFTER factor scoring.

[Original Qiskit local CPU experiment **39539165648**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39539165648) **2/2 PASS** with original source gate reproof and exact 1024 amplitudes plus all16 possible outcomes. [Independent no-rescoring original-artifact audit/preservation **39539345288**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39539345288) **PASS**, downloaded ORIGINAL science receipt JSONs, independently recomputed all p(k) via work-state interference, proper GCD witness/candidate policies, uniform baseline and classical preemptions, preserved originals untouched under `results/n35_ideal_iqft_outcome/qrr_n35_ideal_iqft_outcomes_base{2,8}.json`. Full [report and every one of 16 phase outcomes](QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_RESULT.md).

| Exact noise-free four-wide IQFT output under FROZEN classical policy | Base2 | Public cubic8 |
|---|---:|---:|
| Mathematical order (DESCRIPTIVE AFTER scoring) | 12 | 4 |
| **STRICT CF ideal P(proper factor)** | **0%** | **50%** |
| **BOUNDED m≤4 public additional CF tests ideal P(proper factor)** | **37.5%** | **75%** |
| Uniform random k strict success baseline | 0% | 12.5% |
| Uniform random k bounded-success baseline | **37.5%** | 68.75% |
| Uninformative zero-phase k0 P | 9.375% | 25% |
| Immediate PUBLIC gcd(a−1,35) |1|**7 — trivial factor!** |
| Four small EVEN r=2,4,6,8 public exponent scan success | NO | YES |
| Independent 10-qubit 1024 amplitude agreement, exact +1 full 35-qubit source | PASS | PASS |
| Hardware usable? / QPU device jobs | **NO /0** | **NO /0** |

**Most important honest negative:** The base2 **0% STRICT** 4bit CF period/factor recovery and the 37.5% permissive success **exactly equal to uniform unrelated four-bit k** show the limited measurement has insufficient useful phase information for that frozen factor policy. Cube8 produces ideal phase outcomes precisely k=0,4,8,12 with probability25% each, but a single PUBLIC classical `gcd(8−1,35)=7` already factors 35, so 50% and75% quantum-readout-based *ideal factor scores do not establish any quantum factoring advantage*. The bounded-multiple heuristic uses extra public classical modular exponent tests and must not be advertised as strict Shor. All N35 toy data remain strictly distinct from practical RSA/ML-KEM cryptanalysis, actual Shor device fidelity and proof of consciousness or other projects.

**Next falsifiable direction:** preregister further phase resolution (6..8 phase bits) and test strict continued-fraction outcome probabilities while controlling for exponential wide readout costs and classical trivial-factor prechecks; a **real recycled phase-QPE controller** would be a separate architecture that cannot be established by wide circuit QFT. Never weaken CZ800/depth2000 device gate or submit QPU without separate explicit Open Plan-confirmed approval. Preserve successes BEFORE new experiments.


## 2026-10-20 — N35 ideal six/eight-phase-bit precision gives base2 strict CF 11.48%/29.26%; cube8 50% saturated/classically preempted; zero QPU

**Research lead Chase Lunsford / CaMaLabs.** A further precision-level ideal quantum-information experiment, not a new live IBM device result or compiled 6/8-bit arithmetic implementation. Earlier [complete 35-qubit FOUR-WIDE-phase-bit inverse-QFT readout](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md) passed 1,024 actual emitted quantum gate-basis phase+1 clean-helper cases per original/source-selected variant per public N35 base a2/cube8, and its [independent fourbit full-outcome+classical scoring](QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_RESULT.md) gave strict 0% base2 vs50% cube8 and bounded 37.5% base2 vs75% cube8. The 35-qubit four-bit target-ISA benchmark FAILED the strict native CZ≤800/depth≤2000 hardware preflight, and cube8 was already classically factorable by gcd(8−1,35)=7. Prior actual IBM Open-plan N15 phase-qubit recycling pilot and all arithmetic wins and nulls remain unchanged.

**PRECOMMITTED hypothesis [`QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_PREREG.md`](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_PREREG.md)**, git **`7f67f62c9b3ee7ee84eda43e2927a0a7430ec6da`** BEFORE new six/eight-bit numbers. Exact public N35 bases2/8, phase bits **4,6,8** (M16,64,256), full six-bit work state; b4 numerical source anchor; **same strict ordinary public convergent denominators q≤M, r=q and permissive m=1..4 r=mq but ALWAYS r≤64**, public even-order verification and standard gcd plus/minus factors; k=0 never succeeds; uniform-random-k and classical gcd(a±1,35) baselines, full no-postselection 336 outcomes per base. Six/eight are explicitly **IDEAL predicted extensions of the previously verified four-bit unitary, not 37/39-qubit circuits built on a real processor or even native CPU transpiled; NOT phase-qubit recycling**. No IBM credentials, no backend read, NO quantum runtime, no QPU.

New [source `hardware/qrr_n35_ideal_phase_precision_4_6_8.py`](../hardware/qrr_n35_ideal_phase_precision_4_6_8.py) FIRST reproved original 35qubit four-phase Qiskit-emitted `Operator` exact complex quantum-phase full work/control 1,024+1,024 source cases per public base, all 25 aux clean, old IQFT source checks. For b=4,6,8 it used only PUBLIC `pow(a,c,35)` to build the reduced ideal state `1/sqrt(M) sum_c |c>|a^c mod35>`, independently computed **EVERY complex Fourier amplitude** via **NumPy FFT and literal Qiskit `Statevector.evolve(QFTGate(b).inverse())`**, matching all **1,024+4,096+16,384=21,504 complex amplitudes per base** within 1e−9 (observed max ~1.67e−16), full ∑P(k)=1, exact fourbit original P(k) and old strict/bounded score anchors, all public exponent witnesses. Descriptive group orders r2=12, r8=4 checked strictly AFTER the policy scores, never used to generate q or r.

| N35 IDEAL quantum phase readout per single mathematical measurement | Public base2 4b | Base2 6b | Base2 8b | Public cube8 4b | Cube8 6b | Cube8 8b |
|---|---:|---:|---:|---:|---:|---:|
| **Strict public ordinary CF proper-factor success** | **0%** | **11.4756%** | **29.2552%** | **50%** | **50%** | **50%** |
| Extra-classical-search bounded up-to-4-multiple CF success | 37.5% | **61.7593%** | **79.7151%** | 75% |75%|75%|
| Uniform-random-k strict policy |0%|3.125%|5.46875%|12.5%|21.875%|27.34375%|
| Uniform-random-k bounded policy |37.5%|59.375%|65.625%|68.75%|82.8125%|89.453125%|
| P(uninformative k0) |9.375%|8.3984375%|8.3374023%|25%|25%|25%|
| PUBLIC gcd(base−1,35) immediate proper factor | none |none|none|**7**|**7**|**7**|
| WIDE register logical width if implemented using same six work+25 clean helpers |35|**37 forecast only**|**39 forecast only**|35|**37 forecast only**|**39 forecast only**|
| Public nonidentity powers from pow(base,2**i,35) |4|6|8|2|2|2|
| Actual b6/b8 source ISA built or IBM QPU executed | NO b6/b8 |**NO**|**NO**|NO b6/b8|**NO**|**NO**|

**Scientifically grounded win:** For public base2, more IDEAL phase precision makes standard **strict** CF factor recovery nonzero and informative versus the random-k baseline: 6b11.48% versus random3.125%; 8b29.26% versus random5.46875%. Bounded m≤4 includes substantial nonquantum search and at 4bits base2 was identical to uniform k, while cube8's 50% strict saturated already with four bits and gcd(8−1,35) publicly factors N without any Fourier measurements; at 8bits uniform-k bounded even exceeds cube's 75% true QFT score. All are mathematically ideal, for classically trivial N35; not evidence of RSA-speedups or IBM hardware performance.

**Source workflow [39540677040](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39540677040)** completed both 35q source proofs and ALL 2×(4/6/8) mathematical QFT/FFT computations and exported original success/complete JSON; **GitHub overall marked FAILURE due solely to a POST-RESULT AUDITOR wrong capitalization** `strict_cf_ideal_success_probability` instead of correct `strict_CF_ideal_success_probability`. Original science and source steps succeeded. No quiet rerun or amended numerical outputs. [**Independent original-artifact audit+archival 39540931690**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39540931690) **SUCCESS**: downloaded ORIGINAL two result JSONs without rerunning model, independently computed all **672 ideal output probabilities** from direct `cmath` interference (not FFT or Qiskit), recomputed **all** strict/bounded convergent q, exponent attempt r, factor witnesses, uniform baselines and the earlier original b4 source/score evidence; byte-preserved original receipts under `results/n35_ideal_phase_precision/qrr_n35_ideal_phase_precision_base{2,8}.json`. Full [report](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_RESULT.md), exact 16/64/256 outcome tables in JSON. **ZERO backend/QPU jobs/shots/Open/Paid Runtime.**

**NEXT falsifiable step:** An actual **ONE-recycled-phase-qubit** mid-circuit measurement/reset/feedforward implementation (semi-classical inverse QFT or iterative phase estimation), to match **all** independently audited b4/b6/b8 WIDE ideal distributions for both public bases. This has NOT yet been built. Need separately freeze the correct history-dependent feedforward and IQFT bit ordering, verify exact quantum phases & six-bit public work state with no precomputed answer, and never substitute an analytic WIDE distribution for an implemented recycled circuit. No physical QPU until a separately justified CZ≤800/depth≤2000 native-cost gate AND explicit Open Plan authorization.


## 2026-10-20 — First true 32-qubit ONE-phase-recycled N35 dynamic IQFT source: 672/672 adaptive-vs-wide ideal outputs and 768 stage unitary cases per base; no QPU

**Research lead Chase Lunsford / CaMaLabs.** Separate, actual **Qiskit DYNAMIC source construction** milestone following independently archived [4/6/8 ideal phase-precision mathematical study](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_RESULT.md). That previous study showed base2 STRICT public CF 0%/11.4756%/29.2552% for 4/6/8 bits and cube8 STRICT50% fixed, but b6/b8 WIDE quantum gate-source circuits were never constructed; prior actual 4-WIDE-phase N35 35qubit source and full inverse QFT failed real IBM native CZ≤800/depth≤2000 hardware feasibility. Previous genuine IBM Fez Open-Plan N15 recycled-phase toy QPU run still independent; public cube8 has the trivial classical proper factor `gcd(8−1,35)=7`, so NO quantum factoring/cryptanalytic advantage.

**NEW FROZEN prereg before science:** [`docs/QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_PREREG.md`](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_PREREG.md), git commit **`f952942dc56ecf8e2ad6fab70056c8544651947a`**, for public N35 bases2/8, b=4/6/8, ONE TRUE reused phase QUBIT +6 work quantum qubits+25 clean arithmetic helpers =**32 quantum QUBITS**, b classical bits, with public controlled multipliers phase-exact, actual Qiskit mid-circuit `measure`, `reset`, `if_test` conditional phase feedforward, and exact comparisons to every original independently audited WIDE ideal QFT probability, with no true-period/order input, no precomputed 64-entry quantum oracle, and ZERO QPU.

**New actual [Qiskit dynamic source & phase-source proof](../hardware/qrr_n35_true_recycled_phase_feedforward.py)** constructs six distinct b4/b6/b8 and base2/8 quantum circuits, all width **32** (not 35/37/39 WIDE), phase control stage j from b−1 DOWN to0, `m_j=pow(base,2**j,35)`, H→controlled honest sign-selected Qiskit modular arithmetic→adaptive phase P(−2π /2^(t−j+1)) guarded by earlier classical result bit `b−1−t`→H→measure into bit `b−1−j`→reset when another stage follows; work never measured/reset and 25 helper bits cleaned. Precisely H counts8/12/16, mid-circuit measurements4/6/8, phase resets3/5/7, actual conditional `if_else` operations6/15/28 per precision, all original sign-selected 34-row public source k mappings regenerated/checked against committed originals. Controlled multiplication uses original exact reversible six-bit public weight accumulator/network/inverse cleanup, **not** a custom basis permutation gate and no period oracle. Independently verified **six distinct full-register nonidentity public powers {2,4,8,11,16,29} × all128 control/work input cases =768 true quantum-emitted `Operator` instruction semantic tests PER BASE**, correct full six-bit residue action, invalid and disabled identity, all **25 helpers returned ZERO**, exact output COMPLEX quantum phase +1.

**Ideal branch work dynamics:** a 64-complex-amplitude coherent quantum work state propagated through every measurement-history branch, explicit classical P(theta), H measurement/projected unnormalized postmeasurement states and real work multiplier, branch norms sum1 every stage. Proper reversed measurement-to-k bit order was essential. **Base2 b4/b6/b8 all 16+64+256=336/336 independent prior WIDE IQFT P(k) matched**, maximum per-outcome probability deviation **1.39e−17 / 6.94e−18 / 2.08e−17**. **Cube8 b4/b6/b8 336/336 EXACT P(k) matches** in saved floating-point receipts. **TOTAL 672/672 WIDE-versus-RECYCLED exact ideal output predictions verified**, no excluded outcomes, plus strict/bounded classical CF scores equal archived b4/6/8. **New SIX b4/b6/b8 Qiskit dynamic source circuits are actually constructed**, unlike previous b6/b8 wide forecasts. These are SOURCE and independent mathematical ideal branch results, **NOT end-to-end Qiskit dynamic/Aer shot execution, real Fez ISA transpilation, or hardware run**.

**Provenance:** First workflow [39541874090](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39541874090) failed PRE-SCIENCE due only to misnamed archived source receipt folder; corrected statically without changing quantum source or hypothesis. [Original full source SCIENCE workflow **39542022177**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542022177) ran both public bases' actual gate unitary cases and all recycled dynamic circuit constructs and 672 complete ideal probability validations, saved original **success=true** source result JSONs. Overall GitHub workflow marked **FAILURE due solely to post-science auditor CASE-MISMATCH**: `actual_QPU_jobs` vs nested `actual_qpu_jobs`; the actual source and all arithmetic/branch computations completed SUCCESS before auditor. First independent preservation [39542289598](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542289598) repeated that audit field typo; [**corrected independent original-artifact audit/preservation workflow 39542358654**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542358654) **SUCCESS**, downloaded original source-run numerical artifacts, independently reverified every 32qubit quantum gate source-unitary receipt, Qiskit dynamic classical `if_else`/measurement/reset/phase source structure, AND recalculated all **672 ideal branch probabilities using independently written PURE Python sparse complex amplitudes (NO Qiskit, NumPy or re-run of science)**, matched old full wide reference, signed strict/bounded scores, no runtime. Committed the **ORIGINAL UNMODIFIED original receipt bytes** under `results/n35_true_recycled_phase_feedforward/qrr_n35_recycled_phase_feedforward_base{2,8}.json`. Read [full report](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md).

| TRUE Qiskit source variant | phase4 | phase6 | phase8 |
|---|---:|---:|---:|
| Actual simultaneous quantum qubits | **32** | **32** | **32** |
| Simultaneous quantum phase qubits | **1** | **1** | **1** |
| Classical midcircuit measurements | 4 | 6 | 8 |
| Real phase reset gates in source | 3 | 5 | 7 |
| If_test conditional P feedforward controls | 6 | 15 | 28 |
| Independently checked exact ideal outcome probabilities PER BASE | **16/16** | **64/64** | **256/256** |
| Original hypothetical WIDE source quantum qubits | 35 | 37 (unbuilt) | 39 (unbuilt) |
| Native IBM Fez CZ/depth verified for this new dynamic source | **NOT COMPILED** | **NOT COMPILED** | **NOT COMPILED** |
| Real IBM quantum processor jobs/shots | **0** | **0** | **0** |

**SCIENTIFIC MILESTONE:** The project now contains an actual quantum-source *one-reused-control-phase-qubit* dynamic implementation with phase-aware public-gate semantics and independently verified exact full ideal IQFT branch probabilities. It is no longer just a wide inverse-QFT phase-precision forecast. **LIMITATIONS:** not end-to-end Qiskit dynamic quantum device/Aer execution, no proof of hardware midcircuit support or latency, no actual native ISA resource numbers for this dynamic design, no full hardware factoring, no alternative to classical factoring N35, no RSA/cryptographic impact. Frozen hardware native CZ≤800 & depth≤2000 remain unsatisfied/unassessed for new dynamic source, and ZERO real Open/Paid QPU runtime authorized or used.

**Next:** preregister IBM Fez **READ-ONLY CPU native transpiler** lowerability of actual dynamic `if_else`/`reset`/`measure` using all source qubits, and check backend dynamic support and source control-flow preservation; independently document *compilation failure as a valid negative* if unsupported. No hardware runtime should be touched without separately explicit scope/Open Plan authorization.


## 2026-10-21 — TRUE recycled N35 dynamic Fez ISA compiler accepts 6/6, all 98 feedforward conditional quantum operators phase-correct; mapped physical phase wire still uncertified

**Lead and original research:** Chase Lunsford / CaMaLabs. The most recent prior [true one-recycled-phase-qubit Qiskit SOURCE](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md), independently archived via [39542358654](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542358654), genuinely constructed N35 public base2 and cube8 × b4/6/8 **six 32-logical-qubit source dynamic circuits**, one reused phase bit, six coherent unmeasured work, 25 returned-clean arithmetic ancillas and b classical output bits. All6 distinct public power stages pass **768/768 source complex-phase+1 direct gate input cases per base** and all b4/6/8 ideal conditional measurement branch probabilities **672/672 agree** with independent WIDE inverse QFT across both bases. None had previously been compiled to dynamic IBM Fez native ISA, and all original N35 full-circuit hardware preflight limits CZ≤800/depth≤2000 remained FAILED. Real IBM Fez Open Plan N15 phase recycling is a separate genuine QPU milestone; public cube8 mod35 already trivially factors by gcd(8−1,35)=7.

**NEW preregistered actual dynamic-ISA CPU compiler study**, [frozen before native score](QRR_N35_TRUE_RECYCLED_PHASE_DYNAMIC_FEZ_ISA_PREREG.md), original commit `b5d457abf9423a81040bfedf0e1102c342a2eb8f`, [source `hardware/qrr_n35_true_recycled_dynamic_fez_isa.py`](../hardware/qrr_n35_true_recycled_dynamic_fez_isa.py), same exact original six dynamic circuits, IBM Fez read-only target, Qiskit~=2.5.2, runtime~=0.47, opt1 seed8776, NO source rewrites to phase register, feedback, fake oracle, public order or factor, ZERO QPU jobs. Before backend, original exact six source instruction histograms/schedules and original archived 768 stage input cases/336 ideal outcome reference PER BASE were checked intact. Fez TARGET advertised `if_else`, measurement and reset native operations. **ALL SIX Qiskit CPU ISA compiles accepted**, retaining original classical condition count b(b−1)/2, exactly b measurement, b−1 reset, b classical output bits and 32 SOURCE logical qubits. CPU native CZ/depth: **base2 b4 29813/69008, b6 43613/99325, b8 59446/138604; cube8 b4/6/8 14499/34259 each**. Compiler lowered conditional source `P(theta)` to native `RZ(theta)`, conservatively marked **COMPILED_UNCERTIFIED_DYNAMIC_SEMANTICS** until independent matrix proof. Authenticated Fez device width 156 in compiled Qiskit result is NOT the original source 32, and neither it nor top-level `depth()` establishes actual on-device feedback latency. [Original experiment CI **39729198098**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729198098) 2/2 SUCCESS; [independent byte-for-byte source artifact audit/archive **39729456702**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729456702) SUCCESS, stored original JSON `results/ibm_shor35_true_recycled_dynamic_fez_isa/qrr_n35_dynamic_isa_base{2,8}.json`. Full [ISA result report](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEZ_ISA_RESULT.md).

**Second DIFFERENT preregistered native conditional quantum-Operator falsification**, [protocol](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_PREREG.md), initial git `10084259eda715d41c38a787de1371ae31b04967`, same exact source/seed/compiler, [reproducible audit source](../hardware/qrr_n35_native_dynamic_feedback_phase_audit.py). It independently extracted every ACTUAL compiled 1-qubit true `if_else` body as a complex `Operator`, compared it to SOURCE `PhaseGate(theta)` with original measured classical bit index, comparison literal1, bit ordering and angle, allowing **ONLY one global scalar per PREVIOUSLY CLASSICALLY MEASURED outcome-history branch**. Crucially `P(theta)=e^(i theta/2) RZ(theta)`; branch-global phase has no effect on probabilities only when the controls are measured CLASSICAL bits, not for unmeasured quantum controls. **ALL 98/98 source-vs-native conditional 2×2 branch matrices PASS**: two public bases × [b4 6 +b6 15 +b8 28]; max residual **≤1.6×10^−16**, correct classical condition and output bits, all original native CZ/depth reproduced exactly. The remaining independently recorded problem: compiled measure/reset/conditional phase operations move across multiple physical device qubit positions (e.g. cube8 locations85,86,91, base2 b8 nine different reported locations), so the STRICT full-dynamic semantics + ONE FIXED physical phase-wire certification FAILS 6/6. This does **not** refute recycling ONE LOGICAL phase in original source, but it leaves physical SWAP/routing lineage, latency and actual hardware feasibility unproven. Individual conditional phase unitary semantics PASS, overall physical-mapping certification does NOT. [Original native-phase CI **39729974663**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729974663) 2/2 SUCCESS; [independent original JSON operator audit/preservation **39730198680**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39730198680) SUCCESS, original numerical receipts at `results/ibm_shor35_true_recycled_dynamic_feedback_audit/qrr_n35_native_dynamic_feedback_phase_base{2,8}.json`. Full [matrix/physical-mapping result](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md).

| True 32-SOURCE-QUBIT recycled phase precision | Public base2 compiled CZ / Qiskit depth | Public cube8 compiled CZ / Qiskit depth | Conditionally compiled RZ P-equivalence |
|---|---:|---:|---|
| b4 classical phase bits | 29,813 / 69,008 | 14,499 / 34,259 | **12/12** across bases |
| b6 classical bits | 43,613 / 99,325 | 14,499 / 34,259 | **30/30** |
| b8 classical bits | 59,446 / 138,604 | 14,499 / 34,259 | **56/56** |
| ALL feedback condition branches | 6+15+28 per base | two bases | **98/98 EXACT up to measured-branch-global phase** |
| Full native ISA CPU acceptance | 3/3 | 3/3 | **YES** |
| ONE fixed physical phase wire / dynamic device timing | uncertified | uncertified | **DO NOT CLAIM** |
| Frozen CZ≤800 and depth≤2000 physical QPU preflight | FAIL 3/3 | FAIL 3/3 | **HARDWARE BLOCKED** |
| Real N35 quantum device jobs/free or paid Runtime | **0** | **0** | ZERO |

**Research record interpretation:** The actual dynamic source is genuinely one reused logical phase, and a real backend-target native CPU compiler ACCEPTS it while all explicitly classical conditional rotation operators correctly lower to native rotations **UP TO irrelevant branch-global phase**. But routing/SWAP lineage, real-time hardware support/fidelity, actual phase-experiment QPU factoring, and the massive native gate budget remain unproven, so **do not submit to any IBM QPU**. This is a carefully verified source+compiler milestone, not real QPU capability/advantage, and the recorded limitations are meaningful. Next prioritize exact native routing-state tracking only if investigating dynamic source deployment, and pursue another order-of-magnitude reduction in full public modular arithmetic with matched seeds and phase-clean helpers before hardware feasibility discussions.


## 2026-10-22 — TRUE one-phase-recycled N35 source 32→23 qubits: nine genuinely idle scratch removed, all 48 Fez native CPU pairings valid, native robustness and QPU still FAIL

**Research lead / attribution Chase Lunsford / CaMaLabs.** This continuation uses the LATEST genuine N35 **one reused phase qubit** mid-circuit measurement+reset+classical IQFT source, not the older one-multiplier seed experiment. The existing independent [source proof](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) found original **32 source quantum qubits** = phase1+work6+helpers25 with b4/6/8 classical outputs, phase unitary operator tests 768 public stage cases PER BASE and 336 independent ideal branch probabilities per base, plus real `if_else`/measure/reset instruction structure. The distinct [authentic IBM Fez read-only CPU ISA compilation](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEZ_ISA_RESULT.md) compiled all six original b4/6/8 base2/cube8 circuits, while a later [quantum-Operator conditional phase matrix study](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md) established 98/98 actual compiled P→RZ branch equivalences **UP TO previously measured classical-history GLOBAL phase**. But physical constant phase-wire routing remained UNCERTIFIED and original hardware cost gate **CZ≤800/depth≤2000 FAIL** everywhere. No IBM real QPU job/free or paid quantum runtime.

**New preregistration** [`QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md`](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md), frozen commit `b2f19450390cccb5464a51eeec93027ec517cf7b` BEFORE any new compiler scoring, tests a simple falsifiable hardware-source efficiency idea: the original `scratch9` register might be allocated but never used after source arithmetic optimizations. For every base2/cube8 × b4/6/8 actual source, first strictly inspect every emitted instruction qubit operand and nested feedback body; ABORT if a scratch qubit is touched. Otherwise reconstruct a **23-source-qubit** original SAME dynamic circuit using original register objects and EXACT original individual gate operations, quantum/classical operands, ordering and `if_else` branch/condition objects, but omit the genuinely idle 9-qubit scratch register. Verify every emitted operation/parameter identical, original source phase1 and work6 unchanged, original measure=b/reset=b−1/if_else=b(b−1)/2 intact. Predeclare four compiler seeds **[509,1223,4093,8776]**, pinned Qiskit~=2.5.2/IBM runtime SDK~=0.47, Fez TARGET READ ONLY, optimization1. For every base, precision and seed, match ORIGINAL32q against new23q source, **2×3×4×2=48** independent native CPU compiles, no layout cherry picking. Native conditional 2×2 branch `Operator` proofs required for every compiled `if_else`; historical seed8776 CZ/depth must match original immutable values. Strict resource win only if for every base and precision ≥3/4 seeds have BOTH lower native CZ/depth and negative median deltas. Physical CZ≤800/depth≤2000 separate, **QPU prohibited**.

**First precompiler harness failure** [39738758532](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738758532) was caused by using Python identity `reg is not scratch` across register wrappers instead of stable `reg.name!='scratch'`. Original source inspection already saw zero scratch operand, but the code rejected expected register count **BEFORE backend read or native compilation**, so this FIRST run is NOT counted as an experiment success. A narrowly documented single-line source-clone register filter repair changed NO arithmetic, Qiskit operation, feedback, seed, hardware settings or acceptance criteria; initial failure preserved in prereg audit note.

**TRUE new source width result**, [successful 2/2 original CPU trial **39738979913**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738979913): ALL six true dynamical b4/6/8 circuits had **ZERO of 9 scratch bits in actual instruction operands**, including all single-qubit conditional bodies. The source reduced EXACTLY from **32→23 qubits** (**−9, −28.125%**), keeping phase1, work6 and **16 still-live/necessary helpers**, while every actual quantum operation, operand bit, source operation count and dynamic `if_else` condition/body was exactly preserved. Source program's ideal quantum instrument over surviving wires is thus mathematically the SAME; the prior exact 768 phase-stage and 336 ideal probabilities PER BASE were previous archival proofs, NOT newly rerun numerical simulations. The new candidate retains **one genuine recycled phase bit** and unchanged 4/6/8 classical feedback bits.

**ALL 48 read-only native Fez CPU compiler trials succeeded** and preserved b measure/b−1 reset/b(b−1)/2 conditional gates; every compiled conditional true-block phase matrix matched original source P up to classical branch-global phase. Exactly **784/784 actual native `if_else` branch operator comparisons** (2 bases×4 seeds×2 original/candidate×(6+15+28) branches) passed, as did all six prior native seed8776 original anchors. Native transpiler still reports target **156** physical-device qubit indices; e.g. new cube8 b4 seed509 touched 23 physical addresses while base2 b4 seed509 touched 25, with measured/reset/conditional phase operations at several physical locations. Touched physical addresses and compiled target register width do NOT prove single fixed physical phase wire, peak physical occupancy, device latency or hardware fidelity. Physical mapped reuse remains unresolved.

**Native cost robustness** against exact source-original matched seeds FAIL for ALL six base/precision groups. Negative deltas mean fewer native CPU gates or lower compiled top-level depth. The frozen seed8776 side-by-side raw native CZ/depth:

| Public base/precision b | Original 32q CZ/depth | New 23q CZ/depth | Paired four-seed joint CZ+depth wins | Median paired ΔCZ / Δdepth | Native robust gate |
|---|---|---|---:|---:|---|
| base2 b4 | 29813/69008 | **29223/68106** | 2/4 | −287.5 / −1281 | **FAIL** |
| base2 b6 | 43613/99325 | 44313/102275 | 2/4 | −411 / +568.5 | **FAIL** |
| base2 b8 | 59446/138604 | 59730/138953 | 1/4 | +123 / +2.5 | **FAIL** |
| cube8 b4 | 14499/34259 | 15036/34595 | 2/4 | −286.5 / −1800 | **FAIL** |
| cube8 b6 | 14499/34259 | 15036/34597 | 2/4 | −286.5 / −1800 | **FAIL** |
| cube8 b8 | 14499/34259 | 15036/34599 | 2/4 | −286.5 / −1800 | **FAIL** |

The source width win is real despite **inconsistent physical routing gate cost**. Every native hardware gate CZ≤800 AND depth≤2000 **FAILED** (lowest observed near 14097 CZ/depth32814 for cube8 pruned), even before realistic fidelity/timing, and **ZERO real IBM QPU submissions or paid/free quantum Runtime use**.

[**Independent original-artifact audit and preservation CI 39739268951**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39739268951) **SUCCESS**: downloaded both originally produced JSON receipts without recompiling, checked ALL 48 raw CZ/depth tuples, exact source qubit instruction identity, old 768+336 archived evidence, 784 native compiled classical feedback Operator successes, all seed8776 historical anchors, six precision group medians/win counts and QPU gates; committed exact unchanged original `results/ibm_shor35_true_recycled_idle_scratch_pruning/qrr_n35_prune_idle_scratch_base{2,8}.json` files. Full [result report](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md), [precommitted preregistration](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md), [original source code](../hardware/qrr_n35_true_recycled_prune_idle_scratch.py). All earlier real IBM Open Plan N15 hardware recycled-phase pilot results and prior N35 arithmetic-positive/negative research remain untouched.

**Interpretation and next boundary:** 23 source quantum qubits without changing dynamic arithmetic/source quantum instrument is a tangible design improvement, while a **robust native CZ/depth speedup is NOT established**, a single physical phase-wire mapping remains unproved, and real N35 hardware feasibility/QPU validation does NOT exist. The next concrete issue is tracing compiled source logical phase through native routing and midcircuit measure/reset/condition blocks; pursue this read-only before any hardware attempt. Do not confuse Qiskit original source width, 156-width padded target compiler view, or distinct touched physical sites with actual on-device simultaneously needed resources or ability to solve RSA.


## 2026-10-24 — TRUE 23q N35 phase initial Fez site85 pinned 12/12; phase SWAPs still move to 3–8 sites, physical fixed-site gate FAIL; zero QPU

**Research lead Chase Lunsford / CaMaLabs.** This continues the [true N35 23-source-qubit one-recycled-phase midcircuit feedback](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md) and latest [actual Qiskit routed source-phase SWAP-token lineage](QRR_N35_23Q_ROUTED_PHASE_LINEAGE_RESULT.md). True source phase1/work6/other16 live helpers after deleting nine independently proven actually idle scratch source wires; b4/6/8 classical output gates measured/reset and IQFT if_else feedback, previously archived exact ideal IQFT outcomes and source quantum gate phases. Prior original routed CPU Fez target results traced 12/12 source-phase token and final native dynamic event addresses, verified 196 conditional PhaseGate-vs-native quantum Operators up to ONLY measured-classical-history branch-global phase, but native phase operations occupied 2–7 physical addresses. Existing real N15 Open Plan phase recycling pilot remains a separate actual QPU success; NO N35 hardware job is authorized. Native full-circuit hard heuristic CZ≤800 AND depth≤2000 still vastly failed.

**NEW preregistrated experiment:** [N35 23q original phase site85 initial-layout frozen protocol](QRR_N35_23Q_PINNED_PHASE_SITE_PREREG.md), prereg commit **`ab00c3a9bc03596ec784bb6b833f41fe5612cc40`** BEFORE new target scoring. Same exact arithmetic/source public base2 and cube8 × b4/b6/b8 × seeds509 and8776=**12 fixed cases**, Qiskit~=2.5.2/runtime~=0.47, Fez authenticated TARGET READ only, opt1. ONE intervention: request `initial_layout` mapping original Qiskit source `recycled_phase[0]` to **physical Fez site85**, and test whether it remains stationary for all measure/reset/if_else, full compiler routed token and native quantum phase matrices, no hardware execution.

**First [CPU CI 40145027852](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145027852) FAILED BEFORE native science**: Qiskit rejected the incomplete partial `initial_layout={phase:85}` because other original source qubits, e.g. `work[0]`, had no initial mapping. The [amended prereg](QRR_N35_23Q_PINNED_PHASE_SITE_PREREG.md) before any native score prespecified a non-tuning Qiskit API-repair: first obtain normal exact original `init+layout` full 23-source-qubit mapping with same public source/seed/target, then swap ONLY phase source assignment with incumbent source at physical85 (or leave original source vacancy) and hand Qiskit the full 23-virtual-qubit permutation. All other Qiskit routing/SWAP, ISA compiler/seed, source arithmetic and frozen site85 unchanged; **do not conceal this first failed attempt or describe it as physics**.

[**Original successful fixed two-arm six-case GitHub Actions source run 40145166136**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145166136) **2/2 SUCCESS**; all **12/12 native CPU ISA compiles** completed, all **12/12 source phase start pins EXACTLY at physical 85** and all source logical phase tokens independently tracked through real compiler staged `swap` instructions and final `measure/reset/if_else` physical addresses. **All 196/196 actual compiled native classically conditional quantum PhaseGate→RZ Operator checks matched** up to measured-history branch-global phase and prior classical control order. Phase token traveled **8–89 phase-moving routed SWAPs PER case**, and final dynamic phase operations used **3–8 distinct physical sites**. Consequently **ZERO of 12** strict no-physical-movement/fixed-site criteria pass; **ZERO of 12** have all dynamic phase events at 85. Pinning only the *initial* layout does NOT enforce fixed-site hardware phase recycling.

| Public N35 b/seed | Original unpinned archived CPU CZ/depth | New site85 initial-pin native CPU CZ/depth | Phase-moving SWAP count | Native distinct phase dynamic sites |
|---|---|---|---:|---:|
| base2 b4 s509 | 29353 / 65641 | **29375 / 67210** |30|3|
| base2 b4 s8776 | 29223 / 68106 | **29477 / 67531** |17|4|
| base2 b6 s509 | 44038 / 101597 | **44229 / 102970** |19|5|
| base2 b6 s8776 | 44313 / 102275 | **45075 / 103270** |77|4|
| base2 b8 s509 | 59690 / 137015 | **61539 / 141149** |89|8|
| base2 b8 s8776 | 59730 / 138953 | **60645 / 138584** |77|4|
| cube8 b4 s509 | 14857 / 34038 | **14907 / 34385** |8|3|
| cube8 b4 s8776 | 15036 / 34595 | **15816 / 35767** |33|3|
| cube8 b6 s509 | 14857 / 34038 | **14907 / 34385** |8|3|
| cube8 b6 s8776 | 15036 / 34597 | **15816 / 35767** |33|3|
| cube8 b8 s509 | 14857 / 34038 | **14907 / 34386** |8|3|
| cube8 b8 s8776 | 15036 / 34599 | **15816 / 35767** |33|3|

**CAUSAL COMPARISON CAVEAT:** numerically pinned CZ exceeds archived unpinned CZ for all12, and zero pinned native layouts are better in both CZ/depth, but **archived unpinned results were NOT newly compiled side-by-side against the SAME backend object**. Qiskit's newly derived unpinned preliminary phase initial layout differs from prior archived staged-routing `initial_layout` for various rows (e.g. base2 b4 s509 now77 vs previously90, cube8 b4 s8776 now1 vs previously85). Do NOT causally attribute gate changes only to pinning; they may include different target metadata or pass/layout-stage behavior. The **physical phase token moved / final ISA dynamic events at multiple sites** in every new compiled pinned result is independently valid regardless of old baseline native cost and proves failure of strict frozen fixed-site hypothesis.

[**Independent ORIGINAL source artifact audit/preservation CI 40145320774**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40145320774) **SUCCESS**, downloaded original two JSONs WITHOUT rescoring/compiler, reconstructed actual source phase token positions SWAP-by-SWAP interleaved with routed events and verified exact final native physical addresses, all196 native conditional operator success receipts, all12 original CZ/depth, initial pins, minimal source layout changes, original source dynamic quantum/classical instructions, frozen hardware gate and QPU0. Exact unchanged original artifacts `results/ibm_shor35_23q_initial_phase_site85/qrr_n35_site85_pinned_base{2,8}.json` committed. [Full report](QRR_N35_23Q_PINNED_PHASE_SITE_RESULT.md), [experiment](../hardware/qrr_n35_23q_pinned_phase_site.py). All prior real and simulated research successes/failures and attribution remain intact.

**Conclusions:** (a) TRUE one-logical-phase 23-source-qubit quantum recycling remains provably represented at SOURCE and Qiskit SWAP-token compiler level, (b) initial pin physical85 SUCCESS 12/12, (c) **strict stationarity / all measure-reset-feedback at ONE physical device site FAIL 12/12**—a genuinely constrained phase-preserving routing algorithm, not a one-qubit `initial_layout` preference, is needed to enforce that property, (d) **native hard resource gate CZ≤800 and depth≤2000 FAIL ALL12**, even best cube8 14,907CZ/34,385depth. **ZERO real N35 IBM QPU hardware jobs, free Open/paid runtime, physical latency/fidelity, on-device factor extraction or RSA/cryptanalysis gain**. Next if investigating placement cost must freeze genuine same-target-snapshot paired pinned/unpinned compilers; if investigating fixed-site target, explicitly design/test a routing constraint that forbids phase token SWAP movement rather than assuming initial placement is permanent. Arithmetic simplification remains by far the more serious obstacle to N35 QPU feasibility.


## 2026-10-25 — Dark Star N25 exact same-order audit (CPU-only; rigorous negative results preserved)

After the completed independently SHA-frozen N25 8-row ideal online-CF/CCX test (0 bounded wins, 0 bounded losses, 6 inconclusive, 2 undefined), recorded and ran a **separate exploratory post-hoc deterministic mechanism test**, without reusing the QPE scorer or submitting any quantum hardware jobs. [Protocol](DARK_STAR_N25_EXACT_ORDER_DOMINANCE_PROTOCOL.md), [result](DARK_STAR_N25_EXACT_ORDER_DOMINANCE_RESULT.md), [full machine receipt](../results/dark_star_ptp/dark_star_n25_exact_order_dominance.json), [GitHub Actions success #40270627654](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40270627654). Source manifests/order identities and eight original cases untouched.

**Proven secondary conclusions:** when gcd(3,r)=1, odd cubing does not change the uniform ideal eigenphase distribution, and public online CF/GCD acceptance matches exactly for every QPE measurement y because z^3=z mod N for z^2=1. This removes sampling uncertainty from the success-path coupling. In 2/8 rows (N=20,088,463 base29, N=32,295,103 base17), **all 24 source-CCX stages cost strictly more with the cube**: stagewise minimum coupled attempted-session ratios >=1.0053045 and >=1.0027691, respectively; the latter was the only surviving case under the fixed B47/rho64 classical budget. In 2/8 other rows (N=29,256,449 base5, N=28,787,333 base11) the known order/trivial-root math proves both bases incapable of factor extraction via this specific strict even-order CF/GCD route; thus a cost *per factor* is undefined, not a positive opportunity. Three changed-order cases remain undecided, and one same-order row has one cheaper cube stage, so stagewise dominance alone does not classify it. All eight reported, zero censorship.

Reproducibility: exact proof implemented and cross-checked with 6,720 exhaustive y tests over 20 small same-order cases (13 nontrivial cubes) and 142 denominator/176 measurement matches for EACH of four same-order N25 cases. **Explicit guardrail:** this is a post-hoc mechanistic follow-up; original N25 0/0/6/2 *preregistered* classifications unchanged. Deterministic source-level CCX inequalities are NOT native physical device or paid/free quantum runtime results. All runs ZERO IBM QPU and ZERO paid runtime. This is a valuable rigorously negative milestone, not evidence of ML-KEM/RSA breaking.


## 2026-10-25 — Dark Star N25 exact 96-shot prefix theorem: three rigorous cubic source-CCX regressions

After first proving the exact same-order distribution/factor-verifier identity, froze and executed a **separate post-hoc cumulative pathwise cost audit** for *every one of the 96 possible stopping-shot positions* of the existing 4-shots × 24 phase-stage model. Protocol: docs/DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_PROTOCOL.md; code: hardware/dark_star_n25_prefix_dominance.py; complete 8-row receipt: results/dark_star_ptp/dark_star_n25_prefix_dominance.json; report: [DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_RESULT.md](DARK_STAR_N25_SHOT_PREFIX_DOMINANCE_RESULT.md); [successful CPU Actions #40271034234](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40271034234). ZERO IBM QPU and zero paid runtime, original first-test scores and all earlier results unchanged.

**Milestone:** 3/8 factor-capable N25 cases where cubing preserves r have **strictly higher** cubed cumulative source CCX at *all* 96 possible stopping points, proving no cubic structural cost win for those cases under the ideal coupled-eigenphase model. Their exact worst-case pathwise cube/plain ratios are >=1.00906785897 (N=20,088,463 a29), >=1.00536176319 (N=28,811,323 a31), and >=1.00849849253 (N=32,295,103 a17). The second is NEWLY RESOLVED despite one individually cheaper cube stage, because the accumulated earlier disadvantages dominate. The last is the only original survivor of the deliberately small B47/rho64 classical budget. A fourth same-order N25 has 96/96 higher cube cost but is provably incapable of factor extraction by either base; no finite per-success ratio is asserted.

Combined with the preceding exact witness argument, exactly **two** N25 cases are fixed-base factor-incapable, **three** same-order factor-capable cases are now structurally dominated by plain, and **three** order-reducing factor-capable cases remain unclassified for cubic end-to-end gain. Important: this is a stronger post-hoc model theorem, **not** a rewrite of the originally preregistered 0 bounded wins/0 bounded losses/6 inconclusive/2 undefined QPE numerical test, not a native quantum hardware gate claim, and not a Shor cryptanalytic breakthrough. This is a preserved negative result from the user's Dark Star quantum optimization program.


## 2026-10-27 — Dark Star N25 changed-order conditional source CCX break-even audit: 3 order-reducing factor-capable candidates still unproven

**Lead:** Chase Lunsford / CaMaLabs. Following the completed original independent SHA-frozen N25 **8-case** online-CF + structural source modular-arithmetic test (0 preregistered bounded cubic wins, 0 losses, 6 inconclusive, 2 undefined), the exact same-order source-cost theorem certified three factor-capable cases where cube always costs more structural source CCX at EVERY 1..96 possible coupled stopping position, and a separate exact factor-verifier witness test found two incapable fixed-base cases. **All older results stay intact**, including successful IBM Fez real Open Plan N15 recycled-phase trial, separate full N35 CPU-only arithmetic/true reused logical phase experiments and negative source arithmetic cases. As of checking the repository on 2026-10-27, the most recent previous Actions run **40271034234** (October 26 UTC) had succeeded; no new jobs were active.

**New separate preregistered post-hoc deterministic calculation:** [protocol](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_PROTOCOL.md), original freeze git **`6026440498f130ca471894f1d538904f560bc392`** BEFORE scoring, [source](../hardware/dark_star_n25_changed_order_break_even.py), [full independently verified report](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_RESULT.md), exact original source-run receipt [`results/dark_star_ptp/dark_star_n25_changed_order_break_even.json`](../results/dark_star_ptp/dark_star_n25_changed_order_break_even.json). All eight same N25 cohort cases and exact original SHA manifest `66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7` fixed. Calculate exact rational public source CCX costs at every width **m=4,6,...50** and **96 fixed-workload prefixes** (4 shots per width); separately cross-check the cumulative shot sums against independently weighted stage sums. For a standalone repeated *fixed-width* model, cube wins source CCX per success only if its **true public CF/GCD factor-success probability ratio** `p_cube/p_plain` STRICTLY EXCEEDS `CCX_cube/CCX_plain`, and any public online verifier CPU work must be counted separately. Neither success ratio is measured by this new secondary audit. **Because the orders differ, DO NOT interpret fixed 96-shot source work cost ratios as true adaptive early-stop per-factor runtime or expected-cost ratios.**

| Three factor-capable, order-reducing N25 cases | Exact validation-only order a→a³ | Cube cheaper structural stages | Cubed/plain 96-shot FIXED WORKLOAD source CCX |
|---|---|---:|---:|
| N=20,508,127, a=3 | 854,124→284,708 | 0/24 | **1.0131532358** |
| N=24,467,873, a=3 | 12,228,930→4,076,310 | 0/24 | **1.0111317204** |
| N=28,064,303, a=13 | 1,753,308→584,436 | 2/24 (m42,44) | **1.0074703383** |

Every one of 96 **fixed-workload** cumulative source CCX costs is greater for cube in all three cases, but distinct order/phase distribution means an increase in factor-success probability could still offset this. At fixed phase width **m50** standalone stage source CCX break-even success-probability multiplier thresholds are **1.009986816, 1.005259732, 1.002877020** respectively. All 24 exact rational stage targets preserved in original JSON. Fourth order-reduced N=29,256,449/a5 remains **factor-incapable for both bases** under this verifier and has undefined per-factor ratio, despite numerical cost ratios; all four same-order original controls preserved. Original statistical 0/0/6/2 classification is NOT rescored. **This is secondary post-hoc mathematical cost accounting, NOT an independent new population, not quantum success measurement, no native IBM Fez device resource test or factor-recovery demonstration.**

[**Original ZERO-QPU source+arithmetic independent within-run CI 40467868224**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40467868224) **SUCCESS**, independently checked all 8×96 original source cost fraction outputs, SHA+exact previous results and no hardware methods. [**Separate original source JSON archival/audit CI 40468006478**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40468006478) **SUCCESS**, fetched ORIGINAL JSON artifact without recomputation, cross-checked all 768 exact ratios against immutable original costs, all 8 classifications and correct conditional interpretation, and committed original unchanged machine bytes. **ZERO real IBM QPU jobs, free Open Plan or paid Runtime consumed.**

**Next necessary move** for Dark Star validity: a new *PUBLICLY preregistered* semiprime+base cohort, classically prefiltered with a genuinely metered useful budget, followed by on-demand CF/GCD success-rate tests and source+verifier cost comparison without selecting samples on hidden validation orders. Do not claim current conditional break-even thresholds themselves are factor-advantage evidence.


## 2026-10-28 — NEW SHA-frozen N25 post-B47/rho64 public m50: 2/4 bounded cubic ideal fixed-width source-cost-per-factor model wins, zero QPU

**Research lead / attribution: Chase Lunsford / CaMaLabs.** This new test follows [the original N25 eight-case success-probability break-even audit](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_RESULT.md), whose strict scientific conclusion was only conditional structural CCX break-even thresholds, **NOT measured probability ratios**: 3 factor-capable changed-order cases have greater cube source CCX under all 96 **fixed-workload** shot prefixes and no demonstrated end-to-end advantage. The old manifest SHA `66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7` and all original results were kept intact. Previous real IBM Fez N15 Open Plan phase-recycling pilot remains independent.

**Frozen BEFORE scoring:** [`DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_PROTOCOL.md`](DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_PROTOCOL.md), original commit `fc7e4a4eb641a31932b3a375aacb44409b9669d6`. This protocol sets 4 **NEW N25 semiprime N/base cases**, public SHA N selection/independent base-rotation salts, exactly 2 survivors each N mod3=1/2, max200 ranked candidates/group; ranks use only PUBLIC N and base, NO factor/order/witness or QPE. Run actual B31 `classical_cascade`, followed by full metered fixed public `Pollard p−1 B47, Floyd rho64 (seeds2/3), prime trial≤97`; accept only cases unsolved under BOTH fixed public budgets (does NOT imply difficult classical factoring). Exclude original eight N.

**Independent pre-scoring public manifest freeze:** [source `hardware/dark_star_n25_fresh_cf50_public_manifest.py`](../hardware/dark_star_n25_fresh_cf50_public_manifest.py), [public-only original CI **40657655151**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657655151) SUCCESS, [original public full screened ledger `dark_star_n25_fresh_cf50_manifest.json`](../results/dark_star_ptp/dark_star_n25_fresh_cf50_manifest.json) was in main BEFORE any order or QPE scoring. New selected SHA `a136789dcdcbb32730f293973805f8edacf5d684d8350c2e51c665db0099d629`. G1 25 public screens produced 10 B31 solved +13 later B47/rho64 solved +2 survivors; G2 2 public screens both survived: **4 genuinely public-budget-unsolved N/base pairs** with original ranks 19/25/1/2: N19774537/a29, N28467259/a31, N29915783/a29, N24556361/a23.

**Fixed post-freeze model:** One m=50 phase width with **16,384 coupled new-SHA pseudo-IID ideal QPE phase/head-bin samples per plain a and cube b=a³ modN** for every new N, total **131,072 ideal simulated phase outcomes**; new sampling salt `QRR-N25-CF50-FRESH-PHASE-20261028`. Public **ON-DEMAND measured-y CF/GCD** `online_factor_cf`, no precomputed factor-producing denominators; exact p/q/orders disclosed ONLY AFTER public freeze to sample ideal QPE eigenphases, never used by the measured-y public verifier. Short exact original verifier cross-check **1680/1680** per row. Same old 65 QPE head bins with conservative omitted-tail ≤1/63. Nominal simultaneous 99% Hoeffding per-arm bound `p∈[max(0,h−eps),min(1,h+eps+1/63)]`, eps `sqrt(log(2*8/.01)/(2*16384))`; a model-sampling bound, NOT real quantum probability or directed-rounding certification.

**Independent source arithmetic cost** from the existing genuine `stage_arithmetic_count(N,base,50)['ccx']`, not native Fez CZ: approximately 41 million **structural SOURCE** CCX per modeled fixed-m50 attempt. Public online CF denominator/modpow/GCD operations logged separately and NOT added to CCX without unit conversion. Source cost expected per independent repeated factor success is `C/p` ONLY at this single fixed width; cubing is lower expected *source-only* cost if `p_cube/p_plain>C_cube/C_plain`, NOT because order alone shrinks or reduces depth and NOT for adaptive 24-stage policies.

[**Four source jobs original Actions **40657959490**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657959490) **4/4 SUCCESS** (each prechecked frozen manifest, original online verifier, exact one-phase sampler), original completed result artifacts, zero IBM SDK/Runtime. [**Separate independent original byte-preservation and mathematical CI audit **40658211255**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658211255) **SUCCESS**: downloaded ORIGINAL 4 source-run artifacts and rechecked all 131,072 head-sample count input records, factor/order identities after freeze, public B31+B47 budgets, exact source cost `Fraction` break-even, nominal bounds and classifications, no QPE re-sampling; committed original untouched files `results/dark_star_ptp/n25_fresh_cf50/n25_fresh_cf50_index{00..03}.json` and independently generated aggregate [`dark_star_n25_fresh_cf50_all_4.json`](../results/dark_star_ptp/dark_star_n25_fresh_cf50_all_4.json). Full [original report](DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_RESULT.md).

| Four NEW N25 public N/base | Validation-only order plain→cube | Head successes plain→cube / 16384 | Original source CCX per m50 shot plain→cube | 99% nominal interval `p_cube/p_plain` | Conclusion |
|---|---|---|---|---|---|
| 19774537/a29 | 9882818→9882818 | 7325→7325 | 40939341→41169698 | [0.904,1.106] | inconclusive |
| 28467259/a31 | 7114126→7114126 | 7631→7631 | 40900461→41053362 | [0.908,1.102] | inconclusive |
| **29915783/a29** | **14952360→4984120** | **4139→6335** | 40925171→41236298 | **[1.311,1.757]** | **bounded_cube_win** |
| **24556361/a23** | **3068304→1022768** | **5356→8190** | 41095307→41343785 | **[1.355,1.702]** | **bounded_cube_win** |

For the 2 factor-capable changed-order cases, the **observed head success ratio is ~1.53×** while source-CCX cube/plain cost ratios are only **1.0076023** and **1.0060464**. The nominal conservative success-ratio lower bounds **1.311** and **1.355** beat those respective cost break-evens. The two same-order controls have identical coupled head counts but slightly higher cubed source CCX and wide bounds, thus **inconclusive**, not falsely certified loss. All four were factor-capable under post-freeze public-witness validation. **PREDECLARED MODEL SIGNAL GATE PASSED:** 2/4 bounded model wins, zero bounded losses, ≥2 capable. This is *small-sample within-cohort conditional ideal model evidence*, **NOT a hardware or quantum speedup**.

**Relevant contemporaneous contrast**: another [separate fresh N25 post-B47rho eight-case aggregate](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_all8.json) on an independently frozen distinct cohort SHA `e46425355e422ff32d167920d7ddc80ada0ed8733c73048912133db6f79526d2` found **0 bounded wins, 4 inconclusive, 4 factor-incapable/uncertified**, its own preregistered staged model gate FAIL. Its *24 widths/4 shots/stage/4096 per-stage* model differs from this ONE m50 16384-shot model, so these are neither directly pooled nor a replication of the positive fixed-width model. In aggregate these studies **DO NOT support a general cubic advantage claim**, and the original negative eight-case research records all remain unchanged.

**Hardware feasibility strictly unchanged:** all modelled N25 source CCX costs are ~41 million per shot and are **NOT** equal to native Fez CZ; there is no compiled 25bit circuit/native ISA/fidelity result and NO REAL N25 QPU factoring. 25bit N are easy on ordinary CPUs regardless of public fixed-screen survivors. **ZERO real IBM QPU jobs, ZERO Open free or paid Runtime, ZERO secrets leaked.** Appropriate next falsification: a new larger publicly frozen sample with a phase-width-adjusted actual online-factor success estimate and an explicitly priced adaptive stopping/controller policy, or measurable gate-level arithmetic costs, without cherry-picking the 2 successes.


## 2026-10-28 — NEW fresh public N25 post-B47/rho64 8-case 24-stage ideal online CF: 0 bounded cubic wins, 4 inconclusive / 4 factor-incapable, zero QPU

**Lead/attribution: Chase Lunsford / CaMaLabs.** This is a NEW preregistered PUBLIC cohort, not rescoring our previous original eight N25 outcomes or post-hoc cost ratios. Before starting, the prior original [N25 on-demand CF+source structural cost test](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_RESULT.md) reported **0 bounded wins /0 bounded losses/6 inconclusive/2 undefined**, but **7 of 8** old cases were actually solved in advance by a stronger public B47/rho64/trial97 filter. Later exact N25 post-hoc audit [changed-order CCX break-even](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_RESULT.md) found three factor-capable order3-reducing examples where cubic *costs more source CCX* in a fixed 96-shot workload, and the hypothetical success ratio necessary to overcome that loss was unknown. The present science improves cohort nontriviality *relative only to the published narrow classical filter*, not cryptographic hardness.

**Fresh protocol frozen BEFORE any public selection, order inspection or QPE scoring:** [`DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_PREREG.md`](DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_PREREG.md), original prereg commit **`aac41888337b7c2fb07b4c9855d14feba757f79b`**. Construct same 80,200 publicly known unique 25-bit synthetic semiprime N candidates from discarded prime pairs, exclude ALL previous 8 N, SHA-rank publicly with NEW population salt and separate base salt, 4 cases in each N mod3 group, fixed base pool (2,3,5,7,11,13,17,19,23,29,31), evaluate **ACTUAL existing B31 classical cascade** then **ACTUAL B47 Pollard p−1 + seeds2/3 Floyd rho max64 + trial≤97** on each B31 survivor, keep first four unsolved/group from at most1200 ranks. No p,q, hidden validation-only order, factor-success status, gate cost or synthetic QPE used in selection. New public manifest frozen on GitHub **BEFORE** any QPE job: [original public SHA freeze Actions **40657776029**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657776029) SUCCESS and [original selection complete ledger JSON](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_manifest.json) independently verified, **group G1 screened 137 / G2 screened 85**, all 8 new survivors passed both public cost filters. **Exact frozen new selected SHA** `e46425355e422ff32d167920d7ddc80ada0ed8733c73048912133db6f79526d2`. No overlap with old8 or separate concurrently preregistered four-case fresh m50 cohort. The new eight public (N,a) pairs are (18291577,19), (32028229,19), (32170573,19), (32536033,19), (21546281,19), (21667697,29), (28445861,19), (33112721,19). **Seven a19, one a29**, a substantial base concentration from public filter/hash selection, LIMIT generality; no outcome-driven post-selection.

**Frozen model:** reuse UNCHANGED existing [on-demand CF/GCD and reversible source gate-cost model](../hardware/dark_star_n25_online_qpe_arithmetic.py) from previous experiment using thin [wrapper](../hardware/dark_star_n25_post_b47rho_fresh_score.py) to bind only NEW archived public manifest SHA, independent new phase-randomness salt and output; full exact **24 widths m4,6,...50**, **4096 pseudo-IID ideal phase samples/arm/width**, 4 modeled shots per width, 65-bin head + explicit conservative omitted-tail mass, nominal original empirical Bernstein H/T intervals with alpha0.01 over family1536, old intended sequential adaptive expected source CCX per factor envelopes and unchanged classification. Public on-demand verifier receives ONLY measured synthetic y and N,a, checks CF candidate d, pow(a,d,N), and gcd(a^(d/2)±1,N), **no O(N) factor-certificate precomputation**. Public B31+B47rho pre-QPE execution and separate online denominator/pow/GCD counts recorded, distinct from quantum source CCX. Private factors and validation-only order are allowed **only AFTER sample freeze** for ideal eigenphase generation and strict factor-witness checks; cubic order identity checked exactly.

[**Original eight independent CPU-only SHA-frozen QPE model shards + original merge Actions 40658075317**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658075317) **9/9 SUCCESS**, with old **1,680 on-demand verifier-vs-direct factor selftests per shard**; saved 8 complete ORIGINAL JSONs `results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_index00.json` through `index07.json`, plus untouched original merged `results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_all8.json`. [**Separate independent original artifact audit and SHA-preservation Actions 40658465772**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658465772) **SUCCESS**, downloaded original eight source-run artifacts without resampling or running QPE, byte-compared each to original committed shard, checked all **8×2×24=384** arm-stage source model entries, source semantic/CF proof receipts, 4096 samples/stage, public SHA/exclusion/selection ledger, source comparator and independent interval-classifier reconstruction, all classical verifier operation sums, exact order3 relation and zero quantum hardware. Independently preserved original 8 artifact SHA hashes in `results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_original_audit.json`. Complete [result report and original N/base table](DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_RESULT.md).

| Frozen fresh eight-case N25 SOURCE model outcome | Result |
|---|---:|
| Public fixed B31+B47/rho64 filter survivors entering ideal QPE | **8/8** |
| True source model bounded cubed a³ wins | **0** |
| True source model bounded cubed losses | **0** |
| Original source sequential CCX-per-success **inconclusive** | **4** |
| Original source fixed-base factor-incapable/undefined | **4** |
| Validation-only factor-capable cases | **4** |
| Factor-capable r reduced by cubing | **3** |
| Preregistered ≥3 bounded-win original model gate | **FAIL** |
| Executed real IBM QPU jobs / Open minutes / paid runtime | **0 / 0 / 0** |

The 4 capable cases are N32170573/a19 (same order, inconclusive), N32536033/a19 (order 5420718→1806906, inconclusive), N21546281/a19 (10768482→3589494, inconclusive), N33112721/a19 (16550106→5516702, inconclusive). Original conservative *source CCX per-factor* cube/plain interval examples: `[0.378,2.177]`, `[0.357,2.260]`, `[0.332,2.204]` respectively: **NONE have upper<1**, so **no bounded winner**, even though lower bound is favorable. Four other cases are mathematically factor-incapable under THIS fixed-base strict witness, not under other bases/classical algorithms; report undefined success ratios. No 25-bit QPU hardware run, no native IBM Fez CZ gates, no measured latency/fidelity, no cryptanalysis break or scalable factoring demonstration. The 25-bit semiprimes are trivial for unrestricted classical factoring; surviving a deliberately narrow fixed-cost filter is NOT hardness.

**Concurrent distinct scientific result MUST NOT BE HIDDEN:** a [separately precommitted four-case FRESH m50 public-survivor study](DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_RESULT.md), independently original-audited CI [40658211255](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658211255), found **2/4 bounded model cubic SOURCE-CCX cost-per-factor wins** for independent 25bit N at ONE fixed m50 with **16384 ideal samples/arm** and Hoeffding+bounded tail, and no previous/new N overlap. That is a legitimate *different estimand*: fixed-width independent attempts versus our 24-stage adaptive cumulative cost/envelope, and different cohort/precision/samples. It does NOT contradict the current 0/8 adaptive bounded result and must NOT be pooled or called replication/device evidence. Both ZERO QPU. The original genuine real IBM Fez Open Plan N15 recycled-phase result remains separately preserved.

**Next useful direction:** frozen larger **base-diversified fresh public B47/rho64 survivor cohort**, compare m50 fixed-width on-demand CF/GCD per-success probability AND full adaptive expected-source-CCX cost on EACH SAME public N, with robust source/detection and separate metered online verifier CPU work. Preserve 8+4 independent positive/negative cohorts and all old original reference data. No automatic real QPU, no Open/paid runtime, no RSA-scale claim.


## 2026-10-28 — Unified Dark Star original PTP + classical + odd-power + adaptive recycled Shor end-to-end CPU integration

**Lead/original project:** Chase Lunsford / CaMaLabs. **New independent algorithm integration only, not an independent new factor-population experiment**. The earlier PTP 210/kernel/symmetry/Fermat positive and falsified claims, N209/N713 conditional Shor model positives, and frozen N22–N25 cube win/inconclusive/factor-incapable/model-loss observations remain unchanged.

[Protocol](DARK_STAR_UNIFIED_END_TO_END_PROTOCOL.md) committed before code; [Unified algorithm](../integrations/darkstar_hybrid/darkstar_unified.py), [Unit tests](../integrations/darkstar_hybrid/test_darkstar_unified.py), [complete scientific report](DARK_STAR_UNIFIED_END_TO_END_RESULT.md). Original [CI first run 40658837229](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658837229) **SUCCESS**. Improved PUBLIC-ORDER multi-exponent fallback and unit test [CI 40659074991](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40659074991) **SUCCESS**, including original immutable JSON results of [N=209](../results/dark_star_unified/unified_demo_N209.json), [N=713](../results/dark_star_unified/unified_demo_N713.json), and [N=781](../results/dark_star_unified/unified_demo_N781.json). **ZERO IBM QPU shots/jobs and ZERO free/paid IBM runtime**.

**Unified runnable program:** derive 48 modulo-210 PTP roots/24-or-28 root-pair rows; keep mirror symmetry annotation but NEVER unsafely drop factor pairs; compare conventional trial/wheel210/LFK kernel methods; use public gcd, power2 chain, budgeted ordinary and 105/15015-residue Fermat midpoint, B31 Pollard p−1, rho64 and prime<=97 before requiring a quantum model. Predeclared odd-power options L=1,3,5,7,105,1155,15015; public PTP-conditioned L3 if N%3==2 then fallback through fixed exponent sequence; no hidden-order selection. Recycled iterative and wide-architecture phase models share ideal quantum outputs but have different simultaneous LOGICAL phase width. A physically separate, **simulated** true-order/eigenphase generator gets synthetic p/q, while factor-recovery sees only public (N,base,measured y,m); on-demand CF even-d direct modular verification and proper gcd, followed by safe PTP pair validation. Up to 65 analytically weighted centered bins with missed-tail events never credited as factor success. Source modular multiplication CCX/CX/CSWAP counted; no native physical routing measured.

**Three end-to-end proof-of-function synthetic cases:** classical-first genuinely recovers **209=11×19** and **713=23×31** in 1 ordinary Fermat square test each, and **781=11×71** through a separate PTP 105-midpoint step after the ordinary 12-test cap; all three are **classically solved before hypothetical quantum**. For the deliberately separate ideal-QPE counterfactual arms, 209/a3 plain missed its 28-shot cap (3,658,744 source-CCX) vs L3 succeeded in 10 shots (730,594); cannot compute a valid savings per successful factor with a failed baseline. For 713/a19, plain and cube both succeeded in 27 vs 18 simulated shots, 7,366,012 vs 3,778,140 modeled source-CCX (one deterministic seed, not an expectation or hardware win). For 781/a29 the public mod3 selector correctly leaves a unchanged; separate L7 succeeds in 8 simulated shots vs L1 18, illustrating an opportunity **not identifiable by the frozen simple public selector** (do NOT cherry-pick L7 retrospectively). Full wheel210 often beats the stagewise combinations in actual classical work; for 781 spending 12 ordinary Fermat checks then 4 PTP checks is more total tests than 14 ordinary Fermat would need, so there is **no net end-to-end speedup claim**.

**Boundaries:** valid PTP symmetry table transforms are not proof of fixed-N factor-equivalence; public PTP validates factor roots post-GCD but isn't an online phase-order oracle. Large-odd-exponent side-effect gcd discoveries are classical. The small-case ideal phase head can omit tails; these are logged as unmodeled failure, not secretly successful outcomes. Source CCX and logical qubit-width model are not native CZ/depth, real noisy recycled QPU, actual factoring speedup or RSA/ML-KEM attack. The simulator takes factors because this is **self-generated toy-benchmark validation**, never because private factors are a permitted preprocessing input. CI successes demonstrate coherent code integration and exact factor checks, not practical quantum advantage. The next scientifically valid gate is fresh public-only N samples after explicit classical processing budgets and complete matched PTP/non-PTP and wide/recycled noisy-native comparisons.


## 2026-10-28 — Fresh N26 unified Dark Star end-to-end 12-case held-out population (PREREG SELECTED BEFORE SCORING; zero QPU)

**Research lead** Chase Lunsford / CaMaLabs. New, frozen [N26 prereg](DARK_STAR_UNIFIED_N26_FRESH_POPULATION_PREREG.md), [public manifest](../results/dark_star_unified/unified_n26_public_manifest.json), source-row SHA256 **`0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939`**, distinct two-prime N 26-bit not used in the earlier N25 cases; 12 public N/base rows, six Nmod3=1, six Nmod3=2, ranked by SHA from 185,661 public-N candidate frame. Public sample freeze [GitHub Actions **40659871113 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40659871113) committed **before** any validation-only factors/orders, public classical outcomes, or quantum costs were calculated.

[**All 12 independent scoring jobs and strict original SHA/artifact merge SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40660172585), source: [new N26 scorer](../integrations/darkstar_hybrid/darkstar_unified_n26_holdout.py), [complete verified report](DARK_STAR_UNIFIED_N26_FRESH_POPULATION_RESULT.md), [merged small summary](../results/dark_star_unified/unified_n26_all_12_summary.json), 12 full original receipts `results/dark_star_unified/unified_n26_original_00.json` through `_11.json`. **ZERO IBM QPU and ZERO paid/free IBM Runtime**.

**Main end-to-end result (negative):** 11/12 were fully factored classically within the unified preflight (3 PTP midpoint15015, 3 PTP midpoint105, 2 Floyd rho64, 2 Pollard p−1 B31, 1 ordinary Fermat). Exactly one N=49,273,331 (frozen base17) exhausted this *particular* bounded classical prefilter; then the *ideal simulated* publicly controlled conditional L3 policy recovered correct factors 4703×10477 using public CF/GCD after 87 phase attempts in the first seed. All twelve were nonetheless classically factored with the independent conventional wheel210 AND PTP LFK/kernel full-search controls. **No demonstrated practical factoring speedup**, no claim that the classical survivor is hard or that its simulated quantum source was real hardware.

**Separate diagnostic / NOT QPU result:** eight precommitted pseudorandom seeds per each of seven **fixed public** odd exponents (1,3,5,7,105,1155,15015), 12 frozen cases, counterfactual ideal QPE with honest unmodeled tails, on-demand strict public CF/GCD plus PTP validation, and source clean-MCX CCX/CX/CSWAP. Plain and always-cube both recovered 88 factors out of 96 per-arm model sessions (one distinct N unresolved 0/8 for either); aggregated source CCX from ALL attempts 160,257,888,003 plain vs 142,998,156,168 cube (10.77% less for this finite ideal-model cohort). Conditional public Nmod3 selector cost 150,270,511,956 source CCX (6.23% below plain, worse than unconditional cube); 10/11 factor-capable cases descriptively favored cubing, one factor-capable order-preserving case cost more, one model-incapable case has **undefined** cost-per-factor. Higher smooth exponents L1155/L15015 each found a CLASSICAL shortcut in one of the 12 rows: their 80/88 quantum-model sessions cannot be compared directly to 88/96 without charging that classical work. All numerical gains are **descriptive, non-certified** eight-seed pseudorandom ideal model source-operation savings, NOT hardware/cryptographic quantum advantage. The simple public selector still has NOT been validated as reliable. Recycled vs wide phase controls report modeled logical peak-width only, not physical QPU.

**Persisted milestone:** One formerly separate PTP period-210 table/kernel/midpoint/wheel/symmetry-safe classical branch and Dark Star odd-power/adaptive recycled Shor branch now compose into one repeatedly tested executable without private factor/oracle leakage in public algorithms, across a **fresh** larger sample. Exact prior N25 negative model conclusions and favorable earlier N209 small-model results remain separately logged. Next rigorous gate must make end-to-end classical cost fair to optimized conventional factoring and produce complete-tail/numerically bounded expected-value model before claiming more.


## 2026-10-28 — Recovered original Dark Star v2 midpoint pruning — exact N26 re-audit, original table equivalence, and revised 12/12 classical exit

**Research lead:** Chase Lunsford / CaMaLabs. User identified that the recent unified project may have partially lost its original highly effective **PTP composite-specific Fermat midpoint pruning**. This is now objectively confirmed and restored—not just described. The original Dark Star v2 method coupled factor residues via `q=N p^{-1} modM` and jumps between viable `x=(p+q)/2 modM`; previous median M15015 result had ~28.8× fewer integer square tests but end-to-end throughput 0.84× (table setup dominated). The N26 unified algorithm had retained only M105/M15015 midpoint stages limited to **12 exact square tests each** and omitted the stronger M255255 prime mask search.

[Frozen BEFORE restoration code, evaluation protocol](DARK_STAR_N26_RESTORED_MIDPOINT_PRUNING_PROTOCOL.md), [safe public QR implementation](../integrations/darkstar_hybrid/midpoint_qr_pruner.py), [first 12-row exact audit](../integrations/darkstar_hybrid/darkstar_midpoint_pruning_reaudit.py), [full report](DARK_STAR_N26_RESTORED_MIDPOINT_PRUNING_RESULT.md). [GitHub Actions **40801569711 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40801569711) and immutable machine [receipt](../results/dark_star_unified/unified_n26_midpoint_pruning_reaudit.json). Uses all twelve originally frozen public N26 cases, original SHA `0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939` (NOT a new holdout). **181,440 exact wheel-membership checks** agree with original M105 and M15015 inverse-pair tables for all 12 original Ns, zero false pruning, all exact correct original factors recovered. M15015 median **22.75×** reduction in exact square roots vs plain Fermat; stronger M255255 median **47×** fewer costly exact square roots. M255255 end-to-end setup+search timed faster than conventional wheel210 on **7/12** but original PTP LFK method only **6/12**; strict >6/12 against BOTH baselines **FAILED**. The microbenchmark timing is noisy and abstract operation types are different; **no practical algorithm-wide speedup proved**.

**Critical original N26 correction:** `N=49,273,331=4703×10477` was the single old 11/12 classical gate survivor only because legacy M15015 needed **14** allowed root tests and old cap was **12**. Ordinary Fermat needs **571**, M105 needs **64**, M15015 needs **14**, M255255 needs just **8** exact square roots over the same 571 candidate midpoint positions. The NEW public-only QR implementation needed **985 cheap quadratic-residue membership checks** plus 8 root tests, within BOTH the 4096-x-span and 12-root cap. This is a real classical operation-pruning result; **does not imply wall-time faster than wheel**, and N was never classically cryptographically hard.

[Unified pipeline code](../integrations/darkstar_hybrid/darkstar_unified.py) now contains the safe bounded `restored_midpoint_QR_255255` stage following the old classical filters. [Separate after-update classical replay](../integrations/darkstar_hybrid/darkstar_n26_restored_classical_replay.py), [GitHub Actions 40801831973 SUCCESS](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40801831973), [new original-byte record](../results/dark_star_unified/unified_n26_midpoint_restoration_classical_replay.json): **original first-run classical gate 11/12; updated after-pruning classical gate 12/12**, exactly ONE changed method, all other original methods and actual prime factors match, and all original counterfactual QPE source outcomes remain unchanged and separately saved. No real IBM QPU, no paid or free IBM Runtime, no claims of factoring quantum advantage. Preserve user-origin method attribution and negative end-to-end speed benchmarks.

**Other pruning distinguished:** N35 public `pow(a,2^k,N)==1` identity-controlled-modmul elision is mathematically valid and remains a separate hardware-source track, while 32→23 recycled source qubits via 9 proven idle scratch wires failed its original robust native CZ/depth performance gate; neither should be asserted as a scalable native gate advantage without independent validation. Next scientifically meaningful gate: new independent public selected cohort with RESTORED classical stage precommitted and cost comparison with conventional wheel/LPK + PTP LFK, then separately test exact public identity gate pruning in the generic arithmetic source model.


## 2026-10-28 — BOTH requested follow-ups: independently frozen N27 restored-pruner holdout plus public identity-U source pruning

**Research lead:** Chase Lunsford / CaMaLabs. Two separate CPU-only studies, **zero real IBM QPU or paid/free IBM Runtime**, no changes to original N25 or N26 receipts. [Combined preregistration](DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md) preceded both; first **new** public-only 27-bit input population was independently committed before any factoring, true orders, model outcomes or source-gate checks. Public selected N/base SHA256: **`12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10`**, twelve 27-bit squarefree semiprimes ranked from 292,399 synthetic candidate N in 2 groups (6 Nmod3=1, 6 Nmod3=2). [Public manifest](../results/dark_star_unified/unified_n27_restored_public_manifest.json), [selection Actions **40811162116 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811162116).

### Track A — first truly fresh restored-pruning end-to-end N27 population

[Full independent report](DARK_STAR_N27_FRESH_RESTORED_END_TO_END_RESULT.md), [implementation](../integrations/darkstar_hybrid/darkstar_n27_restored_holdout.py), [complete 12-case summary](../results/dark_star_unified/unified_n27_restored_all_12_summary.json), twelve original per-case files `results/dark_star_unified/unified_n27_restored_original_00.json` through `_11.json`; [**full CPU Actions **40811563655 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811563655).

**Verified scientific conclusion:** all **12/12** 27-bit public inputs successfully factored by a priori public classical-first method **without** reaching the quantum stage: 4 old M15015 midpoint stage, 4 M105 stage, 1 Pollard p−1 B31, 3 Floyd rho64. The final restored stronger M255255 QR gate was available in every case but not reached because an earlier stage solved each. Both independently complete wheel210 and PTP LFK benchmarks factor **12/12**. The whole preflight's full-run median wall time (5 repeats, same runner including setup and preceding failed stages) beat wheel210 on only **4/12** and PTP LFK on only **4/12**; hence **NO practical factoring speedup**. This also prevents crediting hypothetical model QPE as necessary quantum work.

Three predeclared, seeded (20261028,20262037,20263046) ideal QPE counterfactual sessions each for plain and public cubic 27-bit bases: both model arms factor-producing **24/36 sessions** (4 original moduli 0/3 each and undefined per-factor ratio); aggregate *source* CCX plain **99,925,111,990**, cube **94,622,162,391** (5.31% less on this small descriptive sample). Not a statistical model confidence guarantee, native hardware cost or practical advantage. Public conditional policy references these existing original runs rather than fabricating new independent outcomes. Original public CF/GCD and PTP post-verifier consume only N/base/y/m. Retain every negative case.

### Track B — independent exact public-multiplier identity-U source circuit optimization

[Full independent report](DARK_STAR_N27_PUBLIC_IDENTITY_U_PRUNING_RESULT.md), [auditor](../hardware/dark_star_n27_public_identity_source_audit.py), [opt-in corrected source-level gate counter](../hardware/dark_star_recycled_scalable_arithmetic_audit.py), [152-original-configuration JSON](../results/dark_star_unified/unified_n27_public_identity_U_source_audit.json). First Actions **40811424129 failed due Python import entrypoint**, not model; corrected [Actions **40811595809 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811595809) confirmed and committed originals, no hidden-order selectors or QPU.

**Exact result:** 152 source-level configurations checked (32 small anchor plus 120 fresh original N27 N/base/m pairs) and 714 exhaustive small residue/control identity checks. When publicly computed `a^(2^k)%N==1`, omit controlled U_1 as intended permutation identity; no measured phase, true order or private factor. At N35 cube base8 m4 multipliers [8,29,1,1], 2 identity rounds permit exact model deletion **9,828 CCX of 20,295** (48.4% source-cost reduction for that example). Across ALL 32 historical small anchors 237,918 CCX saved from 3,231,563 counted, but across the 120 new N27 source configurations **no identity multiplier occurs and 0 CCX saved**. Original unpruned source counter intentionally retained for historical repeatability; new counter opt-in only, and no physical qubit, native CZ, routed depth or fault-tolerant claim is made. Original N35 32→23 unused scratch elimination FAILED robust native multi-seed CZ/depth gate and must not be conflated.

**Bottom line:** Both experimental tracks were actually run, scientifically audited, committed and preserved. Original periodic prime-table pruning is active and safe, though the latest fresh N27 sample needed no late M255255 branch and still fails end-to-end speed gate; public identity-U quantum pruning works algebraically on short-order anchors but returns an honest **zero** improvement on the tested larger public population. The next valid step is preregistering a cheap PUBLIC cost-based classical router against a new independent cohort, with separately compiled native circuit identity/noise/route tests only for suitable small demonstrators; never imply hardware advantage from abstract source gates.


## 2026-10-28 — Two independent Dark Star N27 milestones: restored classical holdout and identity-U null

**Research lead:** Chase Lunsford / CaMaLabs. Both studies were frozen separately in [preregistration](DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md), and **original fresh N27 public inputs were SHA-frozen before any factoring, order inspection or QPE model evaluation**, [successful freeze run 40811162116](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811162116). Public sample SHA `12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10`; twelve selected from 292,399 synthetic 27-bit semiprime N values, six per N mod3 group.

**Track 1 — Independent fresh 27-bit unified factoring:** [Original verified CPU Actions 40811563655](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811563655), [full report](DARK_STAR_N27_FRESH_RESTORED_END_TO_END_RESULT.md), [merged summary](../results/dark_star_unified/unified_n27_restored_all_12_summary.json), all twelve detailed JSON receipts `results/dark_star_unified/unified_n27_restored_original_00.json`–`_11.json`. **12/12 actual classical-first factorizations**, methods PTP midpoint 15015 (4), PTP midpoint 105 (4), Pollard p−1 B31 (1), bounded rho64 (3). The newly restored M255255 late stage found none **because all were already solved by previous fixed public stages**, not because invalid. Standalone conventional wheel210 and PTP LFK both solved 12/12, and five-repeat FULL unified classical-first median timing was faster than wheel210 in only **4/12** and PTP LFK only **4/12**. **No practical speedup or real quantum need demonstrated.** Separately, with **three fixed seeds per arm** (all counterfactual ideal-QPE, even when N classically solved), plain and cubic each recovered 24/36 factors with total *original source-level* CCX **99,925,111,990** vs **94,622,162,391** (5.31% descriptive saving for cube) but **four rows generated zero factor recovery in either arm**; no finite per-success ratio for these rows, no certified statistical model win, and no real QPU.

**Track 2 — Independent public identity-controlled-modmul source pruning:** [Successful CPU-only Actions 40811595809](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811595809), [complete report](DARK_STAR_N27_PUBLIC_IDENTITY_U_PRUNING_RESULT.md), [152-case original receipt](../results/dark_star_unified/unified_n27_public_identity_U_source_audit.json), implementation [source counter opt-in](../hardware/dark_star_recycled_scalable_arithmetic_audit.py) and [auditor](../hardware/dark_star_n27_public_identity_source_audit.py). Public `pow(base,2**k,N)==1` implies controlled modular multiply is identity, so it can be removed with no hidden multiplicative order. Original `stage_arithmetic_count` is **unchanged** to preserve prior results, and opt-in `stage_arithmetic_count_public_identity_pruned` counts only the nonidentity round costs. **152** configurations, **714** exhaustive small semantic checks: 32 historical anchors (12 with positive savings, 237,918/3,231,563 source CCX saved collectively, 7.36% weighted), **120 fresh N27 plain/cube configurations with ZERO identity rounds and ZERO saved source CCX**. At N35 a8 m4, public multipliers [8,29,1,1] permit exact removal at k2,3: source CCX **20,295→10,467** (saving 9,828 or 48.4%) **only in this toy source gate model**. First Actions 40811424129 failed Python direct-script import path before scientific checks; corrected module entry point and original science 40811595809 passed. Does **not** demonstrate compiled native CZ/depth, physical width or gate savings; prior N35 32→23 idle-scratch-pruning native robustness gate failed separately and is preserved.

**Overall status:** Both tracks completed, verified, committed as separate evidence and reports; negative results retained. **No IBM QPU jobs, no free or paid IBM Runtime**. Next step, if continuing: precommit a public-only low-cost *classical-first route selector* that avoids expensive failed prefix stages and benchmark against full standalone wheel210 and PTP LFK on a new original population; do not confuse it with identity-U source pruning or repeat this same cohort as an independent new holdout.


## 2026-10-29 — Fresh N28 publicly selected classical cost-router primary PASS (16 original fresh 28-bit semiprimes, CPU only, ZERO QPU)

**Research lead:** Chase Lunsford / CaMaLabs. **Preregistered** fixed [cost-router method sequence](DARK_STAR_PUBLIC_COST_ROUTER_N28_PREREG.md), source [darkstar_public_cost_router.py](../integrations/darkstar_hybrid/darkstar_public_cost_router.py) frozen git blob `4420a5d5d83869ccc41ab2396cde15d84f98a4c1` **before** any new public cohort selection; original [16-case manifest](../results/dark_star_unified/darkstar_public_router_n28_frozen_manifest.json), canonical SHA256 `9f8cd1d83b3bcfdfce9c41ceda05621b52c9e9076d7cdc2dec36bc24598b7a51`, SHA-ranked from 562,219 synthetically constructed N28 public semiprime candidates, 8 per public N mod3 group, in separate [successful freeze Actions run **40892476026**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40892476026).

[Full original 16 × 8 repeated, interleaved source evidence](../results/dark_star_unified/darkstar_public_router_n28_original_16_holdout.json), [complete verified report](DARK_STAR_PUBLIC_COST_ROUTER_N28_RESULT.md), [CPU GitHub Actions **40892932977 SUCCESS**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40892932977) and tests. Every N28 factor verified, no private factors/orders in public router selection. Fixed sequence: divisibility by 2/3/5/7, 8 Fermat midpoints, deterministic batched Brent Pollard rho with public c1/seed2 max256 modular squarings then c3/seed3 max128, conditional public proximity-gated PTP quadratic-residue M255255 limited 128 midpoints and 8 exact root tests, and **complete wheel210** fallback. Full baseline wheel210, PTP LFK kernel, previous fixed full preflight and 4096-window Fermat all measured on same 16 N with eight rotated order repetitions each, including all previous failures and factor validation.

**New primary classical speed result PASSED** its prospective >=9/16 wins against EACH full wheel210 and full PTP/LFK: successful router factors **16/16**, measured per-N median router latency faster than full wheel210 on **16/16**, faster than full PTP LFK on **13/16**, faster than prior expensive fixed full pipeline on **12/16**. Median *casewise* router/wheel runtime ratio **0.31544** (~3.17x); versus PTP LFK ratio **0.35504** (~2.82x). No selective exclusions; source and original 16 full raw case receipts archived.

**Critical mechanism boundary:** **15/16 actual factors found using STANDARD BRENT POLLARD RHO**, one (N=204,445,411) by short early Fermat; **zero** by late PTP M255255 or wheel fallback. This is a *classical method-ordering and implementation* positive versus the repository's limited Python wheel/LFK baselines, **not novel PTP mathematics, Shor or quantum advantage, asymptotic factoring improvement, or real-world cryptographic factoring speedup**. No comparable standalone optimized Brent baseline yet: **do not** claim the router itself beats simply running Brent rho alone. Eight repetitions in microsecond-scale GitHub runner are noisy. The earlier N26 restored-PPT exact pruning improvements and prior N27 null gates remain separately frozen and unchanged. ZERO IBM hardware jobs, zero paid/free runtime. After archiving this milestone, next fair secondary audit should test exact standalone Brent-with-wheel versus this router on the SAME original cohort strictly labeled **post-hoc**; then prospectively evaluate on new different-size semiprimes.


## 2026-10-29 — N28 secondary exact standalone Brent control: incremental router advantage FAIL (same original 16 cases, post-hoc, ZERO QPU)

The original **preregistered** N28 positive wheel/LFK comparison (`docs/DARK_STAR_PUBLIC_COST_ROUTER_N28_RESULT.md`) and all original SHA-frozen 16-case records were committed **before** this secondary control, and are **NOT** revised. [Post-hoc secondary protocol](DARK_STAR_N28_ROUTER_VS_STANDALONE_BRENT_SECONDARY_PROTOCOL.md) freezes a stricter and FAIRER actual mechanism comparison versus **standalone Brent rho using the exact identical algorithm and original fixed public budgets** (c1/seed2 256 modular squarings + c3/seed3 128, preceded by same 2/3/5/7 wheel small-prime checks and followed by same full wheel210). The only intended extra methods in router are its eight early Fermat midpoint trials and the conditional never-reached PTP QR search; the control does not look at prime factor truth. All sixteen **same** originally frozen public N28 cases re-run with eight rotated interleaved Python timings, raw results archived, SHA inputs and router immutable source verified.

[Original successful secondary GitHub Actions **40893476655**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40893476655), [complete report](DARK_STAR_N28_ROUTER_VS_BRENT_SECONDARY_RESULT.md), [machine raw all sixteen, all eight repeats](../results/dark_star_unified/darkstar_n28_posthoc_router_vs_brent_control.json). All factors recovered by both methods **16/16**; standalone Brent itself factored **16/16 without wheel fallback**. Router beats identical standalone Brent in median time only **1/16**, vs predeclared secondary >=9/16 speed gate (**FAIL**). Median per-case router / same Brent runtime ratio **1.071603** (~7.16% SLOWER). This is a scientifically important **falsification of the hypothesis that the current public routing overhead makes standard Brent faster** on this toy N28 cohort; the original primary positive result versus conventional wheel210 (16/16 wins) and PTP LFK (13/16 wins) remains true but now properly attributed to using **established Brent Pollard rho early**.

Do NOT claim an incremental novel Dark Star PTP, Fourier, classical geometric or quantum advantage from N28. The user-origin periodic-table midpoint pruning is mathematically valid and can eliminate many expensive integer square-root tests in other test conditions, but neither original N28 nor this secondary shows faster overall factorization than a competent rho baseline. No true hardware, QPU, paid/free Runtime, native gate benefit, asymptotic or cryptographic factoring claims. Future truly new cohort must compare to optimized Brent from its ORIGINAL preregistration, not add it only afterward.


## 2026-10-29 — Fresh N32 factor-separation PTP pruning versus optimized Brent original holdout — prospective result, PTP primary FAIL / mixed FQ secondary PASS (properly limited)

**Research lead:** Chase Lunsford / CaMaLabs. The last N28 comparison showed that the routing policy was actually ~7% slower than standalone same-budget optimized Brent (router 1/16 wins), so this genuinely NEW test preregistered optimized Brent as a primary baseline **before freezing its 32-bit cohort**. [Exact prereg and frozen original thresholds](DARK_STAR_N32_SEPARATION_VS_BRENT_PREREG.md), [separate original public input freeze successful GitHub Actions 40991779058](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40991779058), [original 24-row public manifest](../results/dark_star_unified/darkstar_n32_separation_frozen_manifest.json), canonical SHA `82ae5b25791967188418bcf7ab6fb3be24b6d43209bc18dbb6da392de86e5c0b`. Three prospectively constructed synthetic-factor-separation strata, 8 each: near Fermat midpoint D=0..8; middle D=64..640; far D=4096..16384. Prime factors generated strata for **experiment selection only**, kept out of public N-only factoring functions and outcome measurements until verification after all timed benchmark calls. All 24 N are fresh 32-bit synthetic semiprimes, never the previous 28-bit cases.

[New public-only complete B (strong Brent+wheel fallback), F (Fermat8+B), Q (safe PTP M255255 QR 2048 midpoint positions/96 root cap+B), FQ (both+B), wheel210, PTP LFK and bounded plain Fermat source](../integrations/darkstar_hybrid/darkstar_n32_separation_vs_brent.py), [independent tests](../integrations/darkstar_hybrid/test_darkstar_n32_separation_vs_brent.py). First CI [40991915820](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40991915820) **failed before any scientific case was scored** on a manifest field-name-only mismatch `stratum` vs frozen `group`. Fixed just reader; no protocol, budget, cohort, method or outcome re-selection. [Successful full original Actions **40992002589**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40992002589), [unmodified 24-case original all-gate and all-nine-timing receipt](../results/dark_star_unified/darkstar_n32_separation_vs_brent_original_24_results.json), [full scientific report](DARK_STAR_N32_SEPARATION_VS_BRENT_RESULT.md). **24/24 exact factors** verified under all six complete methods; nine rotated interleaved microsecond Python timings per case/arm; all modular work, mask prep and failed route costs counted; zero IBM QPU, no paid/free Runtime.

**Original PRIMARY PTP-specific strict middle gate FAILED**: required Q faster than BOTH baseline standalone strong optimized Brent (B) and early Fermat8+Brent (F) in >=6/8 each predeclared middle cases. Actually **5/8 vs B and 5/8 vs F**. Q/B median casewise latency ratio middle **0.7794** (~22% lower descriptive median) but not a strong stable majority. Q QR sieve directly factored all eight middle cases with 1–9 exact sqrt tests after 90–535 x probes, yet overhead sometimes exceeded Brent. **Near 0..8**: Q beat Brent 8/8, but **lost to ordinary F in 8/8** because Fermat8 alone catches all eight very quickly (median F/B ratio 0.0355 vs Q/B 0.1581). **Far 4096..16384**: Q beat Brent 0/8, scanned its full 2048 x window with ~3200–5100 modular membership tests before falling back to Brent, and was **median 5.829× slower** than Brent. This validates the necessity of recognizing when QR work is worth doing.

**Original SECONDARY mixed FQ+Brent overall timing threshold passed exactly 13/24** versus the prereg minimum 13/24; this is **not** a standalone PTP win: 8 near cases are factored by standard early Fermat BEFORE invoking QR, five middle cases improve with QR, and all 8 far cases lose to Brent. Synthetic stratum labels are NOT available to a public N-only factorizer; no robust public predictor or general speedup has been demonstrated. Do NOT infer an unknown semiprime's true closeness using hidden p/q labels. The strong Brent baseline remains hard to beat systematically. Clear separation of successful operation pruning and failed full-cost test maintained. Historical N25–N28 positive and negative milestones untouched. Next scientific task would precommit a public-only economical routing predicate and evaluate on a NEW N33/34 cohort, never retroactively stratum-select.


## 2026-10-29 — Prospective N33 cheap public QR-density predictor fails under fresh strong Brent and fixed QR controls

**Research lead** Chase Lunsford / CaMaLabs. Original preregistration and policy both committed **before** the new experiment: [policy and gates](DARK_STAR_N33_PUBLIC_ADAPTIVE_QR_PREREG.md), [public-N-only fixed router](../integrations/darkstar_hybrid/darkstar_n33_public_adaptive_qr.py), source Git blob `431d1e8d8e3120c78415dcae226cb521be652732`. **New** [33-bit original public N-only population frozen in a separate successful Actions run 41005291111](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41005291111), [manifest](../results/dark_star_unified/darkstar_n33_adaptive_qr_public_frozen_manifest.json), SHA256 `6ad065cef19f01bd44da35dec101cc45432f398ce4b404362fcd7e87f801859c`. Exact **24 fresh synthetic semiprimes**, eight per near D=0..8, middle D=64..640, far D=4096..16384 construction groups. Population uses hidden p/q only to *construct and label* synthetic separation groups, not within any real factorization route: algorithm receives N and fixed method label only; validation p/q/D reconstructed only AFTER all public timings.

[Successful scored/verified GitHub Actions **41005485140**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41005485140), [complete scientific report](DARK_STAR_N33_PUBLIC_ADAPTIVE_QR_RESULT.md), [raw all-24 case / seven-method / nine interleaved timing source receipts](../results/dark_star_unified/darkstar_n33_adaptive_qr_original_24_result.json); [standalone semantic tests](../integrations/darkstar_hybrid/test_darkstar_n33_public_adaptive_qr.py). ALL six complete classical methods correctly factored **24/24** exact semiprimes. No actual IBM QPU or paid/free runtime.

The **prospective public-only predictor** A tested small-prime divisions, 8 exact plain Fermat midpoints, a true 64-position public QR pilot, and then extended expensive QR through x offset +639 iff **at most two of the 64 pilot positions passed all six small-prime QR masks**. Remaining unfactored N went to same fixed strong Brent c1+1024 squares / c3+512 squares and complete wheel fallback. Preregistered compare to complete standalone Brent B, Fermat8+Brent F, fixed fullQR+Brent Q, wheel W, PTP/LFK L, bounded Fermat M. All per-run QR mask construction, modular checks, failed routes and cleanup charged. Nine interleaved timing repeats per arm and N, all original measurements preserved.

**Original PRIMARY routing gate FAILED:** A faster than standalone Brent on only **14/24** (minimum **15/24**) and faster than nonadaptive full QR Q only **2/24** (minimum 15/24). Near group A>B **8/8**, A>Q **0/8**, all factors early Fermat and no QR needed. Middle A>B **6/8**, A>Q **1/8**, A extended QR in **7/8** and actually found factors via QR **7/8**, descriptive median A/B runtime ratio **0.6757**. Far A>B **0/8**, A>Q **1/8**, selected extended QR **8/8**, recovered ZERO via QR, descriptive median A/B ratio **2.2541**. **Original SECONDARY public selection gate FAILED:** required ≥6/8 middle A>B (met), ≥4/8 middle QR extension (met), and ≥6/8 FAR QR skips (**0/8 achieved**). Qualifying QR residue density in the initial pilot is **not** a useful predictor of unknown true factor-pair separation: almost all far tests had 0 or1 eligible short-window candidate, so the proposed sparse residue heuristic chose an expensive search for all far rows. Important middle exception N=7,334,956,339 had 3 initial survivors and was incorrectly sent to Brent even though fixed full QR would recover its D=85 midpoint. This is a decisive negative routing result, not a failure of the mathematically safe residue pruning itself.

**Scientific interpretation:** The user's earlier PTP/Fermat midpoint modular pruning remains formally correct and recovered 7/8 middle-stratum factors under this public QR test. But **no public-only proximity predictor or practical total-work speedup against strong Brent has yet survived prospective tests**, and no quantum advantage demonstrated. Do not mistake synthetic construction group metadata for available public information about an arbitrary unknown N. Next logical test (only with independent new prereg/cohort) is an *anytime resource scheduler* using public computation/failure events rather than pretending local QR-residue density predicts factor separation; must compare Brent/Fermat+Brent/fullQR+Brent with full accounting and record nulls. Preserve earlier N32 partial positives and strict failures without revision.


## 2026-10-29 — N34 original anytime resumable Brent/PTP checkpoint experiment falsified — exact state-machine validated, no end-to-end routing win

**Research lead:** Chase Lunsford / CaMaLabs. After the previous fresh N33 QR density public predictor **failed** both performance and far-rejection gates, this next prospective study tested a new **truly resumable**, non-restarting Brent/segmented-PTP scheduler, not a heuristic based on hidden factor separation. [Precommitted N34 schedule and pass gates](DARK_STAR_N34_ANYTIME_INTERLEAVED_PREREG.md), [immutable public-N-only source](../integrations/darkstar_hybrid/darkstar_n34_anytime_scheduler.py), source Git blob `afdc1e69a94ebfdd7d73fd2b6d5ada6d8c589753`. A uses 8 exact early Fermat checks; Brent c1 state checkpoints **96,384,1024** polynomial squarings interleaved with PTP M255255 exact quadratic-residue offset windows **8..71, 72..199, 200..639**, with fresh N masks and hard total QR root cap64; then identical c3 Brent max512 and full wheel fallback. All comparisons use the same stateful Brent engine; none has a hidden p/q, true D, group label or multiplicative order.

[Separate successful public-selection/freezing GitHub Actions **41016927212**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41016927212), [frozen original 24 N34 public-only manifest](../results/dark_star_unified/darkstar_n34_anytime_public_frozen_manifest.json), original SHA `b0ff1c6cc46e5db8d3e5ff8c841c9b01b40e027646e4734d43cb7665afa68bd2`. Eight new N34 synthetic semiprimes in each construction-only prime separation group near D=0..8, middle D=64..640, far D=4096..16384 (candidate frames **801,218 / 4,630,744 / 16,555,967**); prime factors used only for experimental generation and AFTER public timings for scientific verification, never public factoring/routing. Exact pause/uninterrupted source-level rho correctness and factor tests passed before freeze.

[Successful original scorer/independent verification Actions **41017105426**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41017105426), [full 24-case original JSON with all seven arm original traces and nine rotated timing samples each](../results/dark_star_unified/darkstar_n34_anytime_original_24_result.json), [complete scientific report](DARK_STAR_N34_ANYTIME_INTERLEAVED_RESULT.md), [source controls](../integrations/darkstar_hybrid/test_darkstar_n34_anytime_scheduler.py). **ALL 24/24 factors recovered correctly** under all six complete public algorithms (A anytime, B standalone Brent+wheel, F Fermat8+B, Q fullQR+Brent, independent W wheel210, L PTP LFK). A single c1 Brent state truly resumed, with no lost or repeated work: independent 24-case tests proved **identical factor outcomes, modular-square/product/GCD counts and stopping phases** versus uninterrupted c1 **and** c3 Brent, on every N. This is a correct engineering milestone but not necessarily a speed advantage. Zero actual QPU, zero paid/free IBM Runtime.

**PREREGISTERED PRIMARY cost gate FAILED** on every component: anytime faster than standalone optimized B **10/24** (required15), than full Q **8/24** (required15), than cheap F+B **5/24** (required13). Group outcomes:
- **Near 0..8**: A>B **8/8**, A>Q **0/8**, A>F **2/8**, median casewise A/B **0.02734**, A/Q **1.34446**. Seven wins are solely ordinary Fermat8 before QR; the eighth has D=8, paid Brent 96 squarings then immediately found its factor in QR's first x position.
- **Middle 64..640**: A>B **2/8**, A>Q **0/8**, A>F **3/8**, median A/B **1.21835** and A/Q **3.04690**. A solved 4 via mid QR but the Brent checkpoints deferred useful QR work while full QR Q could find them earlier; four were factored via Brent.
- **Far 4096..16384**: A>B **0/8**, A>Q **8/8**, A>F **0/8**, median A/B **1.28787** and A/Q **0.79569**. All eight factored through Brent, zero via QR. The interleaving spared the full late-QR penalty of Q but still paid unused masks and 64–192 x midpoint candidate checks, yielding ~29% median overhead vs Brent only.

**PREREG SECONDARY middle/far discipline gate FAILED**: middle A>B minimum6/8, actual2; far A>Q minimum6/8, actual8; far median A/B slowdown must ≤1.25, actual1.28787. Preserve both the genuine correctness of PTP quadratic-residue pruning and the falsification of this implementation's full-cost performance. Synthetic group labels are NOT a valid unknown-N routing input. No novel factorization complexity, real hardware, RSA/ML-KEM break or quantum benefit established.

**Scientific next direction:** stop repeating generic public-QR predictor/checkpoint thresholds without a new math-derived signal. Strong Brent plus optional inexpensive Fermat precheck is the defensible general classical baseline. If original PTP structure offers a new public-only provable distance bound or a structural transform, preregister and falsify that first on a truly independent cohort; alternatively pivot attention to the isolated quantum arithmetic-circuit resource studies, keeping them separate from integer factoring performance. All N25–N33 prior wins and nulls remain archived unchanged.


## 2026-10-30 — Mathematical public midpoint-bound audit, same-wheel-residue falsification, RSA versus ML-KEM scale assessment

**Lead:** Chase Lunsford / CaMaLabs. Following the original failed N33 and N34 public PTP proximity-predictor/scheduler experiments, this task shifted from tuning heuristics to a **proof audit**, avoiding any misrepresentation of fresh holdout performance. [Predeclared mathematical protocol](DARK_STAR_PUBLIC_MIDPOINT_BOUND_MATH_PROTOCOL.md), [exact symbolic/counterexample program](../integrations/darkstar_hybrid/darkstar_public_midpoint_bound_math_audit.py), [independently successful CPU GitHub Actions **41019940060**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41019940060), [machine JSON certificate](../results/dark_star_unified/darkstar_public_midpoint_bounds_mathematical_audit.json), and [full RSA/ML-KEM feasibility and mathematics report](DARK_STAR_PUBLIC_MIDPOINT_BOUND_RSA_MLKEM_ASSESSMENT.md). **Zero IBM QPU or paid/free Runtime in this mathematical audit**; earlier *real* Fez/Shor15 hardware experiment remains valid and is separately documented.

**Provable generic conditional midpoint bound:** for N=pq odd with true p≤sqrt N and **publicly certified p≥L**, the true Fermat midpoint `x=(p+q)/2` is ≤`floor((L²+N)/(2L))` by monotonic f(t)=(t+N/t)/2 on (0,sqrt N]. This is NOT a new small-public bound if L can only be obtained by exhaustive exclusion of small prime factors or by an externally supplied RSA prime-generation interval. The odd wheel coprimality only implies p≥19, giving a grossly loose bound in the worked 30-bit semiprimes.

**Rigorous QR-only negative:** x_triv=(N+1)/2 and y_triv=(N−1)/2 satisfy x_triv²−N=y_triv². For any integer k and M255255, `(x_triv+kM)^2−N ≡ y_triv² mod M`: **an unbounded arithmetic progression always satisfies every necessary small-prime quadratic-residue midpoint mask**, regardless of whether the coordinate is a genuine nontrivial factor midpoint. Thus CRT/PTP QR residue elimination is safe for each candidate but by itself cannot certify a generally close global factor location. Exact constructed prime pairs independently verified:
- N=`922551607=29989×30763`, 30 bit, public N mod 255255=`60037`, true factor midpoint offset D=`2`.
- N=`537116557=8719×61603`, ALSO 30 bit, public N mod 255255=`60037`, true D=`11985`.
Both true midpoints pass all six required QR masks. Hence (bitlength,N mod255255) alone cannot discriminate near versus far, but does not prove impossibility of all other public-N predicates. This is a **constructed illustrative counterexample**, not a new performance holdout.

**RSA upper-envelope reality check:** even if a publicly guaranteed RSA-2048 key-gen interval makes p,q each 1024-bit (ratio q/p<2), Fermat D/√N≤3/(2√2)−1≈0.06066017, leaving *order 2^1020* worst-case midpoint positions. Prior tiny-N isqrt pruning ratios do not make that tractable. QRR's genuine IBM Fez N15 Shor factoring had successful hardware samples and narrower compiled native circuit but is NOT an RSA-2048 fault-tolerant demonstration. N35 32→23 source-wire scratch removal failed its native CZ/depth robustness gate; N27 modeled conditional cubic source CCX saving does not establish physical or scaled advantage. Competitive published RSA-2048 resource estimates require large fault-tolerant hardware under explicit error-correction assumptions.

**ML-KEM separate track reality:** the [LWE_GeometryLab 2026-10-25 reused-basis degree56 synthetic audit](https://github.com/CaMaLabs/LWE_GeometryLab/blob/main/docs/mlkem512_reused_basis_n56_verified_20261025.md) had **1/4** exact posthoc degree56 secret/error recoveries with three 420-second BKZ40 timeouts, not full standardized degree256 ML-KEM-512. The [ideal 4-qubit QRR×actual full ML-KEM public-objective test](https://github.com/CaMaLabs/LWE_GeometryLab/blob/main/docs/mlkem512_qrr_quantum_optimization_verified.md) did not improve the exact local public classical baseline or recover any standardized secret. NIST FIPS203 https://csrc.nist.gov/pubs/fips/203/final still describes module-LWE ML-KEM as believed quantum-resistant. Shor's factoring/order finding advantage for RSA does **not** directly apply to ML-KEM.

**Overall answer to user's explicit question:** neither real-world RSA-2048 nor standardized ML-KEM is close to being broken by the combined research. Never multiply gains from separate experiments as though they were one demonstrated end-to-end factorization/key-recovery speedup. This mathematical negative is a successful research milestone that stops overconfident QR distance heuristics without discarding exact local PTP pruning. Keep all earlier original positive and negative simulation/hardware records untouched.
