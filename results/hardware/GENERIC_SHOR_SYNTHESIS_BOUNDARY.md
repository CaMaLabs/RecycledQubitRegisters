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

The explicit constant-add path improved substantially over the HLS fallback, reducing one-power CZ cost by about `5.94x`. However, `72,229` CZ gates remains far outside a credible present-hardware execution regime.

The clean-ancilla linear-MCX experiment did **not** improve this boundary. It increased native cost from `72,229` to `84,339` CZ (`+16.8%`) and depth from `180,783` to `203,857` (`+12.8%`) while increasing width from 15 to 22 logical qubits. The compiler evidently handles the original MCX representation better than the manually expanded exact-Toffoli chain for this topology/target.

This is retained as a negative result. Do not scale either arithmetic path directly to 8 phase bits or submit it to a QPU.

## Next experiment: full-residue generic permutation synthesis

The next zero-QPU experiment separates **order/orbit independence** from **scalable arithmetic**.

`hardware/ibm_shor35_generic_full_permutation_preflight.py` generates the complete modular multiplication permutation directly from `N`, `a`, and the QPE power:

```text
y < N  -> m*y mod N
y >= N -> y
```

It does not use `r=12` and does not encode only the 12-state orbit. Instead, it synthesizes the entire 64-state six-qubit permutation through cycle decomposition, Gray-path basis transpositions, and phase-controlled adjacent basis-state swaps.

For the first multiplier `m=2`, the generated full-register permutation has:

- 5 nontrivial cycles with lengths `12, 12, 3, 4, 3`;
- 29 basis-state transpositions;
- 117 adjacent basis-state swaps;
- 6 controls per adjacent swap (phase + five work-pattern controls);
- 4 reusable clean scratch qubits;
- 1,053 abstract CCX gates from the clean-MCX chains before backend routing/decomposition.

At eight phase bits the nominal simultaneous width is only:

- recycled: 11 logical qubits;
- wide: 18 logical qubits.

This construction is **generic full-register reversible synthesis for small N, not scalable modular arithmetic**. A successful hardware result from it would remove dependence on the known order/orbit, but would not by itself establish a scalable arithmetic Shor implementation.

Run the one-power zero-QPU preflight first:

```bash
python hardware/ibm_shor35_generic_full_permutation_preflight.py \
  --backend ibm_fez \
  --phase-bits 1 \
  --kind both \
  --optimization-level 1
```

The absolute native CZ/depth result determines whether this path deserves 2/4/6/8-bit compiler scaling. No QPU execution should occur before that boundary is known.
