# RSA-713 IBM-target native-cost preflight result

## Summary

The residue-conditioned small-RSA case `N=713` completed a zero-QPU IBM-target transpilation study against `ibm_fez`.

Public case:

```text
N = 713 = 23 * 31        # factors used only as validation labels
ell = 5
seed base a = 19
transformed base b = 19^5 mod 713 = 563
baseline order = 330
transformed order = 66
order reduction = 5x
```

The staged recycled-QPE schedule was:

```text
4, 6, 8, 10, 12, 14, 16, 18, 20 phase bits
```

The circuit used 15 logical qubits (`1` recycled phase qubit + `10` work qubits + `4` HLS scratch qubits).

No Sampler invocation was made and no QPU job was submitted.

## Primary compiler-weighted result

Exact staged expectation weighted by the IBM-target compiled native cost gave:

```text
phase-round ratio transformed / baseline = 0.5061263839
phase-round reduction                    = 49.3874%

native-CZ ratio transformed / baseline  = 0.4899589346
native-CZ reduction                     = 51.0041%

compiled-depth ratio transformed/base   = 0.4891740773
compiled-depth reduction                = 51.0826%
```

The compiled native-cost advantage was therefore slightly larger than the ideal phase-work advantage.

## Success by textbook precision cap

```text
baseline success probability by cap    = 0.935272
transformed success probability by cap = 0.997279
absolute increase                       = 0.062007  (+6.2007 percentage points)
```

Corresponding cap-failure probabilities were:

```text
baseline failure    = 0.064728
transformed failure = 0.002721
```

This is a ~95.8% reduction in modeled failure-by-cap probability for this selected case. This endpoint is model-derived and case-specific; it is not a hardware fidelity result.

## Same-precision circuit-cost check

At 18 phase bits:

```text
baseline:
  CZ    = 2,643,688
  depth = 4,481,365

transformed:
  CZ    = 2,529,713
  depth = 4,221,190
```

So even before accounting for earlier staged stopping, the transformed modular-unitary circuit was modestly cheaper at the same precision:

```text
18-bit CZ reduction    ~4.31%
18-bit depth reduction ~5.81%
```

At 20 phase bits, the transformed circuit compiled to:

```text
CZ    = 2,813,282
depth = 4,690,913
size  = 11,317,601
```

## Interpretation

This result shows that the residue-conditioned order reduction survives compilation to an actual IBM backend target under the repository's exact small-N full-register synthesis path. In this selected RSA-713 case, the transformed path reduces exact expected IBM-native CZ burden and compiled-depth burden by about one half.

The result combines two effects:

1. **Stopping effect:** the transformed order is smaller, so conservative staged phase estimation succeeds earlier on average.
2. **Circuit-cost effect:** at matched precision, the transformed modular-unitary circuit can itself be somewhat cheaper after transpilation.

## Claim boundary

This is a **compiler-weighted resource result**, not a QPU performance measurement.

It does **not** establish:

- a measured 51% hardware runtime reduction;
- a measured fidelity improvement;
- successful QPU factoring of `713`;
- scalable RSA modular arithmetic;
- practical RSA-2048 capability;
- an asymptotic improvement to Shor's algorithm.

The exact modular multiplication layer remains a truth-table/full-register reversible synthesis intended for small-N validation. Its multi-million-CZ depth makes the current circuit unsuitable for a meaningful N=713 QPU submission.

## Next engineering step

Replace the full-state permutation synthesis with scalable reversible modular arithmetic, then repeat the same IBM-target staged-cost comparison. That isolates whether the ~50% order/stopping advantage persists when the modular-exponentiation layer is implemented with an architecture that scales polynomially rather than by enumerating the full work-register state space.

Source receipt:

```text
results/dark_star_ptp/ibm_residue_rsa_N713_staged_cost_preflight.json
```
