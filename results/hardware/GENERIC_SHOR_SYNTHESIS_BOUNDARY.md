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

The absolute 8-bit cost remains very large for current noisy hardware.

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

The validator uses a default maximum-probability tolerance of `1e-10`. No QPU job is submitted by this validation path.

This closes the semantic gate for the full-register small-N permutation implementation: the correct finite-precision Shor distribution is reproduced without supplying `r=12` or a hand-encoded 12-state orbit to the constructor.

It does **not** make the implementation scalable modular arithmetic. The current truth-table/permutation synthesis still grows exponentially with work-register width.

## Next experiment: reduce the full-register synthesis cost

The next compiler-only pass is `hardware/ibm_shor35_generic_permutation_optimizer.py`.

It retains the exact full 64-state modular permutation but improves its decomposition before routing. For each nontrivial permutation cycle it tries every cyclic choice of star-transposition pivot and selects the one requiring the fewest Gray-path adjacent basis swaps. Every candidate cycle factorization is checked exactly, and the final complete swap network is revalidated against the generated modular permutation.

The optimizer then sweeps MCX HLS profile, Qiskit optimization level, and transpiler seed. The first target is the recycled circuit at 6 and 8 phase bits, because 6 bits is materially cheaper while still providing a strict direct-order signal in the existing postprocessor.

Zero-QPU command:

```bash
python hardware/ibm_shor35_generic_permutation_optimizer.py \
  --backend ibm_fez \
  --phase-bits 6 8 \
  --kind recycled \
  --profiles 1_clean_kg24 n_clean_m15 auto \
  --optimization-levels 1 2 3 \
  --seeds 8776 9401 2026
```

This command submits **no QPU jobs**. It records the exact baseline-vs-optimized adjacent-swap counts and reports the lowest native CZ/depth result across the compiler sweep.

Do not promote the generic-permutation path to hardware yet. The semantic gate is now passed; the remaining gating problem is absolute native cost and, after that, matched physical placement.