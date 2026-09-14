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

## Calibration for the full-information run

The selected iterative pair on `ibm_fez` was physical qubits 22 and 23. At run time:

- `measure_2` on qubit 22: duration 1.34 us, reported error 0.002685546875.
- CZ(22,23): duration 68 ns, reported error 0.001519508547649151.

## Important limitations

This repository does **not** claim that two physical qubits replace a full Shor implementation or an arbitrary wide coherent quantum register. The demonstrated savings apply to the phase/control register in workloads that permit iterative measurement, reset, classical feed-forward, and qubit reuse. A modular-arithmetic work register is still required for Shor-style factoring. Arbitrary high-entanglement circuits are also outside the regime where this architecture can substitute a narrow recycled quantum register.

The large difference observed between `ibm_fez` and `ibm_kingston` in the early diagnostic runs also shows that backend and physical-qubit selection are part of the architecture problem, not merely deployment details.
