# Fixed-width qubit recycling phase-scaling result

Date: 2026-09-15

## Scope

Zero-QPU IBM-target compiler benchmark for the exact small-N `N=35` full-register modular-permutation implementation. This measures phase-register recycling and physical-width scaling only. It is **not** a scalable RSA modular-arithmetic result and does not claim QPU runtime or fidelity improvement.

Backend target: `ibm_fez`.

Recycled construction:

- 1 recycled phase qubit
- 6 work qubits
- 1 reusable clean ancilla
- **8 allocated qubits total**, independent of requested phase precision

Wide construction:

- one phase qubit per requested precision bit
- 6 work qubits
- 1 clean ancilla
- width = `phase_bits + 7`

All reported winners satisfy strict width: compiled touched physical qubits do not exceed allocated logical qubits.

## Results

| Phase bits | Wide qubits | Recycled qubits | Qubits saved | Width reduction | Wide CZ | Recycled CZ | CZ reduction | Wide depth | Recycled depth | Depth reduction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 11 | 8 | 3 | 27.27% | 7,554 | 7,517 | 0.49% | 16,428 | 16,452 | -0.15% |
| 8 | 15 | 8 | 7 | 46.67% | 14,746 | 14,396 | 2.37% | 31,155 | 31,137 | 0.06% |
| 12 | 19 | 8 | 11 | 57.89% | 22,086 | 21,211 | 3.96% | 45,993 | 45,521 | 1.03% |
| 16 | 23 | 8 | 15 | 65.22% | 30,301 | 28,233 | 6.82% | 60,749 | 60,019 | 1.20% |
| 20 | 27 | 8 | 19 | 70.37% | 37,457 | 34,965 | 6.65% | 75,379 | 74,246 | 1.50% |

The recycled circuit therefore held a constant 8-qubit physical footprint while the strict wide implementation grew from 11 to 27 qubits. Across this range, recycling did not create a native-CZ penalty; by 20 phase bits it compiled to 6.65% fewer CZ gates and 1.50% lower depth than the best strict wide result.

## Routing / physical-footprint behavior

The recycled circuit remained strict-width for every transpiler seed tested at every precision. Some wide runs borrowed additional physical qubits before strict filtering. Examples:

- 4 phase bits: 11 allocated, some seeds touched 15 physical qubits.
- 8 phase bits: 15 allocated, one seed touched 17 physical qubits.
- 16 phase bits: 23 allocated, two seeds touched 25 and 26 physical qubits.

This is not by itself a hardware-performance claim, but it suggests the recycled construction gives the transpiler a more tightly bounded active footprint.

## Interpretation

Within the current exact `N=35` architecture:

- 7 qubits is the generic full-residue hard width floor: 6 work qubits plus 1 iterative phase qubit.
- 8 qubits is the current practical Pareto point because one reusable clean ancilla dramatically reduces MCX synthesis cost.
- Increasing requested phase precision does **not** increase recycled quantum width; it increases sequential circuit work instead.
- The wide construction grows linearly in qubit count with phase precision.

This is the central resource tradeoff demonstrated by the project: phase precision can be converted from simultaneous quantum width into sequential dynamic-circuit work while retaining exact public modular semantics for this small-N validation system.

## Claim boundary

Safe claim: for this compiler-targeted small-N implementation, iterative/recycled QPE kept the active quantum width fixed at 8 qubits from 4 through 20 requested phase bits, while the matched wide implementation grew from 11 to 27 qubits, with comparable or lower compiled CZ/depth cost.

Do not generalize these gate counts to RSA-scale arithmetic. The current modular unitary is exact truth-table/full-register synthesis and is not scalable.
