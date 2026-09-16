# Placement-optimized recycled-register topology result

Date: 2026-09-16

This note records the zero-QPU placement-optimization audit from
`hardware/ibm_nighthawk_placement_optimization_audit.py`.

## Scope

- N = 35 exact small-N full-register permutation benchmark.
- Architectures: 8-qubit recycled QPE versus growing wide QPE.
- Topologies: authenticated `ibm_fez` heavy-hex connectivity and a clearly labeled
  10x12, 120-qubit square-lattice Nighthawk proxy because `ibm_phoenix` metadata was
  unavailable to the active open-instance account.
- Every compile target was capacity locked to exactly the source-circuit width, so
  extra HLS/routing qubit borrowing was impossible.
- 16 connected exact-width placements were searched per topology/architecture/precision.
- Transpiler seed: 2026.
- No Sampler and no QPU job.

This is a compiler/topology placement result, not calibrated Nighthawk performance,
not a QPU runtime/fidelity result, and not scalable RSA modular arithmetic.

## Best-placement results

| phase bits | topology | recycled width | wide width | recycled CZ | wide CZ | CZ reduction | recycled depth | wide depth | depth reduction |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | Fez heavy-hex | 8 | 23 | 27,769 | 29,430 | 5.64% | 60,130 | 61,356 | 2.00% |
| 16 | Nighthawk proxy | 8 | 23 | 20,703 | 22,791 | 9.16% | 52,513 | 52,676 | 0.31% |
| 32 | Fez heavy-hex | 8 | 39 | 54,973 | 60,656 | 9.37% | 118,122 | 120,212 | 1.74% |
| 32 | Nighthawk proxy | 8 | 39 | 40,628 | 46,049 | 11.77% | 102,357 | 103,793 | 1.38% |
| 64 | Fez heavy-hex | 8 | 71 | 109,726 | 122,436 | 10.38% | 235,651 | 240,086 | 1.85% |
| 64 | Nighthawk proxy | 8 | 71 | 81,320 | 92,999 | 12.56% | 205,015 | 206,549 | 0.74% |

## Interpretation

Within the searched placement set, the 8-qubit recycled architecture beats the best
wide placement on both native CZ count and compiled depth at 16, 32, and 64 phase
bits on both topology models. The advantage grows with phase precision in CZ while
the width remains fixed at eight qubits.

At 64 phase bits, recycled uses 8 rather than 71 qubits (63 fewer, 88.7% width
reduction) and also has lower native CZ and depth in the best-placement comparison.

The subgraph-ensemble audit showed that recycled circuits are much more placement
sensitive than wide circuits. Therefore this best-of-16 result should be interpreted
as evidence that placement-aware mapping is a high-value compiler optimization for
recycled registers, not as an unbiased expected-placement advantage.

## Claim boundary

Supported:

- placement choice materially changes recycled-QPE native cost;
- a searched exact-width placement can make the 8-qubit recycled circuit outperform
  a searched wide circuit in CZ and depth in this N=35 compiler/topology benchmark;
- this holds in the reported best-of-16 search on both Fez heavy-hex and the labeled
  Nighthawk square-lattice proxy.

Not established:

- that arbitrary placements have this advantage;
- that Nighthawk hardware will reproduce these proxy numbers;
- a measured QPU speedup or fidelity improvement;
- scalable RSA resource savings from the small-N full-state permutation synthesis.

## Next falsification / replication

Repeat the placement search with a fresh subgraph RNG seed and multiple transpiler
seeds. Treat the original deterministic dense patch as non-independent and judge the
replication primarily from fresh stochastic placements. The result should be reported
separately from the discovery search.
