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
