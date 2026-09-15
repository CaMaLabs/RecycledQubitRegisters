# N=781 residue-conditioned IBM-native cost result

This note records the completed zero-QPU IBM-target compiler preflight for the post-replication `ell=7` scout case.

## Case

```text
N = 781 = 11 * 71
ell = 7
public seed base a = 29
transformed base b = a^7 mod N = 380
validation-only order: 70 -> 10
order reduction: 7x
backend target: ibm_fez
logical qubits in the current full-register implementation: 15
```

The factorization and multiplicative orders above are validation labels. They are not used to construct the modular-unitary circuits.

## Exact staged-QPE result

Using the same conservative staged stopping model used by the residue-prime replication audit:

```text
phase-round ratio transformed / baseline = 0.30515769568639634
phase-round reduction                     = 69.48423043136036%
```

## IBM-target native-cost result

The complete Fez-target compile-weighted expectation was:

```text
native CZ ratio transformed / baseline       = 0.25722067317064556
native CZ reduction                           = 74.27793268293544%
compiled-depth ratio transformed / baseline  = 0.2566410793319597
compiled-depth reduction                      = 74.33589206680403%
success by textbook precision cap            = 0.998842 / 0.999982
```

The compiled native-cost reduction is therefore larger than the ideal phase-work reduction for this selected case.

At 18 phase bits, the same-precision circuits compiled to:

```text
baseline a=29:
  CZ    = 2,776,500
  depth = 4,651,285

transformed b=380:
  CZ    = 2,305,094
  depth = 3,867,664
```

At 20 phase bits, the transformed path compiled to:

```text
CZ    = 2,559,905
depth = 4,292,140
size  = 10,345,691
```

## Relation to the N=713 result

This independently extends the same compiler-weighted direction seen in the `ell=5`, `N=713` scout case:

```text
N=713, ell=5:
  phase-work reduction = 49.39%
  native-CZ reduction  = 51.00%
  depth reduction      = 51.08%

N=781, ell=7:
  phase-work reduction = 69.48%
  native-CZ reduction  = 74.28%
  depth reduction      = 74.34%
```

These are selected hardware-scout case studies after the independent statistical replication. They are not additional confirmatory population-level evidence.

## Claim boundary

This result establishes a compiler-weighted resource reduction for the selected small semiprime when exact full-register modular permutations are transpiled to the IBM Fez target.

It does **not** establish:

- a measured QPU runtime or fidelity improvement;
- practical factoring of `N=781` on current hardware;
- scalable modular arithmetic;
- an RSA-2048 resource estimate;
- an asymptotic improvement to Shor's algorithm.

The current truth-table/full-register arithmetic still produces multi-million-CZ circuits. The next project track therefore returns to qubit/resource optimization: phase-register recycling, scratch-ancilla minimization, ancilla reuse, and wide-versus-recycled target compilation.
