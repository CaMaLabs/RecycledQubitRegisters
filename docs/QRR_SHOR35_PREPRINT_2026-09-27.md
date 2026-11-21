# Dynamic phase-register recycling and hardware-aware placement in compiled Shor order finding on superconducting quantum processors

**Author:** Chase Lunsford (CaMaLabs)  
**Status:** preprint manuscript; not peer reviewed  
**Date:** 27 September 2026

## Abstract

Dynamic quantum circuits can exchange simultaneous coherent width for mid-circuit measurement, reset, and real-time classical feed-forward. We study that trade experimentally for a compiled Shor order-finding instance, `N=35`, `a=2`, whose multiplicative order is the non-power-of-two value `r=12`. The twelve-state modular orbit is represented exactly in a four-qubit affine basis, while the phase register is implemented either conventionally with eight simultaneous phase qubits or iteratively with one recycled phase ancilla. On IBM `ibm_fez`, the initial matched eight-bit experiment used 12 logical qubits and 331 CZ gates for the wide circuit versus 5 logical qubits and 175 CZ gates for the recycled circuit. The recycled circuit produced 40.23% permissive factor recovery and 5.86% strict direct-order recovery, compared with 12.50% and 2.34% for the wide circuit. A clean unmodified repeat strengthened recycled strict recovery to 7.03%. A calibration-aware zero-QPU placement search subsequently reduced the recycled circuit to 160 CZ gates and depth 572 and yielded 53.71% permissive recovery, 7.03% strict recovery, Hellinger fidelity 0.6441 to the exact finite-precision order-12 distribution, and total-variation distance 0.3947. Cross-backend tests on `ibm_marrakesh` show that the architecture ranking is not universal. In two same-job four-circuit A/B controls, hardware-aware placement improved recycled recovery in both calibration windows, while the optimized wide circuit varied strongly between windows. In the second Marrakesh A/B run, optimized recycled achieved 41.99% permissive recovery and 6.25% strict direct-order recovery versus 16.02% and 2.93% for optimized wide. Across the two Marrakesh jobs, optimized recycled and optimized wide both rose above the strict uniform-output floor, but with different calibration sensitivity. These results support a narrow conclusion: for this compiled order-finding problem, simultaneous coherent width, physical placement, backend topology, and dynamic-circuit overhead interact strongly, and a recycled phase register can preserve useful order information while using substantially fewer simultaneous logical qubits. The experiments do not constitute a scalable general-purpose Shor implementation and do not remove the need for scalable reversible modular arithmetic.

## 1. Introduction

Shor's algorithm reduces integer factorization to quantum order finding. In the textbook phase-estimation formulation, a coherent phase register is prepared, entangled with a modular-arithmetic work register, transformed with an inverse quantum Fourier transform (QFT), and measured. On present superconducting hardware, that architecture can be costly for two related reasons: a wider active register exposes the computation to more heterogeneous physical-qubit errors, and the coherent inverse-QFT construction can add routing and entangling-gate overhead.

Semiclassical Fourier transforms, iterative phase estimation, and qubit recycling offer a different resource trade. Measurement outcomes can be stored classically and fed forward, allowing one physical phase ancilla to be reset and reused for successive phase bits. This reduces simultaneous coherent width, but introduces mid-circuit measurement, reset, conditional control, and additional latency. Whether this trade is favorable is therefore a hardware question rather than a purely circuit-count question.

This work asks a deliberately narrow experimental question:

> For a fixed compiled `N=35`, `a=2`, `r=12` order-finding problem on current superconducting hardware, how does an eight-bit wide phase register compare with a one-qubit dynamically recycled phase register when the work-register encoding, phase precision, initial work-register placement, post-processing, and random-output baselines are controlled?

The study was developed progressively rather than around a single favorable hardware run. The public repository preserves exact simulator checks, failed or noise-floor implementations, matched hardware experiments, clean replications, placement searches, cross-backend controls, and raw-result-derived summaries.

The contribution is not the invention of qubit recycling or semiclassical phase estimation. The contribution is an architecture/compiler/hardware benchmark combining: (i) a non-power-of-two `r=12` Shor order; (ii) an exact affine encoding of a twelve-state modular orbit into four coherent work qubits; (iii) matched wide-versus-recycled dynamic-circuit hardware experiments; (iv) explicit analytic uniform-output baselines under the same classical post-processing; (v) replication on IBM Fez; and (vi) same-job cross-backend layout A/B controls on IBM Marrakesh.

## 2. Prior work and novelty boundary

Qubit recycling in Shor-style order finding is established prior art. Martín-López *et al.* experimentally demonstrated a compiled iterative Shor implementation for `N=21` using a recycled control qubit in a photonic architecture. The semiclassical Fourier transform underlying iterative constructions was introduced earlier by Griffiths and Niu.

Compiled Shor experiments have also been performed on superconducting quantum processors. Amico, Saleem, and Kumph studied `N=15`, `N=21`, and `N=35` on IBM hardware using a semiclassical QFT. Their `N=35` experiment used `a=4` with order `r=6` and did not reliably recover the intended period. Skosana and Tame later demonstrated compiled order finding for `N=21` on IBM hardware.

Dynamic-circuit QFT has separately been demonstrated on IBM superconducting processors by Bäumer *et al.*, who showed that mid-circuit measurement and feed-forward can replace the entangling structure of a unitary QFT followed by measurement. More recently, Wu *et al.* reported a dynamic-circuit Shor implementation on a hybrid superconducting qubit-cavity processor for `N=15`. Therefore, the present work does **not** claim the first dynamic-circuit Shor experiment on a superconducting platform.

`N=35` also has prior experimental literature. Bagourd *et al.* studied Shor execution on current cloud hardware, including `N=35` cases with different bases and orders. Consequently, this work does **not** claim the first quantum-hardware evidence associated with factoring 35.

The safest novelty statement is therefore:

> We report replicated recovery of `r=12` order information for a compiled `N=35`, `a=2` Shor instance on IBM superconducting hardware using a dynamically recycled phase register, together with same-job cross-backend controls showing that the benefit depends strongly on physical placement and calibration.

A stronger priority statement may be supportable with an up-to-date literature qualifier:

> To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware.

That statement is a literature-search claim, not proof that no unpublished or obscure earlier result exists, and should retain the phrase “to our knowledge.”

## 3. Compiled order-finding problem

For

\[
N=35, \qquad a=2,
\]

the modular orbit beginning at 1 is

```text
1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1,
```

so the multiplicative order is

\[
r=12.
\]

The classical Shor post-processing then gives

\[
2^{r/2}=2^6=64\equiv 29\pmod{35},
\]

and

\[
\gcd(29-1,35)=7,\qquad \gcd(29+1,35)=5.
\]

Thus a useful recovery of the correct even order yields the nontrivial factors 5 and 7.

### 3.1 Affine orbit encoding

A direct natural-label implementation of the twelve modular states required expensive high-order controlled operations. The work register was therefore compiled into an exact affine four-bit representation of the twelve-state orbit:

```text
4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4.
```

The other four computational-basis states form a disjoint cycle and are not populated from the chosen encoded initial state. The mapping preserves the twelve-state modular orbit exactly within the subspace used by the experiment.

For eight phase bits, the modular-power sequence is

```text
1, 2, 4, 8, 4, 8, 4, 8.
```

Before phase control, these affine powers reduce to short networks of CNOT and X operations. Under phase control they become controlled operations that are decomposed and routed by the target backend. Exhaustive basis-state self-tests verify the affine powers and the complete encoded orbit before hardware submission.

This is a **compiled-orbit encoding**. It is not a generic reversible modular multiplier and does not by itself scale Shor's algorithm to large integers.

## 4. Wide and recycled circuit architectures

### 4.1 Wide architecture

The wide circuit uses eight simultaneous phase qubits plus the four-qubit coherent work register, for a total of 12 logical qubits. Each phase qubit controls the corresponding affine modular-power operation. The phase register is then processed using a conventional coherent inverse-QFT structure followed by terminal measurement.

### 4.2 Recycled architecture

The recycled circuit uses one phase ancilla plus the same four-qubit coherent work register, for a total of 5 simultaneous logical qubits. For each phase bit, the ancilla is prepared, used to control the corresponding modular power, corrected using previously measured phase bits via real-time classical feed-forward, measured in-circuit, reset, and reused.

The ideal wide and recycled constructions target the same finite-precision phase-estimation distribution. The experimental comparison therefore tests the cost of simultaneous coherence against the cost of dynamic operations.

## 5. Experimental controls and metrics

### 5.1 Matched comparisons

Within each principal wide-versus-recycled comparison:

- both circuits implement the same `N=35`, `a=2`, eight-bit phase-estimation problem;
- both use the same shot count;
- the same initial four physical work-register sites are enforced within each matched pair;
- the recycled ancilla is selected from the same physical region considered for the wide phase register;
- the ideal finite-precision order-12 distribution is generated independently of the measured data;
- uniform random output is processed through the exact same classical recovery code;
- raw or raw-derived result artifacts are retained in the repository.

The transpiler can route logical state away from requested initial sites during circuit execution. “Matched work-register placement” therefore refers to enforced initial physical placement rather than permanent pinning.

### 5.2 Recovery metrics

Two factor/order metrics are reported.

**Permissive verified-multiple recovery.** Continued-fraction denominators and bounded multiples are tested, but a candidate is accepted only when it satisfies the modular-order condition and produces nontrivial factors. This metric has a non-negligible random-output baseline and therefore cannot be interpreted in isolation.

**Strict direct-order recovery.** A shot is counted only when the continued-fraction denominator directly yields a useful verified order. This more conservative metric is used to test whether recognizable order information survives hardware noise.

Distribution-level agreement is measured using Hellinger fidelity and total-variation (TV) distance relative to the exact finite-precision ideal distribution.

### 5.3 Analytic eight-bit reference values

For the exact eight-bit post-processing used here:

| Metric | Uniform output | Exact ideal order-12 distribution |
|---|---:|---:|
| Permissive factor recovery | 12.890625% | 84.939855% |
| Strict direct-order recovery | 2.34375% | 14.975779% |
| Hellinger fidelity to ideal | 0.234867 | 1.0 |
| TV distance to ideal | 0.825713 | 0.0 |

These references are central to interpretation because classical post-processing can map random phase samples to factors at a nonzero rate.

## 6. IBM Fez results

### 6.1 Six-bit boundary experiment

The affine representation substantially reduced synthesis cost relative to an earlier natural-label implementation, but the first six-bit affine hardware experiment remained at or near the strict random-output floor. This negative result separated two bottlenecks: synthesis cost and phase-resolution discriminability.

Exact finite-precision analysis then showed that eight phase bits offered stronger ideal-versus-uniform separation while requiring only two additional low-cost affine modular-power rounds.

### 6.2 Initial eight-bit matched run

The first eight-bit Fez experiment used 512 shots per architecture.

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 788 | **607** |
| CZ gates | 331 | **175** |
| Permissive recovery | 12.50% | **40.2344%** |
| Strict direct-order recovery | 2.34375% (12/512) | **5.8594% (30/512)** |
| Hellinger fidelity | 0.1951 | **0.5236** |
| TV distance | 0.8448 | **0.5723** |

The wide circuit landed at the analytic strict uniform baseline, while recycled output exceeded both factor-recovery baselines and was substantially closer to the ideal distribution.

Using the analytic strict uniform probability `p=0.0234375` as a fixed null, observing 30 or more strict successes in 512 shots gives a one-sided binomial tail of approximately `6.44e-6`. This calculation models shot noise only; it does not account for calibration drift, correlated errors, model selection, or other hardware systematics.

### 6.3 Clean unmodified replication

The eight-bit experiment was repeated without changing the mathematical circuit or benchmark settings.

| Metric | Wide | Recycled |
|---|---:|---:|
| Permissive recovery | 13.6719% | **45.5078%** |
| Strict direct-order recovery | 2.9297% (15/512) | **7.03125% (36/512)** |
| Hellinger fidelity | 0.1932 | **0.5394** |
| TV distance | 0.8399 | **0.5489** |

The recycled strict signal therefore reproduced and increased. Pooling the two unmodified recycled runs gives 66 strict successes in 1024 shots versus 24 expected under the uniform model. The corresponding fixed-null binomial tail is approximately `5.52e-13`, but this pooled value remains descriptive because shots from separate hardware jobs need not be independent and identically distributed.

### 6.4 Calibration-aware placement search

After the clean replication was frozen, a zero-QPU search ranked candidate connected physical regions and deterministic transpiler seeds. The search preserved matched initial four-qubit work placement within each wide/recycled candidate pair. The ranking proxy combined calibrated two-qubit-gate error, mid-circuit measurement/readout quality, compiled CZ burden, depth, and circuit size. The score was used only for candidate selection and was not treated as a predicted hardware fidelity.

The selected plan reduced the recycled circuit from 175 to 160 CZ gates and from depth 607 to depth 572. The wide comparator also received a cleaner physical plan, making the optimized run a stronger rather than weaker comparison.

### 6.5 Optimized Fez matched run

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 746 | **572** |
| CZ gates | 362 | **160** |
| Circuit size | 1453 | **728** |
| Permissive recovery | 20.1172% | **53.7109%** |
| Strict direct-order recovery | 3.7109% (19/512) | **7.03125% (36/512)** |
| Hellinger fidelity | 0.2473 | **0.6441** |
| TV distance | 0.7957 | **0.3947** |

The placement search improved the broad measured distribution while preserving the strict direct-order rate from the clean replication. Under the same fixed strict-uniform null, 36 successes in 512 shots correspond to a one-sided binomial tail of approximately `9.73e-9`. Again, this is a shot-noise-only calculation rather than a complete hardware uncertainty model.

## 7. Cross-backend controls on IBM Marrakesh

A second superconducting backend was used to test whether the Fez result was a one-device artifact and to separate physical-layout effects from calibration-window effects.

Each Marrakesh A/B job submitted four circuits together:

1. legacy recycled,
2. legacy wide,
3. optimized recycled,
4. optimized wide.

All four circuits used the same mathematical problem, 512 shots, and optimization level 3. The legacy and optimized pairs separately preserved matched initial work-register placement.

### 7.1 Same-job A/B run 1

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 22.2656% | 1.3672% | 0.2606 | 0.7755 |
| Legacy wide | 13.4766% | 1.3672% | 0.1897 | 0.8441 |
| Optimized recycled | **33.9844%** | 3.7109% | 0.3908 | **0.6281** |
| Optimized wide | 32.0313% | **6.2500%** | **0.4688** | 0.6438 |

Optimized placement improved both architectures. In this calibration window, optimized wide had the stronger strict-order metric and Hellinger fidelity, demonstrating directly that recycled architecture is not universally superior.

### 7.2 Same-job A/B run 2

The complete four-circuit experiment was repeated in a second hardware job.

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 20.1172% | 2.5391% | 0.3093 | 0.7679 |
| Legacy wide | 14.2578% | 3.3203% | 0.2271 | 0.8132 |
| Optimized recycled | **41.9922%** | **6.2500%** | **0.5480** | **0.5224** |
| Optimized wide | 16.0156% | 2.9297% | 0.2487 | 0.8153 |

In the second calibration window, optimized recycled improved over legacy recycled by 21.875 percentage points in permissive recovery and 3.7109 points in strict recovery. Optimized recycled also exceeded optimized wide by 25.98 permissive percentage points and 3.32 strict points and had substantially better distribution-level agreement with the ideal reference.

Against the strict analytic uniform baseline, optimized recycled produced 32/512 strict successes, corresponding to a fixed-null one-sided binomial tail of approximately `8.37e-7`. Optimized wide produced 15/512, which is not comparably separated from the null.

### 7.3 Two-job descriptive summary

Pooling only for descriptive comparison:

| Circuit | Permissive, two jobs | Strict, two jobs |
|---|---:|---:|
| Legacy recycled | 217/1024 = 21.1914% | 20/1024 = 1.9531% |
| Legacy wide | 142/1024 = 13.8672% | 24/1024 = 2.3438% |
| Optimized recycled | **389/1024 = 37.9883%** | **51/1024 = 4.9805%** |
| Optimized wide | 246/1024 = 24.0234% | 47/1024 = 4.5898% |

Both optimized architectures are above the strict uniform floor when the two Marrakesh jobs are pooled descriptively. The ranking changes across calibration windows, however, and the wide architecture shows greater variation between the two A/B jobs. The present data therefore support an architecture-by-placement-by-backend interpretation rather than a universal recycled-over-wide claim.

## 8. Interpretation

Three conclusions are supported within the tested compiled setting.

First, **simultaneous coherent width is an experimental resource**. The recycled architecture replaces seven of eight simultaneous phase qubits with one repeatedly used ancilla and classical measurement records. On Fez, that width reduction coincided with lower entangling-gate burden and consistently stronger order-finding signal than the matched wide architecture.

Second, **hardware-aware placement materially changes the result**. On both Fez and Marrakesh, physical-region selection and routing quality changed factor recovery and distribution fidelity. Nominal logical width or CZ count alone therefore does not predict hardware performance.

Third, **the architecture ranking is backend- and calibration-dependent**. Marrakesh provides an important falsification control: optimized wide outperformed optimized recycled on the strict metric in one same-job window, while optimized recycled clearly outperformed optimized wide in the next. The useful general result is therefore not “recycling always wins,” but that dynamic-circuit resource trades must be co-designed with topology, placement, measurement quality, routing, and calibration state.

## 9. Limitations

The principal limitations are explicit.

1. **Compiled orbit.** The four-qubit affine work register is specific to the tested twelve-state orbit. It is not a scalable reversible modular multiplier.
2. **Small problem size.** `N=35` is not classically difficult to factor. The experiment is a hardware/resource benchmark, not a demonstration of quantum computational advantage.
3. **Finite hardware replication.** The result includes repeated Fez runs and two Marrakesh A/B jobs, but not enough randomized calibration windows to estimate a backend-independent effect distribution.
4. **Shot-noise significance only.** Reported binomial tails use the exact uniform-output rate as a fixed null. They do not model drift, correlated hardware errors, optimizer selection effects, or temporal dependence.
5. **Dynamic-circuit overhead.** Mid-circuit measurement, reset, and feed-forward have hardware-specific latency and error. The balance may change on future processors.
6. **Placement selection.** Zero-QPU placement searches use calibration-derived proxies. Although the final circuits are executed independently, repeated optimization against calibration metadata can introduce selection effects that require care in statistical interpretation.
7. **No asymptotic claim.** Recycling reduces simultaneous phase-register width; it does not remove the coherent work register or create an asymptotic speedup by itself.

## 10. Reproducibility

The public repository contains:

- circuit construction and exact affine-orbit self-tests;
- wide and recycled hardware runners;
- Fez raw-result-derived summaries;
- clean replication records;
- zero-QPU placement search code and frozen plans;
- Marrakesh cross-backend and same-job A/B records;
- analytic uniform-output baseline code;
- negative/null experiments retained for provenance;
- dependency and environment information for Qiskit and IBM Runtime.

The primary repository is:

`https://github.com/CaMaLabs/RecycledQubitRegisters`

Representative source records include:

- `results/hardware/SHOR35_AFFINE_HARDWARE.md`
- `results/hardware/SHOR35_OPTIMIZED_HARDWARE.md`
- `results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md`
- `results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md`
- `results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md`
- `docs/N35_NOVELTY_AUDIT_2026-09-14.md`

Hardware results depend on calibration, physical-qubit placement, routing, backend state, and software versions. The repository therefore preserves exact job-derived artifacts and treats cross-job pooling as descriptive unless a stronger experimental design justifies otherwise.

## 11. Conclusion

A dynamically recycled phase register can recover useful `r=12` order information for a compiled `N=35`, `a=2` Shor instance on present IBM superconducting hardware while using five simultaneous logical qubits instead of twelve. Fez experiments show replicated recycled performance above analytic random-output baselines, and hardware-aware placement further improves the measured order distribution. Marrakesh same-job A/B controls reproduce the order-finding signal on a second backend but also show that wide-versus-recycled ranking changes with physical placement and calibration. The evidence therefore supports a hardware-co-design conclusion rather than a universal architecture claim: coherent width, dynamic-operation overhead, placement, topology, and calibration state jointly determine whether recycling is advantageous.

The next scientifically useful step is not to scale the claim rhetorically, but to scale the experimental design: more randomized calibration windows, interleaved jobs, additional dynamic-capable backends, and eventually replacement of the compiled affine orbit with scalable reversible modular arithmetic.

## References

1. P. W. Shor, “Algorithms for quantum computation: discrete logarithms and factoring,” *Proceedings of the 35th Annual Symposium on Foundations of Computer Science*, 124–134 (1994).
2. R. B. Griffiths and C.-S. Niu, “Semiclassical Fourier transform for quantum computation,” *Physical Review Letters* **76**, 3228–3231 (1996).
3. E. Martín-López, A. Laing, T. Lawson, R. Alvarez, X.-Q. Zhou, and J. L. O'Brien, “Experimental realization of Shor's quantum factoring algorithm using qubit recycling,” *Nature Photonics* **6**, 773–776 (2012). DOI: `10.1038/nphoton.2012.259`.
4. M. Amico, Z. H. Saleem, and M. Kumph, “Experimental study of Shor's factoring algorithm using the IBM Q Experience,” *Physical Review A* **100**, 012305 (2019). DOI: `10.1103/PhysRevA.100.012305`.
5. U. Skosana and M. Tame, “Demonstration of Shor's factoring algorithm for N = 21 on IBM quantum processors,” *Scientific Reports* **11**, 16599 (2021). DOI: `10.1038/s41598-021-95973-w`.
6. E. Bäumer, V. Tripathi, A. Seif, D. Lidar, and D. S. Wang, “Quantum Fourier Transform Using Dynamic Circuits,” *Physical Review Letters* **133**, 150602 (2024). DOI: `10.1103/PhysRevLett.133.150602`.
7. P. Bagourd, J. Jang-Jaccard, V. Lenders, A. Mermoud, T. Hoefler, and C. Hempel, “Practical Challenges in Executing Shor's Algorithm on Existing Quantum Platforms,” arXiv:2512.15330 (2025/2026 revision). DOI: `10.48550/arXiv.2512.15330`.
8. H. Wu *et al.*, “Demonstrating advantages of dynamic quantum circuits on a hybrid superconducting qubit-cavity processor,” arXiv:2608.04780 (2026). DOI: `10.48550/arXiv.2608.04780`.

## Data and code availability

All code, public result summaries, benchmark definitions, and provenance records used for this manuscript are maintained in the `CaMaLabs/RecycledQubitRegisters` repository. Raw IBM credentials and private account identifiers are intentionally excluded.

## Competing interests

The author declares no competing interests.

## AI-assistance disclosure

AI tools were used for research organization, manuscript editing, literature-search assistance, and software-development support. Experimental claims, hardware result artifacts, and reproducibility records are tied to the public repository and should be evaluated from those source materials rather than from the use of AI assistance itself.
