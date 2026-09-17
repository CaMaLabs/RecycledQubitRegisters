# Recycled-register fixed-width N/base matrix result

Date: 2026-09-17

## Scope

This zero-QPU follow-up holds phase precision fixed at 32 bits and varies public `(N, a)` cases within work-register width classes. The goal is to separate three effects that were confounded in the earlier cross-N sweep:

1. simultaneous qubit-width reduction from phase-register recycling,
2. work-register width,
3. the specific modular-permutation / interaction structure induced by `(N, a)`.

Cases tested:

- 5 work qubits: `(21,2)`, `(21,5)`, `(25,2)`
- 6 work qubits: `(35,2)`, `(35,3)`, `(39,2)`
- 7 work qubits: `(77,2)`, `(77,3)`, `(85,2)`

All cases used 32 phase bits, exact full-register modular-permutation semantics, the same placement-ensemble methodology, Fez heavy-hex topology, and the labeled Nighthawk 10x12 square-lattice proxy. No QPU job was submitted.

## Width result

The width result is invariant across all tested cases:

- 5 work qubits: `38 -> 7`, saving 31 qubits
- 6 work qubits: `39 -> 8`, saving 31 qubits
- 7 work qubits: `40 -> 9`, saving 31 qubits

Thus the primary simultaneous-width advantage is architectural and does not depend on the particular `(N,a)` case in this matrix.

## Best-placement results

| N | a | work | topology | best R/W CZ | best R/W depth |
|---:|---:|---:|---|---:|---:|
| 21 | 2 | 5 | Fez | 0.8157 | 0.9773 |
| 21 | 2 | 5 | Nighthawk proxy | 0.9347 | 0.9781 |
| 21 | 5 | 5 | Fez | 0.8267 | 0.9831 |
| 21 | 5 | 5 | Nighthawk proxy | 0.9342 | 0.9865 |
| 25 | 2 | 5 | Fez | 0.8656 | 1.0024 |
| 25 | 2 | 5 | Nighthawk proxy | 0.9570 | 0.9984 |
| 35 | 2 | 6 | Fez | 0.9751 | 1.0087 |
| 35 | 2 | 6 | Nighthawk proxy | 0.9285 | 1.0116 |
| 35 | 3 | 6 | Fez | 0.9802 | 1.0098 |
| 35 | 3 | 6 | Nighthawk proxy | 0.9368 | 0.9999 |
| 39 | 2 | 6 | Fez | 1.0210 | 1.0169 |
| 39 | 2 | 6 | Nighthawk proxy | 0.9355 | 1.0036 |
| 77 | 2 | 7 | Fez | 1.0361 | 1.0029 |
| 77 | 2 | 7 | Nighthawk proxy | 0.9765 | 0.9978 |
| 77 | 3 | 7 | Fez | 1.0374 | 1.0056 |
| 77 | 3 | 7 | Nighthawk proxy | 0.9790 | 0.9928 |
| 85 | 2 | 7 | Fez | 0.9729 | 1.0226 |
| 85 | 2 | 7 | Nighthawk proxy | 0.8978 | 1.0043 |

## Main findings

### 1. Width reduction generalizes cleanly

All nine `(N,a)` cases save exactly 31 simultaneous qubits at 32-bit phase precision. That part of the result is independent of permutation details in this matrix.

### 2. Gate/depth advantage is not determined by work-register width alone

Within a fixed work width, changing `N` or the public base `a` measurably changes the best-placement ratios. Examples:

- 5-work-qubit Fez best-CZ ratios range from 0.8157 to 0.8656.
- 6-work-qubit Fez ranges from 0.9751 to 1.0210.
- 7-work-qubit Nighthawk proxy ranges from 0.8978 to 0.9790.

This falsifies a simple interpretation in which compiler cost is controlled mainly by simultaneous work width. The induced modular-permutation interaction structure matters.

### 3. Topology strongly moderates the placement-aware CZ result

On the Nighthawk square-lattice proxy, all nine tested `(N,a)` cases retain `best R/W CZ < 1`.

On Fez heavy-hex, the best-CZ advantage disappears for:

- `(39,2)` at 6 work qubits,
- `(77,2)` at 7 work qubits,
- `(77,3)` at 7 work qubits.

This is evidence that higher local connectivity can absorb some of the routing pressure created by the narrow recycled architecture.

### 4. Aggregate width-class pattern

Mean best-placement ratios within each work-width class are approximately:

| work qubits | topology | mean best R/W CZ | mean best R/W depth |
|---:|---|---:|---:|
| 5 | Fez | 0.8360 | 0.9876 |
| 5 | Nighthawk proxy | 0.9420 | 0.9877 |
| 6 | Fez | 0.9921 | 1.0118 |
| 6 | Nighthawk proxy | 0.9336 | 1.0050 |
| 7 | Fez | 1.0155 | 1.0104 |
| 7 | Nighthawk proxy | 0.9511 | 0.9983 |

The heavy-hex best-CZ advantage degrades as work width grows, while the square-lattice proxy remains below 1 across all three width classes. This does not prove a hardware-runtime advantage, but it makes topology-aware placement a central compiler variable rather than a secondary optimization.

### 5. Median placement remains mixed

Median-placement behavior is materially worse than best-placement behavior in many cases. This confirms that the narrow recycled architecture is placement-sensitive and that the supported compiler claim is placement-aware, not arbitrary-placement.

## Updated interpretation

The supported statement is now:

> Phase-register recycling gives a stable simultaneous-qubit reduction across all tested `(N,a)` cases. Whether that narrow implementation also reduces native two-qubit cost depends on the modular-permutation interaction graph and hardware topology. Placement-aware search can recover a CZ advantage across a broad case matrix, especially on the higher-connectivity square-lattice proxy.

This supersedes the simpler idea that the shrinking gate advantage seen in the original N=21/35/77 sweep was primarily a work-register-width effect.

## Compiler implication

The next optimizer should score mappings from the actual two-qubit interaction graph after HLS decomposition rather than from width, degree, or patch density alone. The new `ibm_recycled_interaction_graph_mapper.py` is intended to test exactly this hypothesis.

## Boundaries

- Zero-QPU compiler/topology result only.
- Nighthawk remains a public square-lattice proxy, not authenticated Phoenix calibration/performance.
- Exact small-N full-register permutation synthesis remains non-scalable to RSA-sized modular arithmetic.
- Best-placement results are optimization results; median/random placement can be worse.
- This is not an asymptotic speedup or cryptanalytic claim.
