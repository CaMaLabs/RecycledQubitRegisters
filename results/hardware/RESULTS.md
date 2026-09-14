# IBM hardware results

These results are from IBM Quantum Open Plan hardware runs performed on 2026-09-13/14 UTC with Qiskit 2.5.2 and qiskit-ibm-runtime 0.47.0.

## Dynamic-feedback probe

A one-qubit `H -> mid-circuit measure -> conditional X -> final measure` probe on `ibm_fez` produced 125/128 final zeros, for an observed feedback success probability of **97.65625%**. The run used `measure_2` and consumed 2 billed QPU seconds.

## Shared-layout 4-bit QPE sweep

Both architectures were constrained to the same physical neighborhood on `ibm_fez`. The iterative design reused two physical qubits while the conventional design used five logical qubits.

| Phase | Target | Wide QPE | Recycled 2Q | Difference |
|---|---|---:|---:|---:|
| 0.125 | `0010` | 69.53% | **91.80%** | **+22.27 pp** |
| 0.3125 | `0101` | 74.22% | **88.28%** | **+14.06 pp** |
| 0.6875 | `1011` | 71.48% | **90.23%** | **+18.75 pp** |

Across the three phases: wide QPE = 551/768 = 71.74%; recycled 2Q = 692/768 = 90.10%.

## Precision scaling

For phase 0.3125:

| Phase bits | Wide QPE | Recycled 2Q | Difference |
|---:|---:|---:|---:|
| 4 | 74.22% | **88.28%** | +14.06 pp |
| 5 | 62.11% | **86.72%** | +24.61 pp |
| 6 | 53.91% | **86.33%** | +32.42 pp |

The 6-bit 0.3125 case has trailing zero phase bits, so it is useful as a stability test but is not the hardest six-bit feedback pattern.

## Full-information 6-bit phase

For `phi = 0.328125 = 21/64 = 0.010101`, all six target bits carry information.

| Metric | Wide QPE | Recycled 2Q |
|---|---:|---:|
| Target success | 41.80% | **81.25%** |
| Logical qubits | 7 | **2** |
| Compiled depth | 276 | **103** |
| CZ gates | 105 | **12** |

The recycled implementation therefore used about 71% less simultaneous logical width, 63% less compiled depth, and 89% fewer CZ operations on this workload.

## Full-information 7-bit phase

For `phi = 0.3359375 = 43/128 = 0.0101011`, all seven target bits carry information.

| Metric | Wide QPE | Recycled 2Q |
|---|---:|---:|
| Target success | 39.06% | **83.20%** |
| Logical qubits | 8 | **2** |
| Compiled depth | 333 | **121** |
| CZ gates | 158 | **14** |

The recycled implementation improved target success by **44.14 percentage points** while using 75% fewer simultaneous logical qubits, about 64% less compiled depth, and about 91% fewer CZ operations.

## End-to-end real-QPU Shor factoring: matched same-job comparison

Both architectures were executed in the **same IBM job** on `ibm_fez` for the canonical compiled toy problem `N=15`, `a=2`, using four phase bits and a real 4-qubit modular work register. The two circuits were given the same initial physical work-qubit quartet; the transpiler could still route logical states during execution, so this is a shared-initial-placement comparison rather than a claim that work states remained pinned throughout the circuit.

| Metric | Wide | Recycled |
|---|---:|---:|
| Shots | 512 | 512 |
| Logical qubits | 8 | **5** |
| Compiled depth | 234 | **189** |
| Circuit size | 412 | **304** |
| CZ gates | 102 | **68** |
| Factor-recovering shots | 338/512 | **352/512** |
| Per-shot factor recovery | 66.02% | **68.75%** |
| Shots on the four ideal order-4 peaks | 87.89% | **98.44%** |
| Uninformative `0000` peak | **21.88%** | 29.69% |
| Off-peak outcomes | 12.11% | **1.56%** |

The recycled circuit was numerically ahead in factor recovery by **2.734375 percentage points**, but the difference is only about **0.93 standard errors**. Approximate Wilson 95% intervals are **61.81%-69.99%** for wide and **64.61%-72.61%** for recycled, so this run does not establish a statistically significant accuracy advantage.

The resource result is clearer: recycled used **37.5% fewer simultaneous logical qubits**, about **19.2% less compiled depth**, about **26.2% smaller compiled circuit size**, and **33.3% fewer CZ gates**. It also again produced a much cleaner order spectrum, with only 1.56% off-peak outcomes versus 12.11% for wide. Its remaining weakness is a larger probability on the valid but uninformative zero-order branch.

This matched run supersedes the earlier separate-job comparison as the preferred hardware baseline. See `shor15_matched_compare.csv` for the machine-readable result.

## Preliminary separate-job Shor comparison

The first wide and recycled Shor runs were submitted separately at 256 shots each. Wide measured 68.75% factor recovery and recycled measured 62.11%. Because those circuits were not forced onto the same initial work quartet and were run as separate jobs, these results are retained for provenance but should not be treated as the primary architecture comparison. See `shor15_compare.csv`.

## Post-processing note

The factor-recovery routine does not use the validation-only true-order field. It receives the measured phase integer together with public `N` and `a`, checks candidate orders by modular exponentiation, and then applies the Shor gcd step. It permits a small search over multiples of the continued-fraction denominator so cases such as measured phase `1/2` can recover true order `r=4` when numerator and order are not coprime.

## Calibration for the full-information QPE run

The selected iterative pair on `ibm_fez` was physical qubits 22 and 23. At run time:

- `measure_2` on qubit 22: duration 1.34 us, reported error 0.002685546875.
- CZ(22,23): duration 68 ns, reported error 0.001519508547649151.

## Important limitations

This repository does **not** claim that two physical qubits replace a full Shor implementation or an arbitrary wide coherent quantum register. The demonstrated savings apply to the phase/control register in workloads that permit iterative measurement, reset, classical feed-forward, and qubit reuse. A modular-arithmetic work register is still required for Shor-style factoring. Arbitrary high-entanglement circuits are also outside the regime where this architecture can substitute a narrow recycled quantum register.

The real-QPU `N=15` demonstration is a canonical compiled toy Shor instance, not evidence that cryptographic RSA sizes are currently tractable. Its modular multiplication network is specialized for `N=15`, `a=2`; larger general semiprimes require scalable reversible modular arithmetic and far greater fault-tolerant resources.

The large difference observed between `ibm_fez` and `ibm_kingston` in early diagnostics also shows that backend and physical-qubit selection are part of the architecture problem, not merely deployment details.
