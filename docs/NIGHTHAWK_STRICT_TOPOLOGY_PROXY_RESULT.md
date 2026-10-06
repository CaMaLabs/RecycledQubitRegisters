# Strict-width Fez vs Nighthawk topology-proxy result

Date: 2026-10-06

## Scope

This records the zero-QPU strict-subgraph benchmark from
`hardware/ibm_nighthawk_strict_subgraph_benchmark.py`.

The experiment compares the same exact small-N N=35 recycled-QPE construction
on two normalized CZ-basis connectivity models:

- authenticated IBM Fez heavy-hex connectivity;
- a clearly labeled 10x12, 120-qubit square-lattice proxy for IBM Nighthawk.

For every topology/architecture/phase-precision point, the compiler backend was
hard-capped to the source logical width by using a connected induced subgraph of
exactly that width. Therefore Qiskit could not borrow additional physical
qubits.

This is a topology/compiler proxy only. It contains no Phoenix calibration,
timing, reset-speed, fidelity, or QPU data. The square-lattice proxy is not
asserted to be the exact Phoenix coupling map. The N=35 full-register
permutation synthesis is not a scalable RSA modular-arithmetic estimate.

## Main result

All tested points from 4 through 64 phase bits produced strict-width results.

The recycled architecture remains fixed at 8 qubits while the conventional
wide architecture grows from 11 to 71 qubits.

| phase bits | wide q | recycled q | q saved | Fez R/W CZ | square R/W CZ | Fez R/W depth | square R/W depth |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4  | 11 | 8 | 3  | 0.9649 | 0.9758 | 0.9732 | 0.9908 |
| 8  | 15 | 8 | 7  | 0.9219 | 0.9779 | 0.9617 | 1.0003 |
| 12 | 19 | 8 | 11 | 0.9214 | 0.9549 | 0.9268 | 0.9833 |
| 16 | 23 | 8 | 15 | 0.9637 | 0.9510 | 0.9925 | 0.9865 |
| 20 | 27 | 8 | 19 | 0.9495 | 0.9418 | 0.9594 | 0.9759 |
| 24 | 31 | 8 | 23 | 0.9708 | 0.9279 | 0.9724 | 0.9886 |
| 32 | 39 | 8 | 31 | 0.9632 | 0.9235 | 0.9767 | 0.9853 |
| 40 | 47 | 8 | 39 | 0.9503 | 0.9227 | 0.9574 | 0.9820 |
| 48 | 55 | 8 | 47 | 0.9497 | 0.9190 | 0.9661 | 0.9820 |
| 64 | 71 | 8 | 63 | 0.9459 | 0.9129 | 0.9615 | 0.9886 |

R/W means recycled divided by wide. Values below 1 favor recycling.

## 64-phase-bit endpoint

At 64 phase bits:

- Fez recycled: 8 qubits, 116,029 CZ, depth 231,555.
- Fez wide: 71 qubits, 122,667 CZ, depth 240,818.
- Square-lattice recycled: 8 qubits, 85,385 CZ, depth 204,263.
- Square-lattice wide: 71 qubits, 93,804 CZ, depth 207,804.

Thus the recycled design saves 63 of 71 qubits, an 88.73% width reduction.

Relative to wide at the same topology:

- Fez: recycled uses 5.41% fewer CZs and 3.85% less depth.
- Square-lattice proxy: recycled uses 8.71% fewer CZs and 1.14% less depth.

The CZ advantage of recycling is therefore larger on the square-lattice proxy
at high precision: 8.71% versus 5.41% at 64 bits. Expressed relative to the Fez
CZ saving, that is about a 61% larger recycling advantage. This should be
described as a compiler/topology effect, not a hardware speedup.

## Absolute topology effect

The denser square-lattice proxy benefits both architectures.

At 64 phase bits, relative to the strict Fez subgraph:

- recycled square-lattice uses about 26.41% fewer CZs and 11.79% less depth;
- wide square-lattice uses about 23.53% fewer CZs and 13.71% less depth.

The square lattice therefore reduces routing cost substantially for both
architectures, while giving the recycled circuit a somewhat larger relative CZ
benefit at high phase precision.

## Interpretation

The strict-width rerun resolves the ambiguity from the earlier full-topology
experiment, where the compiler borrowed extra Nighthawk-proxy qubits.

The strongest supported claim is:

> Under equal hard width caps and a normalized CZ basis, a denser
> square-lattice topology preserves the fixed-width recycled-register advantage
> and, from roughly 16 phase bits onward, generally increases its CZ-count
> advantage relative to a conventional wide phase register.

The depth result is more nuanced. The square-lattice proxy lowers absolute
depth for both architectures, but it does not consistently amplify the
recycled-over-wide depth advantage. At 8 bits the depth ratio is essentially
equal (1.0003), and at 64 bits the recycled depth advantage is smaller on the
square proxy than on Fez.

## Methodological caveat and next validation

Each width uses a deterministic compact connected subgraph chosen by a greedy
best-of-all-starts search that favors high induced edge count. This is a
reasonable best-placement proxy, but one selected subgraph can hide placement
sensitivity.

The next topology validation should therefore repeat the strict-width
comparison across multiple connected subgraphs / placements per width and
report the distribution (median, interquartile range, best, worst) rather than
only the densest selected patch. That will distinguish a robust topology effect
from a favorable-placement effect.

No QPU job was submitted.
