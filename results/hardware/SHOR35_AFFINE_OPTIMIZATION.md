# N=35 affine orbit optimization

The first `N=35`, `a=2`, `r=12` hardware run reached the uniform-noise floor at the strict direct-order metric. The natural-label 4-qubit orbit encoding compiled to 388 CZ gates and depth 1209 in the recycled circuit at optimization level 3.

To attack that synthesis bottleneck, `hardware/ibm_shor35_affine_matched.py` uses a conjugate 4-bit encoding of the same 12-state modular orbit. The 16 computational basis states split into a 12-cycle and an unused disjoint 4-cycle under one affine permutation.

The modular exponent orbit is encoded on the 12-cycle

`4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4`.

These states correspond in order to

`1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1 (mod 35)`.

The encoded initial modular state `|1>` is basis state 4 (`0100` in the work-register integer convention); both wide and recycled circuits explicitly prepare that state before phase estimation.

In this encoding the required work-register powers are affine CNOT/X networks:

- `U^1`: 3 CNOT + 1 X,
- `U^2`: 2 CNOT + 1 X,
- `U^4`: 2 CNOT,
- `U^8`: 2 CNOT.

After adding the phase control, CNOT becomes CCX and X becomes CX. For six phase bits, whose power sequence is `1,2,4,8,4,8`, the controlled modular-orbit workload is therefore only **13 CCX + 2 CX before backend routing/synthesis**.

This is exactly the same order-12 eigenvalue problem under a basis relabeling of the compiled orbit subspace. It is still a compiled-orbit experiment, not a generic reversible modular multiplier.

## IBM Fez transpile result

The affine self-test passed for every required power and for the full modular-orbit mapping. At optimization level 3 on `ibm_fez`, six phase bits compiled to:

| Metric | Natural-label recycled | Affine recycled | Affine wide |
|---|---:|---:|---:|
| Logical qubits | 5 | **5** | 10 |
| Depth | 1209 | **466** | 583 |
| Circuit size | 1746 | **603** | 889 |
| CZ gates | 388 | **137** | 212 |

Relative to the previous natural-label recycled circuit, the affine encoding reduces compiled depth by about **61.5%**, circuit size by about **65.5%**, and CZ count by about **64.7%**.

Within the affine matched comparison, recycled uses 5 versus 10 simultaneous logical qubits, about **20.1% less compiled depth**, about **32.2% smaller circuit size**, and about **35.4% fewer CZ gates** than wide.

The affine recycled circuit is also substantially lighter than the previous successful `N=21` recycled hardware circuit (137 versus 193 CZ gates; depth 466 versus 707), making a new `N=35` hardware attempt scientifically justified.

## Run

```bash
python hardware/ibm_shor35_affine_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --optimization-level 3 \
  --max-execution-time 120
```

Interpret the result against the uniform-noise baseline and strict direct-order metric, not only the permissive verified-multiple factor-recovery metric.
