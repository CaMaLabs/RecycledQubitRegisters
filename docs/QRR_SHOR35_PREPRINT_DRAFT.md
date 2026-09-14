# Dynamic phase-register recycling and hardware-aware placement for compiled Shor order finding on superconducting quantum hardware

**Author:** Chase Lunsford (CaMaLabs)  
**Status:** preprint draft; not peer reviewed  
**Date:** 14 September 2026

## Abstract

Dynamic quantum circuits can trade simultaneous coherent width for mid-circuit measurement, reset, and classical feed-forward. We study that trade in compiled Shor order finding on IBM superconducting hardware, with emphasis on a non-power-of-two order instance, `N=35`, `a=2`, whose multiplicative order is `r=12`. The modular orbit is encoded exactly in a four-qubit affine basis, while the phase register is implemented either conventionally with eight simultaneous phase qubits or iteratively with one recycled phase ancilla. On `ibm_fez`, the initial eight-bit recycled circuit used 5 logical qubits and 175 CZ gates versus 12 logical qubits and 331 CZ gates for the matched wide circuit. Recycled output showed 40.23% permissive factor recovery, 5.86% strict direct-order recovery, Hellinger fidelity 0.5236 to the exact finite-precision order-12 distribution, and total-variation distance 0.5723. The corresponding uniform-output baselines were 12.89%, 2.34%, 0.2349, and 0.8257. A clean repeat produced 45.51% permissive recovery and 7.03% strict direct-order recovery. A zero-QPU calibration-aware placement search then reduced the recycled circuit to 160 CZ gates and depth 572 and, in a new matched hardware run, improved permissive recovery to 53.71% and Hellinger fidelity to 0.6441 while preserving 7.03% strict direct-order recovery. The wide comparator also improved under the cleaner placement, reaching 20.12% permissive and 3.71% strict recovery, but remained much closer to the uniform reference. These experiments provide reproducible evidence that phase-register recycling, affine orbit compilation, and calibration-aware placement can preserve and improve useful order-finding signal on current noisy hardware. The result is specific to a compiled `N=35`, `a=2` orbit and does not remove the need for scalable reversible modular arithmetic in a general Shor implementation.

## 1. Motivation

Shor's algorithm reduces integer factorization to quantum order finding. In a textbook circuit, quantum phase estimation uses a coherent phase register whose width grows with the desired phase precision. On current noisy devices, that width can become costly for two separate reasons: more active qubits expose the computation to more calibration variation, and a conventional inverse QFT introduces additional entangling gates and routing overhead.

Semiclassical Fourier transforms and qubit recycling are established ideas. The present work asks a narrower experimental question: **for a fixed compiled order-finding problem on current superconducting hardware, can a one-qubit recycled phase register retain more useful algorithmic signal than a conventional wide phase register, after controlling for initial work-register placement and explicitly auditing random-output baselines?**

The experiments were developed progressively rather than around a single favorable run. Earlier tests included exact QPE simulations, matched hardware QPE, `N=15` phase-width scaling, replicated `N=21` order finding, a failed natural-label `N=35` implementation, a low-cost affine re-encoding, a six-bit `N=35` noise-floor result, an eight-bit breakthrough, an unmodified replication, and finally a calibration-aware placement experiment. Failed and null results are retained in the repository.

## 2. Prior work and novelty boundary

Qubit recycling in Shor-style order finding is not new. Martín-López *et al.* demonstrated a recycled control qubit in a compiled photonic factorization of `N=21` [1]. Griffiths and Niu introduced the semiclassical Fourier transform that underlies such iterative constructions [2]. Amico, Saleem, and Kumph later studied compiled Shor circuits for `N=15`, `21`, and `35` on IBM superconducting hardware using a semiclassical QFT; their `N=35`, `a=4`, `r=6` experiment was reported as unsuccessful [3]. Skosana and Tame subsequently demonstrated complete compiled factorization of `N=21` on IBM hardware [4].

Dynamic-circuit hardware has improved substantially. Bäumer *et al.* demonstrated a dynamic QFT on IBM superconducting processors, replacing the two-qubit-gate-heavy unitary QFT+measurement construction by mid-circuit measurement and feed-forward [5]. In August 2026, Wu *et al.* reported a dynamic-circuit Shor implementation on a hybrid superconducting qubit-cavity processor for `N=15` [6]. Thus this work does **not** claim the first qubit-recycling Shor experiment, the first dynamic QFT, or the first dynamic-circuit Shor experiment on any superconducting platform.

The `N=35` literature also requires care. Bagourd *et al.* reported hardware experiments for `N=35` in a broader study of present-day Shor execution. Their `a=4`, `r=6` experiment showed only marginal evidence at their chosen threshold, while a friendlier `a=8`, `r=4` instance showed a statistically significant signal [7]. Separately, Kuk *et al.* demonstrated `N=35`, `a=4`, `r=6` on a classical nonlinear acoustic phase-bit platform and explicitly noted that, at the time of their study, they were not aware of a successful experimental Shor implementation for `N=35` on quantum hardware [8].

Accordingly, the defensible novelty statement for the present work is deliberately narrow:

> **To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware, and the first reported dynamic-circuit `N=35` Shor/order-finding result on a superconducting qubit processor.**

This wording is a literature-search claim, not a proof of priority. It must remain qualified by “to our knowledge,” and it should be re-checked immediately before external submission. This work is **not** the first quantum experiment associated with factoring 35, not the first Shor-style `N=35` hardware study, and not the first dynamic-circuit Shor implementation on a superconducting platform.

## 3. Compiled `N=35`, `a=2`, `r=12` problem

For

\[
N=35,\qquad a=2,
\]

the modular orbit starting from 1 is

```text
1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1,
```

so the order is

\[
r=12.
\]

The standard classical Shor post-processing then gives

\[
2^{r/2}=2^6=64\equiv 29 \pmod{35},
\]

and

\[
\gcd(29-1,35)=7,\qquad \gcd(29+1,35)=5.
\]

Thus successful recovery of the useful even order yields the nontrivial factors `5` and `7`.

### 3.1 Affine orbit encoding

A direct natural-label encoding of the twelve orbit states produced expensive high-order controlled operations. We therefore conjugated the modular orbit into a 12-cycle of a four-bit affine permutation:

```text
4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4.
```

The remaining four computational-basis states form a disjoint 4-cycle and are never populated from the encoded initial state. The mapping preserves the coherent twelve-state orbit exactly.

The required affine powers are implemented by short CNOT/X networks. For an eight-bit phase-estimation sequence, the modular-power sequence is

```text
1, 2, 4, 8, 4, 8, 4, 8,
```

which requires 17 work-register CNOTs and 2 X operations before adding the phase control. Under phase control these become 17 CCX operations and 2 CX operations before backend decomposition/routing. Exhaustive basis-state self-tests verify each affine power map and the complete modular orbit before any hardware submission.

This is a **compiled orbit encoding**. It is not a generic reversible modular multiplier.

## 4. Wide and recycled phase-estimation circuits

The wide circuit uses eight phase qubits plus the four-qubit work register, for 12 simultaneous logical qubits. Each phase qubit controls the corresponding affine modular-power operation, followed by a conventional inverse QFT and terminal measurement.

The recycled circuit uses one phase ancilla plus the same four-qubit work register, for 5 simultaneous logical qubits. For each phase bit, the ancilla is reset, placed in superposition, used to control the corresponding affine modular power, corrected using previously measured phase bits through real-time classical feed-forward, measured mid-circuit, and then recycled for the next bit.

The ideal wide and recycled constructions implement the same finite-precision phase-estimation distribution. The experimental question is therefore not whether the mathematics differs, but whether the resource trade changes the amount of useful signal that survives hardware noise.

## 5. Experimental controls and evaluation

All principal hardware comparisons were run on IBM `ibm_fez`. Within each matched job:

- wide and recycled circuits are submitted together;
- the same four initial physical work-register qubits are enforced for both architectures;
- the recycled ancilla is selected from the same physical region used by the wide circuit;
- both circuits use the same shot count;
- the ideal finite-precision distribution is computed independently;
- uniform random output is evaluated under the exact same classical post-processing.

The transpiler may route logical states away from their requested initial sites during execution, so “same work register” refers to the initial physical placement rather than permanent pinning.

### 5.1 Post-processing metrics

Two factor-recovery metrics are reported.

**Permissive verified-multiple recovery.** Continued-fraction denominators are tested together with bounded multiples, but any accepted candidate must satisfy the modular-order condition and actually produce nontrivial factors. This metric is useful but can have a high random-output baseline.

**Strict direct-order recovery.** Only a continued-fraction denominator that directly produces a useful verified order is counted. This is the more conservative metric used to test whether recognizable order information survives.

For eight phase bits, the exact analytic references are:

| Metric | Uniform output | Exact ideal order-12 distribution |
|---|---:|---:|
| Permissive factor recovery | 12.890625% | 84.939855% |
| Strict direct-order recovery | 2.34375% | 14.975779% |
| Hellinger fidelity to ideal | 0.234867 | 1.0 |
| TV distance to ideal | 0.825713 | 0.0 |

The uniform baseline is important: factor recovery alone is not sufficient evidence when classical post-processing can turn random phase samples into factors at non-negligible rates.

## 6. Results

### 6.1 Six-bit affine boundary result

The affine encoding first produced a major synthesis improvement relative to the earlier natural-label circuit. At six phase bits, the recycled circuit fell from depth 1209 and 388 CZ gates to depth 466 and 137 CZ gates. However, the first six-bit affine hardware run remained at or near the random-output floor under the strict metric. This negative result showed that synthesis cost and phase-resolution discriminability were separate bottlenecks.

An exact finite-precision analysis then showed that eight phase bits offered much stronger separation between ideal and uniform output while adding only two additional low-cost affine modular-power rounds.

### 6.2 Initial eight-bit hardware result

The first eight-bit affine run used 512 shots per architecture.

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 788 | **607** |
| CZ gates | 331 | **175** |
| Permissive factor recovery | 12.50% | **40.2344%** |
| Strict direct-order recovery | 2.34375% (12/512) | **5.8594% (30/512)** |
| Hellinger fidelity to ideal | 0.1951 | **0.5236** |
| TV distance to ideal | 0.8448 | **0.5723** |

Recycled output cleared both factor-recovery baselines and was substantially closer to the ideal distribution than uniform output. Wide landed exactly at the strict random baseline and approximately at the permissive baseline.

For the recycled strict metric, 30 successes were observed where the uniform model predicts 12 in expectation. A fixed-baseline binomial tail gives `p = 6.44e-6` (approximately 5.26 standard deviations under the corresponding normal-score approximation). This is a shot-noise-only calculation and is not a complete hardware error model.

### 6.3 Clean unmodified replication

Before any placement optimization, the exact eight-bit experiment was repeated without changing the mathematical circuit or benchmark settings.

| Metric | Wide | Recycled |
|---|---:|---:|
| Permissive factor recovery | 13.6719% | **45.5078%** |
| Strict direct-order recovery | 2.9297% (15/512) | **7.03125% (36/512)** |
| Hellinger fidelity to ideal | 0.1932 | **0.5394** |
| TV distance to ideal | 0.8399 | **0.5489** |

The strict recycled signal therefore reproduced and strengthened. Pooling the two unmodified recycled runs gives 66 strict direct-order successes in 1024 shots versus 24 expected under the uniform model; a simple fixed-baseline binomial tail is approximately `5.5e-13`. This pooled number is descriptive only because hardware shots can exhibit calibration and temporal correlations not captured by an iid binomial model.

### 6.4 Calibration-aware placement optimization

After the clean replication was frozen, a separate zero-QPU search examined candidate connected physical regions and deterministic transpiler seeds. The search preserved the same initial four work qubits between wide and recycled circuits within every candidate matched plan. Its ranking proxy combined calibrated CZ error, MCM/readout error, compiled CZ burden, depth, and circuit size. The score was used only for candidate selection and was not interpreted as predicted fidelity.

The recommended matched plan reduced recycled resources from 175 to 160 CZ gates and depth from 607 to 572. It also selected a lower-error MCM ancilla and improved the local mean CZ calibration. The wide comparator received cleaner readout sites and lower depth, making the subsequent experiment a stronger comparison rather than an intentionally disadvantaged wide baseline.

### 6.5 Optimized matched hardware result

The optimizer-selected plan was independently recompiled and reproduced the predicted resource counts before QPU execution.

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 746 | **572** |
| CZ gates | 362 | **160** |
| Circuit size | 1453 | **728** |
| Permissive factor recovery | 20.1172% | **53.7109%** |
| Strict direct-order recovery | 3.7109% (19/512) | **7.03125% (36/512)** |
| Hellinger fidelity to ideal | 0.2473 | **0.6441** |
| TV distance to ideal | 0.7957 | **0.3947** |

The placement search therefore improved the broad phase-distribution quality and factor-recovering output while preserving the strict direct-order rate seen in the clean replication. The wide circuit also improved, as expected from cleaner placement, but remained substantially closer to uniform output than the recycled circuit.

The recycled-minus-wide permissive recovery gap in the optimized run was 33.59 percentage points, approximately 11.88 standard errors under a simple independent-binomial approximation.

For the recycled strict metric, 36 successes versus a uniform expectation of 12 correspond to a fixed-baseline binomial tail of approximately `9.7e-9` (about 7.0 standard deviations by the corresponding normal-score approximation). Again, this is explicitly a shot-noise significance estimate, not a full uncertainty model.

### 6.6 Three-run progression

| Run | Recycled permissive | Recycled strict | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Initial baseline | 40.23% | 5.86% | 0.5236 | 0.5723 |
| Clean replication | 45.51% | 7.03% | 0.5394 | 0.5489 |
| Optimized placement | **53.71%** | **7.03%** | **0.6441** | **0.3947** |

The strict signal is therefore present in the initial run, reproduced in an unchanged second run, and preserved under a separately selected physical layout. The optimizer mainly improved the broader shape of the measured order distribution rather than inflating only one narrow success metric.

## 7. Interpretation

The results support three conclusions within the tested compiled setting.

First, **simultaneous coherent width is itself an experimental resource**. The recycled circuit performs the same ideal phase-estimation task while replacing seven of the eight simultaneous phase qubits with classical measurement records and one reused phase ancilla. On current hardware, that reduction can more than compensate for the latency and noise introduced by mid-circuit measurement and feed-forward.

Second, **encoding and hardware placement interact strongly with algorithmic performance**. The natural-label `N=35` implementation was too expensive. An affine change of basis reduced the modular-work synthesis cost enough to expose the phase-register trade. A later calibration-aware placement search improved the measured distribution further without changing the mathematical problem.

Third, **random-output baselines are essential for small factoring demonstrations**. The six-bit experiment looked superficially successful under a permissive factor metric but failed a stricter audit because uniform random outcomes had a high factor-recovery rate. Increasing phase precision to eight bits lowered the random baseline enough to distinguish genuine order structure.

The broader architectural hypothesis is therefore not “two qubits replace a large quantum computer.” It is that a compiler or scheduler should preserve coherence only where it is algorithmically necessary, move measured information into classical state when allowed by the algorithm, recycle scarce physical qubits, and choose the physical region using live calibration data.

## 8. Limitations

The strongest limitations are explicit.

1. **Compiled orbit rather than generic modular arithmetic.** The four-qubit work register exactly represents the twelve states visited by the `N=35`, `a=2` orbit. This is not a scalable modular multiplier for arbitrary `N`.
2. **Small problem size.** Factoring 35 is a hardware benchmark, not a cryptographic result.
3. **Backend dependence.** The current positive result is on `ibm_fez`. Cross-backend validation is the next required experiment.
4. **Calibration and routing correlations.** Shot-noise p-values do not model all hardware correlations, calibration drift, or the effects of optimizer-based placement selection.
5. **No claim of asymptotic algorithmic speedup from recycling.** Iterative phase estimation and semiclassical QFT are established. The contribution is experimental architecture/compiler co-design and measured hardware behavior in this benchmark.
6. **No claim that the optimized wide circuit is globally optimal.** The placement search is finite and heuristic, although it explicitly improves the fairness of the matched comparison.

## 9. Reproducibility and provenance

The public repository retains code, negative results, hardware summaries, run history, and optimizer artifacts. Key files include:

```text
hardware/ibm_shor35_affine_matched.py
hardware/analyze_shor_noise_floor.py
hardware/ibm_shor35_layout_optimizer.py
hardware/ibm_shor35_affine_plan_runner.py
results/hardware/SHOR35_AFFINE_HARDWARE.md
results/hardware/SHOR35_OPTIMIZED_HARDWARE.md
results/hardware/SHOR35_LAYOUT_OPTIMIZATION.md
results/hardware/shor35_affine_8b_run_history.csv
```

The baseline runner was intentionally left unchanged when the placement optimizer was introduced, so the optimized experiment is a follow-up rather than a retroactive modification of the replicated benchmark.

## 10. Next experiment: cross-backend validation

The next test should hold the mathematical benchmark fixed and move to one or more independent dynamic-circuit-capable superconducting backends. For each backend:

1. run a zero-QPU calibration/topology search;
2. freeze the selected matched plan before hardware execution;
3. submit wide and recycled in the same job with the same initial four work sites;
4. retain 512 shots per architecture initially;
5. evaluate permissive recovery, strict direct-order recovery, Hellinger fidelity, and TV distance against backend-independent ideal and uniform references;
6. report failure as well as success.

A cross-backend replication would materially strengthen the claim that the observed advantage is architectural rather than a peculiarity of one Fez calibration region.

## 11. Claim language for external use

### Supported now

> We demonstrate a replicated dynamic phase-register recycling result for a compiled `N=35`, `a=2`, `r=12` Shor order-finding instance on IBM Fez. Recycled execution uses 5 simultaneous logical qubits instead of 12 and preserves strict continued-fraction order signal above an explicit uniform-output baseline across repeated hardware runs. Calibration-aware placement further improves the measured phase distribution while retaining the strict signal.

### Provisional priority statement

> To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware, and the first reported dynamic-circuit `N=35` Shor/order-finding result on a superconducting qubit processor.

### Not supported

Do not claim any of the following:

- first factorization of 35 by any quantum method;
- first Shor experiment on 35 of any kind;
- first use of qubit recycling in Shor's algorithm;
- first dynamic-circuit Shor experiment on a superconducting platform;
- a scalable factorization of arbitrary 6-bit semiprimes;
- a practical attack on RSA or other deployed cryptography.

## References

1. E. Martín-López, A. Laing, T. Lawson, R. Alvarez, X.-Q. Zhou, and J. L. O'Brien, “Experimental realization of Shor's quantum factoring algorithm using qubit recycling,” *Nature Photonics* **6**, 773–776 (2012). DOI: `10.1038/nphoton.2012.259`.
2. R. B. Griffiths and C.-S. Niu, “Semiclassical Fourier Transform for Quantum Computation,” *Physical Review Letters* **76**, 3228–3231 (1996). DOI: `10.1103/PhysRevLett.76.3228`.
3. M. Amico, Z. H. Saleem, and M. Kumph, “Experimental study of Shor's factoring algorithm using the IBM Q Experience,” *Physical Review A* **100**, 012305 (2019). DOI: `10.1103/PhysRevA.100.012305`.
4. U. Skosana and M. Tame, “Demonstration of Shor's factoring algorithm for N=21 on IBM quantum processors,” *Scientific Reports* **11**, 16599 (2021). DOI: `10.1038/s41598-021-95973-w`.
5. E. Bäumer, V. Tripathi, A. Seif, D. Lidar, and D. S. Wang, “Quantum Fourier Transform Using Dynamic Circuits,” *Physical Review Letters* **133**, 150602 (2024). DOI: `10.1103/PhysRevLett.133.150602`.
6. H. Wu *et al.*, “Demonstrating advantages of dynamic quantum circuits on a hybrid superconducting qubit-cavity processor,” arXiv:2608.04780 (2026). DOI: `10.48550/arXiv.2608.04780`.
7. P. Bagourd, J. Jang-Jaccard, V. Lenders, A. Mermoud, T. Hoefler, and C. Hempel, “Practical Challenges in Executing Shor's Algorithm on Existing Quantum Platforms,” arXiv:2512.15330v3 (2025/2026). DOI: `10.48550/arXiv.2512.15330`.
8. I. Kuk, I. B. Djordjevic, K. Runge, I. R. Gabitov, and P. A. Deymier, “Realizing Shor's algorithm with topological acoustic phase bits,” *Communications Engineering* **5**, 60 (2026). DOI: `10.1038/s44172-026-00623-6`.

---

### Internal note before submission

Before posting to arXiv or sending to a journal, repeat the novelty search for the phrases `N=35 a=2 Shor hardware`, `order 12 Shor superconducting`, `dynamic circuit Shor N=35`, and closely related terms. Replace “first reported” if any prior work is found. Cross-backend data should be added as a separate Results subsection rather than replacing the Fez runs.