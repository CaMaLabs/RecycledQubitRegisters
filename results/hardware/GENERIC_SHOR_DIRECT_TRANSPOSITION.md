# Generic N=35 direct-transposition synthesis result

Date: 2026-09-14

This note records the next zero-QPU step in the order/orbit-independent `N=35`, `a=2` Shor path.

The full six-bit modular permutation is still generated only from `N`, `a`, and the QPE power. The multiplicative order and the known 12-state orbit are not supplied to circuit construction. This remains generic full-register reversible synthesis for small `N`, not scalable modular arithmetic.

## Semantic status

`hardware/ibm_shor35_generic_permutation_direct_transposition.py` replaces Gray-path arbitrary basis-state transpositions with an exact CNOT basis fold, one phase-controlled pattern MCX, and the inverse fold.

For each transposition `|u> <-> |v>` at Hamming distance `d`, the primitive uses:

```text
1 six-control MCX + 2*(d-1) ordinary CNOTs
```

rather than `2d-1` six-control MCXs. Every primitive is exhaustively checked on all 64 work-register basis states, and each complete generated modular permutation is revalidated before compilation.

The reported run passed the direct semantic checks with:

- `order_used_in_circuit_construction: false`;
- `orbit_encoding_used: false`;
- full-register validation true for every round.

## Fez compiler sweep

Command:

```bash
python hardware/ibm_shor35_generic_permutation_direct_transposition.py \
  --backend ibm_fez \
  --phase-bits 6 8 \
  --kind recycled \
  --profiles n_clean_m15 1_clean_kg24 2_clean_kg24 default \
  --optimization-levels 2 3 \
  --seeds 2026 8776 9401
```

No QPU job was submitted.

The best recycled results were both obtained with `1_clean_kg24`, optimization level 3, seed `2026`:

| Phase bits | Logical qubits | High-level MCX | Basis-change CX | Native CZ | Compiled depth | Compiled size |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 11 | 135 | 410 | **10,795** | **23,633** | 44,066 |
| 8 | 11 | 175 | 534 | **14,396** | **31,084** | 58,659 |

Relative to the previous cycle-pivot/compiler optimum:

- 6-bit: `30,823 -> 10,795` CZ, a `65.0%` reduction; depth `64,812 -> 23,633`, a `63.5%` reduction;
- 8-bit: `40,194 -> 14,396` CZ, a `64.2%` reduction; depth `84,480 -> 31,084`, a `63.2%` reduction.

Relative to the earlier frozen full-permutation scaling receipt:

- 6-bit: `43,557 -> 10,795` CZ, a `75.2%` reduction;
- 8-bit: `59,061 -> 14,396` CZ, a `75.6%` reduction.

The high-level six-control MCX burden fell from `545 -> 135` at 6 bits and `709 -> 175` at 8 bits while preserving the exact modular map.

## Hardware decision boundary

This is the strongest compiler result yet for the order/orbit-independent full-register path, but `10,795` native CZ at six phase bits is still an extreme noisy-hardware burden. The result is therefore not, by itself, a hardware go decision.

The next gate is calibration-aware physical placement on the actual direct-transposition circuit. The new zero-QPU optimizer is:

```text
hardware/ibm_shor35_generic_direct_layout_optimizer.py
```

It keeps the frozen `1_clean_kg24`, optimization-level-3 circuit, searches compact 11-qubit physical patches around good MCM sites, includes the six work qubits and four clean HLS scratch qubits in the requested initial layout, sweeps routing seeds, and ranks compiled circuits by both native CZ/depth and a calibration-weighted CZ+measurement proxy. The proxy is explicitly a ranking heuristic, not a predicted fidelity.

Recommended first run:

```bash
python hardware/ibm_shor35_generic_direct_layout_optimizer.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --profile 1_clean_kg24 \
  --optimization-level 3 \
  --seeds 2026,8776,9401 \
  --candidate-plans 10 \
  --ancilla-pool 16
```

This submits **no QPU jobs**. A hardware stress test should only be considered after the physical-layout search is known and the resulting calibration-weighted burden is reviewed.
