# N=35 affine orbit optimization

The first `N=35`, `a=2`, `r=12` hardware run reached the uniform-noise floor at the strict direct-order metric.  The natural-label 4-qubit orbit encoding compiled to 388 CZ gates in the recycled circuit at optimization level 3.

To attack that synthesis bottleneck, `hardware/ibm_shor35_affine_matched.py` uses a conjugate 4-bit encoding of the same 12-state modular orbit.  The 16 computational basis states split into a 12-cycle and an unused disjoint 4-cycle under one affine permutation.

The modular exponent orbit is encoded on the 12-cycle

`4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4`.

These states correspond in order to

`1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1 (mod 35)`.

In this encoding the required work-register powers are affine CNOT/X networks:

- `U^1`: 3 CNOT + 1 X,
- `U^2`: 2 CNOT + 1 X,
- `U^4`: 2 CNOT,
- `U^8`: 2 CNOT.

After adding the phase control, CNOT becomes CCX and X becomes CX.  For six phase bits, whose power sequence is `1,2,4,8,4,8`, the controlled modular-orbit workload is therefore only **13 CCX + 2 CX before backend routing/synthesis**.

This is exactly the same order-12 eigenvalue problem under a basis relabeling of the compiled orbit subspace.  It is still a compiled-orbit experiment, not a generic reversible modular multiplier.

Before any new QPU run, use:

```bash
python hardware/ibm_shor35_affine_matched.py --phase-bits 6 --self-test
python hardware/ibm_shor35_affine_matched.py --backend ibm_fez --phase-bits 6 --shots 512 --optimization-level 3 --transpile-only
```

Only if the transpiled CZ/depth counts are materially below the 388-CZ / depth-1209 natural-label recycled baseline should the hardware run be repeated.
