# Recycled-register three-way Pareto scaling result

Date: 2026-09-15

## Scope

Zero-QPU IBM Fez-target compiler benchmark for the exact small-N `N=35` full-register modular-permutation validation path. This is a resource-scaling result for recycled phase estimation, not scalable RSA arithmetic and not a QPU runtime/fidelity measurement.

Three architectures were compared at phase precision 4, 8, 12, 16, 20, 24, 32, 40, 48, and 64 bits:

- **floor7**: one recycled phase qubit + six work qubits, no scratch ancilla; `noaux_hp24` MCX synthesis.
- **optimum8**: one recycled phase qubit + six work qubits + one reusable clean ancilla; automatic HLS.
- **wide**: one phase qubit per requested precision bit + six work qubits + one clean ancilla.

All reported winners are strict-width results: compiled touched qubits do not exceed source logical width. Three transpiler seeds were tested at optimization level 3.

## Main result

The 8-qubit recycled architecture remains fixed at 8 touched qubits from 4 through 64 phase bits, while the strict wide architecture grows from 11 to 71 touched qubits.

At 64 phase bits:

| architecture | touched qubits | native CZ | compiled depth |
|---|---:|---:|---:|
| floor7 | 7 | 341,049 | 860,530 |
| optimum8 | 8 | 110,067 | 233,439 |
| wide | 71 | 123,452 | 238,581 |

Thus, relative to wide at 64 bits, optimum8 uses 63 fewer touched qubits (88.73% reduction), 10.84% fewer native CZ gates, and 2.16% lower compiled depth.

Relative to the strict 7-qubit floor at 64 bits, the single reusable clean ancilla reduces native CZ by about 67.73% and compiled depth by about 72.87%.

## Scaling summary

| phase bits | floor7 q | optimum8 q | wide q | floor7 CZ | optimum8 CZ | wide CZ | optimum8 / wide CZ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 7 | 8 | 11 | 24,622 | 7,515 | 7,548 | 0.9956 |
| 8 | 7 | 8 | 15 | 45,750 | 14,394 | 14,740 | 0.9765 |
| 12 | 7 | 8 | 19 | 66,760 | 21,203 | 22,086 | 0.9600 |
| 16 | 7 | 8 | 23 | 87,867 | 28,231 | 30,299 | 0.9317 |
| 20 | 7 | 8 | 27 | 108,884 | 34,955 | 37,457 | 0.9332 |
| 24 | 7 | 8 | 31 | 130,248 | 41,934 | 45,103 | 0.9297 |
| 32 | 7 | 8 | 39 | 172,048 | 55,693 | 60,596 | 0.9191 |
| 40 | 7 | 8 | 47 | 214,396 | 69,489 | 76,590 | 0.9073 |
| 48 | 7 | 8 | 55 | 256,678 | 83,118 | 91,895 | 0.9045 |
| 64 | 7 | 8 | 71 | 341,049 | 110,067 | 123,452 | 0.8916 |

The width benefit grows monotonically with requested phase precision, while the native-CZ ratio of optimum8 versus wide improves from near parity at 4 bits to roughly 0.892 at 64 bits.

## Pareto interpretation

At 4 phase bits, all three constructions remain on the strict Pareto front because wide has a very small depth advantage over optimum8.

From 8 phase bits onward, the wide construction is dominated by optimum8 on the measured resource axes: optimum8 uses fewer touched qubits, fewer native CZ gates, and lower compiled depth. The strict Pareto front therefore contains only:

1. **floor7** — absolute width minimum, but high gate/depth cost.
2. **optimum8** — one additional reusable qubit, dramatically lower CZ/depth.

This makes 7 qubits the hard-width point for this exact six-bit residue encoding and 8 qubits the practical Pareto optimum across the tested precision range.

## Claim boundaries

- Compiler/resource proxy only; no QPU job was submitted.
- IBM Fez target only for this result.
- No runtime, fidelity, error-rate, or hardware-success claim.
- Exact full-register small-N permutation synthesis; not scalable modular arithmetic.
- No order information or reachable-orbit encoding is supplied to circuit construction.

## Next experiment

Use the existing `hardware/ibm_nighthawk_topology_recycling_benchmark.py` to compare the same recycled-vs-wide constructions on Fez heavy-hex connectivity versus authenticated Nighthawk/Phoenix connectivity when available, falling back to a clearly labeled square-lattice topology proxy otherwise. Keep this comparison topology-only unless real Nighthawk calibration/timing data and hardware execution are explicitly introduced.