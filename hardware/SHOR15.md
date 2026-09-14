# Real IBM QPU toy Shor test: N=15

`ibm_shor15_hardware.py` runs a genuine order-finding/factor-recovery experiment on IBM hardware for the canonical toy problem `N=15`, `a=2`.

Unlike the earlier injected-eigenphase QPE benchmark, this circuit contains a real 4-qubit modular work register initialized to `|1>` and applies the compiled controlled modular multipliers required by Shor order finding:

- `M2 mod 15`: three controlled SWAPs
- `M4 mod 15`: two controlled SWAPs
- higher powers for `a=2` are identity because the order is 4

The recycled architecture uses one phase ancilla plus the four work qubits, repeatedly measuring/resetting the phase ancilla and applying classical feed-forward. The work register remains coherent throughout the dynamic circuit.

## Scope

This is a compiled demonstration for the small public value `N=15`, not a practical RSA attack. We have **not** factored a 256-bit RSA modulus. The modular multiply networks are special-purpose circuits for `N=15`, matching the standard toy Shor construction. Larger self-generated semiprimes require scalable generic reversible modular arithmetic and much greater quantum resources.

## Pull and activate

```bash
git pull
source ~/ibm-6c2q-venv/bin/activate
```

## Recycled hardware run

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture recycled \
  --phase-bits 4 \
  --shots 256 \
  --max-execution-time 60
```

Ideal four-bit QPE peaks for order `r=4` are `0000`, `0100`, `1000`, and `1100`. The zero phase carries no order information; the other three peaks recover `r=4` and then factors `(3,5)` using `gcd(2^(r/2) +/- 1, 15)`.

## Wide hardware run

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture wide \
  --phase-bits 4 \
  --shots 256 \
  --max-execution-time 60
```

## Preferred matched same-job comparison

`ibm_shor15_matched.py` is the stronger comparison. It chooses one 8-qubit Fez neighborhood, uses the exact same four physical qubits as the **initial modular-work-register placement** for both architectures, reuses the recycled ancilla as one of the wide phase qubits, and submits both circuits in the same Sampler job.

The transpiler may still move logical states during routing, so the controlled claim is **same initial work quartet and same physical neighborhood**, not that work-register logical states remain fixed to physical sites throughout execution.

First inspect the mapping without spending QPU time:

```bash
python hardware/ibm_shor15_matched.py \
  --backend ibm_fez \
  --shots 512 \
  --transpile-only
```

Then run the matched experiment:

```bash
python hardware/ibm_shor15_matched.py \
  --backend ibm_fez \
  --shots 512 \
  --max-execution-time 60
```

The output includes:

- the shared physical neighborhood and shared initial work quartet,
- calibration information for the recycled mid-circuit-measurement ancilla,
- wide/recycled depth, circuit size and CZ counts,
- factor-recovery probability for both architectures,
- ideal-order-peak, zero-peak and off-peak probabilities,
- Wilson 95% intervals and the difference in standard-error units.

Using 512 shots per architecture reduces sampling uncertainty relative to the first independent 256-shot runs while remaining inexpensive compared with the available IBM Open Plan quota.

## Eight-bit phase-register follow-up

An eight-bit phase-estimation follow-up can still use only five simultaneous logical qubits in the recycled architecture, but it performs eight mid-circuit measurement/reset rounds while preserving the four-qubit modular work register:

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture recycled \
  --phase-bits 8 \
  --shots 256 \
  --max-execution-time 90
```
