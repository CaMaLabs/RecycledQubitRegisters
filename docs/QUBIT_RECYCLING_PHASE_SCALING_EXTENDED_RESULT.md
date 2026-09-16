# Extended fixed-width phase-scaling result

Date: 2026-09-15

## Scope

Zero-QPU IBM-target compilation on `ibm_fez` for the exact small-N full-register N=35 validation path. The recycled construction uses one phase qubit, six work qubits, and one reusable clean ancilla for a fixed eight-qubit source width. The wide construction uses one phase qubit per requested precision bit plus the same work/scratch resources.

This is a compiler/resource result, not a measured QPU runtime or fidelity result, and the modular-permutation synthesis is still a small-N validation construction rather than scalable RSA arithmetic.

## Extended sweep

The extended sweep used phase precisions 24, 32, 40, 48, and 64 bits, optimization level 3, `profile=auto`, and transpiler seeds 8776, 2026, and 9401. Strict-width comparisons exclude compiled candidates that touch more physical qubits than were allocated by the source circuit.

| Phase bits | Wide width | Recycled width | Qubits saved | Width reduction | CZ ratio recycled/wide | CZ reduction | Depth ratio recycled/wide | Depth reduction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24 | 31 | 8 | 23 | 74.19% | 0.9297 | 7.03% | 0.9918 | 0.82% |
| 32 | 39 | 8 | 31 | 79.49% | 0.9191 | 8.09% | 0.9877 | 1.23% |
| 40 | 47 | 8 | 39 | 82.98% | 0.9073 | 9.27% | 0.9771 | 2.29% |
| 48 | 55 | 8 | 47 | 85.45% | 0.9045 | 9.55% | 0.9927 | 0.73% |
| 64 | 71 | 8 | 63 | 88.73% | 0.8916 | 10.84% | 0.9784 | 2.16% |

## 64-bit point

Best strict recycled compile:

- logical/touched qubits: 8 / 8
- native CZ: 110,067
- compiled depth: 233,439
- compiled size: 449,539
- seed: 2026

Best strict wide compile:

- logical/touched qubits: 71 / 71
- native CZ: 123,452
- compiled depth: 238,581
- compiled size: 494,853
- seed: 8776

Thus at 64 phase bits, recycled QPE saves 63 simultaneously allocated/touched qubits (88.73%) while also reducing native CZ by 10.84% and compiled depth by 2.16% in the best strict-width comparison.

## Layout stability

Every recycled candidate in the 24-64-bit sweep remained strict-width at exactly eight touched physical qubits for all tested seeds. The wide construction often caused the transpiler to touch more qubits than the nominal source width; those candidates were excluded from strict-width winners. Examples include 31 allocated -> 35 touched at 24 bits, 39 -> 40/42 at 32 bits, 47 -> 51/55 at 40 bits, and 55 -> 57/58 at 48 bits.

## Interpretation

Within this validation architecture, increasing phase precision increases sequential work while the recycled quantum width remains fixed. The conventional wide phase register increases simultaneous width linearly with precision. Through 64 phase bits, the recycled construction does not exhibit a native-CZ penalty relative to the best strict wide compile; instead, its CZ advantage grows to about 10.8% at the largest tested point.

The safe conclusion is therefore narrower than an asymptotic or hardware-runtime claim: for this exact N=35 compiler benchmark, iterative phase-register reuse converts a growing simultaneous phase-register requirement into sequential reuse of one phase qubit, while preserving or improving the compiled native-cost metrics tested here.
