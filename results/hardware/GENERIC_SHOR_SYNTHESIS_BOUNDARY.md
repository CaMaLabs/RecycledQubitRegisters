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

This construction is **generic full-register reversible synthesis for small N, not scalable modular arithmetic**. It removes dependence on the known order/orbit from circuit construction but uses truth-table/permutation synthesis whose cost grows exponentially with work-register width.

## Phase-width scaling on Fez target

The `1_clean_kg24` profile was frozen and compiler-only scaling was run at 2, 4, 6, and 8 phase bits against the same `ibm_fez` target, optimization level 1. No QPU jobs were submitted.

| Phase bits | Recycled qubits | Wide qubits | Recycled CZ | Wide CZ | Recycled depth | Wide depth |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 11 | 12 | 17,396 | 16,789 | 43,266 | 43,693 |
| 4 | 11 | 14 | 30,373 | 32,577 | 80,155 | 81,014 |
| 6 | 11 | 16 | 43,557 | 50,226 | 116,068 | 122,010 |
| 8 | 11 | 18 | **59,061** | **63,727** | **153,418** | **157,017** |

The round multipliers are `2, 4, 16, 11, 16, 11, 16, 11`; their generated full-register swap counts are `117, 108, 96, 96, 96, 96, 96, 96`.

At 8 phase bits, recycling removes 7 simultaneous logical qubits (`18 -> 11`, a 38.9% width reduction), while the auto-routed compiler receipt is also modestly smaller in native cost: `59,061` versus `63,727` CZ (7.3% lower) and depth `153,418` versus `157,017` (2.3% lower). At 6 phase bits the recycled CZ advantage is larger (`43,557` versus `50,226`, 13.3% lower). At 2 phase bits recycled uses slightly more CZ, so the compiler-only gate-count advantage is not universal.

These are **compiler/resource results only**, not a matched physical-layout hardware comparison. Auto routing can choose different physical placements, and no claim about hardware success probability follows from these numbers alone.

## Exact ideal validation: PASS

`hardware/validate_shor35_generic_full_permutation_ideal.py` independently validates the full-register path without using the known order to construct either simulation:

1. wide QPE is computed directly from `N`, `a`, modular exponentiation, and an exact inverse-QFT transform;
2. recycled QPE is simulated branch-by-branch with mid-circuit measurement and classical feed-forward using the generated full-residue modular permutations;
3. every generated six-bit modular permutation and its swap network is checked exactly;
4. the resulting wide and recycled distributions are compared to each other and to the existing finite-precision order reference only after construction.

The local validation run at phase widths `2, 4, 6, 8` completed with:

```text
===== OVERALL =====
{
  "pass": true
}
```

This closes the semantic gate for the full-register small-N permutation implementation: the correct finite-precision Shor distribution is reproduced without supplying `r=12` or a hand-encoded 12-state orbit to the constructor.

It does **not** make the implementation scalable modular arithmetic. The current truth-table/permutation synthesis still grows exponentially with work-register width.

## Cycle-pivot and compiler optimizer result

`hardware/ibm_shor35_generic_permutation_optimizer.py` keeps the same exact 64-state modular permutation but chooses a lower-cost star-transposition pivot for every nontrivial cycle, then sweeps MCX HLS method, optimization level, and transpiler seed.

The decomposition reduced Gray-path adjacent basis swaps from:

- 6-bit: `609 -> 545` (`10.5%` fewer);
- 8-bit: `801 -> 709` (`11.5%` fewer).

The best Fez-target recycled receipts were both obtained with `n_clean_m15`, optimization level 3, seed `2026`:

| Phase bits | Logical qubits | Native CZ | Compiled depth | Compiled size |
|---:|---:|---:|---:|---:|
| 6 | 11 | **30,823** | **64,812** | 116,301 |
| 8 | 11 | **40,194** | **84,480** | 151,664 |

Relative to the earlier frozen scaling receipt, the combined decomposition/compiler search reduced:

- 6-bit CZ from `43,557 -> 30,823` (`29.2%`) and depth from `116,068 -> 64,812` (`44.2%`);
- 8-bit CZ from `59,061 -> 40,194` (`31.9%`) and depth from `153,418 -> 84,480` (`44.9%`).

This is a substantial improvement, but `30k-40k` native CZ remains too large to treat as a credible present-day N=35 hardware execution target. No QPU job was submitted.

## Next experiment: direct arbitrary-basis transpositions

The Gray-path representation is still wasting expensive six-control MCXs. A transposition between arbitrary six-bit basis states `|u>` and `|v>` at Hamming distance `d` was previously implemented as `2d-1` adjacent swaps, each requiring a phase-controlled six-control MCX.

A cheaper exact identity is now implemented in `hardware/ibm_shor35_generic_permutation_direct_transposition.py`:

1. choose one differing target bit `t`;
2. apply an invertible CNOT basis fold `CNOT(t -> j)` for every other differing bit;
3. after the fold, `u` and `v` differ in only bit `t`;
4. apply one phase-controlled pattern MCX;
5. undo the fold.

Therefore each arbitrary basis-state transposition costs exactly one six-control MCX plus `2(d-1)` ordinary CNOTs, instead of `2d-1` six-control MCXs. The primitive is exhaustively checked on all 64 work-register basis states, and the complete modular permutation is revalidated before compilation.

For the current optimal cycle factorizations this changes the high-level entangling structure dramatically:

- 6-bit QPE: `545` six-control MCXs -> **135** six-control MCXs + `410` basis-change CNOTs;
- 8-bit QPE: `709` six-control MCXs -> **175** six-control MCXs + `534` basis-change CNOTs.

That is roughly a **75% reduction in the expensive high-control operations** while preserving the exact full-register modular map and continuing to use neither the multiplicative order nor the known orbit in construction.

Zero-QPU command:

```bash
python hardware/ibm_shor35_generic_permutation_direct_transposition.py \
  --backend ibm_fez \
  --phase-bits 6 8 \
  --kind recycled \
  --profiles n_clean_m15 1_clean_kg24 2_clean_kg24 default \
  --optimization-levels 2 3 \
  --seeds 2026 8776 9401
```

Do not submit the generic-permutation path to hardware yet. If the direct-transposition identity converts the expected high-level reduction into a large native-CZ reduction, then the next step is matched physical-placement optimization and a fresh hardware go/no-go decision.