# Capacity-Locked Fez vs Nighthawk Topology Result

## Scope

This result is a **zero-QPU compiler/topology proxy** for the exact small-N (`N=35`) full-register Shor/QPE benchmark used throughout this repository.

The Nighthawk side was **not** compiled against authenticated `ibm_phoenix` metadata because the available IBM account could not access that backend. It therefore used the repository's explicitly labeled 120-qubit 10x12 square-lattice proxy. No calibration, gate-duration, reset-speed, fidelity, or QPU-execution claim is made.

The capacity-locked benchmark improves on the earlier topology test by reducing each topology to an exact-width connected induced subgraph before compilation. This makes extra physical-qubit borrowing impossible by construction.

## Main result

The recycled architecture uses 8 qubits at every tested phase precision. The wide architecture grows from 11 qubits at 4 phase bits to 71 qubits at 64 phase bits.

On the deterministic exact-width subgraphs, the Nighthawk-style square lattice sharply reduces routing overhead for both architectures. More importantly, it removes most of the recycled-vs-wide routing penalty visible on the capacity-locked Fez patches as precision increases.

Selected recycled/wide native-CZ ratios:

| Phase bits | Fez R/W CZ | Nighthawk-proxy R/W CZ | Relative Nighthawk/Fez |
|---:|---:|---:|---:|
| 8 | 0.9890 | 1.0435 | 1.0551 |
| 12 | 1.1557 | 1.0313 | 0.8924 |
| 16 | 1.1709 | 1.0185 | 0.8698 |
| 20 | 1.1867 | 1.0123 | 0.8531 |
| 24 | 1.1927 | 1.0029 | 0.8409 |
| 32 | 1.1790 | 0.9942 | 0.8433 |
| 40 | 1.1728 | 0.9856 | 0.8404 |
| 48 | 1.1824 | 0.9924 | 0.8393 |
| 64 | 1.1705 | 0.9827 | 0.8395 |

At 64 phase bits:

- recycled width: **8 qubits**
- wide width: **71 qubits**
- qubits saved: **63**
- Nighthawk-proxy recycled CZ: **91,468**
- Nighthawk-proxy wide CZ: **93,081**
- recycled/wide CZ ratio: **0.9827**
- Nighthawk-proxy recycled depth: **207,106**
- Nighthawk-proxy wide depth: **207,032**
- recycled/wide depth ratio: **1.0004**

Thus, on this exact-width topology proxy, the 8-qubit recycled construction reaches essentially the same or slightly lower native two-qubit cost as the 71-qubit wide construction at high phase precision.

## Interpretation

This is consistent with the hypothesis that a higher-degree square lattice is unusually compatible with qubit recycling. The recycled circuit concentrates repeated modular-control traffic into a fixed small set of qubits; a denser local topology reduces the routing penalty of repeatedly reusing that same compact register.

The result should **not** be stated as measured Nighthawk hardware performance. It is a topology-only compiler experiment using a public square-lattice proxy.

## Important control still required

Each capacity-locked topology used one deterministic dense connected induced subgraph. Routing results can depend on which exact patch is selected. The next validation is therefore a subgraph-ensemble audit: compile the same recycled and wide circuits across multiple distinct exact-width connected subgraphs on both Fez and the Nighthawk proxy, then compare the distributions rather than one chosen patch.

## Claim boundary

Safe claim:

> In a zero-QPU topology-only compiler proxy with exact-width capacity locking, a Nighthawk-style square lattice substantially reduces the routing overhead of the fixed-width recycled-QPE construction and brings its native CZ/depth cost to parity with or below wide QPE at higher phase precision, while preserving the large qubit-count reduction.

Do not claim:

- measured Phoenix/Nighthawk runtime or fidelity,
- measured reset-speed benefit,
- calibrated hardware advantage,
- scalable RSA arithmetic,
- or that the public 10x12 proxy is Phoenix's exact coupling map.
