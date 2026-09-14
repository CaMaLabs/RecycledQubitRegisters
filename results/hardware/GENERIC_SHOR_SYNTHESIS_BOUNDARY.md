# Generic Shor synthesis boundary: N=35, a=2

Date: 2026-09-14

This note records zero-QPU compiler experiments that attempt to remove the known-order / compiled-orbit dependency from the successful affine `N=35, a=2, r=12` hardware benchmark.

All circuit constructors in this note derive modular powers from `N`, `a`, and the QPE bit index. The multiplicative order is used only by validation/reporting code, never to construct the tested modular unitary.

## Semantic gate

The first full-residue arithmetic implementation passed exhaustive semantic tests for `N=35, a=2`:

- 6-bit residue register;
- 1,190 modular-add cases;
- 1,024 controlled modular-multiply cases at 8 phase bits;
- `y < 35 -> m*y mod 35`;
- `y >= 35 -> y`;
- arithmetic ancillas returned clean;
- `order_used_in_circuit_construction: false`.

The remaining problem is therefore synthesis cost, not the tested arithmetic semantics.

## One-power Fez compiler receipts

All rows below are zero-QPU, one-phase-bit compiler preflights against `ibm_fez`, optimization level 1. Recycled and wide are expected to have the same arithmetic cost at one phase bit.

| Synthesis path | Logical qubits | Native CZ | Compiled depth | Compiled size |
|---|---:|---:|---:|---:|
| HLS/QFT fallback | 26 | 428,681 | 1,183,808 | 1,866,556 recycled |
| Explicit constant-add / default MCX | 15 | 72,229 | 180,783 | 290,759 recycled |
| Explicit constant-add / clean linear MCX | 22 | 84,339 | 203,857 | 338,326 recycled |
| Full-residue permutation / explicit clean MCX | 11 | 15,642 | 39,097 | 65,035 recycled |
| Full-residue permutation / Qiskit `auto` MCX | 11 | 10,587 | 24,192 | 42,373 recycled |
| Full-residue permutation / `n_clean_m15` | 11 | 9,404 | 25,634 | 37,539 recycled |
| Full-residue permutation / **`1_clean_kg24`** | 11 | **9,083** | **23,159** | **38,805** recycled |
| Full-residue permutation / `noaux_v24` | 11 | 36,972 | 109,886 | 169,068 recycled |

The explicit constant-add path improved substantially over the HLS fallback, but `72,229` CZ gates remained far outside a credible present-hardware execution regime. The clean-ancilla linear-MCX arithmetic experiment did not improve that boundary: it increased cost to `84,339` CZ.

## Full-residue generic permutation result

`hardware/ibm_shor35_generic_full_permutation_preflight.py` generates the complete modular multiplication permutation directly from `N`, `a`, and the QPE power:

```text
y < N  -> m*y mod N
y >= N -> y
```

It does not use `r=12` and does not encode only the known 12-state orbit. It synthesizes the entire 64-state six-qubit permutation through cycle decomposition, Gray-path basis transpositions, and phase-controlled adjacent basis-state swaps.

For the first multiplier `m=2`, the generated full-register permutation has:

- 5 nontrivial cycles with lengths `12, 12, 3, 4, 3`;
- 29 basis-state transpositions;
- 117 adjacent basis-state swaps;
- 6 controls per adjacent swap (phase + five work-pattern controls);
- 4 reusable clean scratch qubits.

The first explicit-clean-MCX realization compiled to `15,642` CZ at depth `39,097` using 11 logical qubits. Preserving the adjacent swaps as high-level `MCXGate` operations and letting Qiskit synthesize them improved the boundary substantially.

## MCX synthesis sweep

The one-power zero-QPU MCX sweep compared four profiles against the same Fez target. Best native result:

```text
profile: 1_clean_kg24
logical qubits: 11
native CZ: 9,083
compiled depth: 23,159
compiled size: 38,805
compile time: ~0.14 s
```

Other successful profiles were:

```text
auto          10,587 CZ, depth 24,192
n_clean_m15    9,404 CZ, depth 25,634
noaux_v24     36,972 CZ, depth 109,886
```

Thus `1_clean_kg24` is the current best Fez synthesis for this one-power full-residue circuit by CZ count and also has the lowest depth among the tested profiles.

Relative to the explicit clean-MCX full-permutation result, `9,083` CZ is about a **41.9% reduction**. Relative to the best direct arithmetic path (`72,229` CZ), it is about an **87.4% reduction**. Relative to the original HLS fallback (`428,681` CZ), it is about a **97.9% reduction**.

This is the first order/orbit-independent synthesis path in the project to reach the sub-10k-CZ range for one modular power.

At eight phase bits the nominal simultaneous width remains:

- recycled: 11 logical qubits;
- wide: 18 logical qubits.

This construction is **generic full-register reversible synthesis for small N, not scalable modular arithmetic**. It removes dependence on the known order/orbit from circuit construction but uses truth-table/permutation synthesis whose cost grows exponentially with work-register width.

## Next experiment: zero-QPU phase-width scaling

The best one-power profile is now frozen as `1_clean_kg24` for the next sizing pass. The new zero-QPU scaling harness is:

```bash
python hardware/ibm_shor35_generic_full_permutation_scale.py \
  --backend ibm_fez \
  --phase-bits 2 4 6 8 \
  --kind both \
  --profile 1_clean_kg24 \
  --optimization-level 1
```

It compiles recycled and wide circuits at 2, 4, 6, and 8 phase bits, preserving the same order/orbit-independent full-register modular semantics and reporting native CZ, depth, size, width, and compile time. It never submits a QPU job.

The scaling result decides whether a hardware experiment is even worth designing. The important question is not simple linear multiplication of the one-power `m=2` cost, because the QPE round multipliers are `2, 4, 16, 11, 16, 11, 16, 11` and their full-register permutation costs differ.

Do **not** submit the generic-permutation circuit to a QPU until the 2/4/6/8 compiler scaling receipt is known and an ideal-circuit validation has been completed.
