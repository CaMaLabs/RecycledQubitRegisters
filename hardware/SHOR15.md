# Real IBM QPU toy Shor test: N=15

`ibm_shor15_hardware.py` runs a genuine order-finding/factor-recovery experiment on IBM hardware for the canonical toy problem `N=15`, `a=2`.

Unlike the earlier injected-eigenphase QPE benchmark, this circuit contains a real 4-qubit modular work register initialized to `|1>` and applies the compiled controlled modular multipliers required by Shor order finding:

- `M2 mod 15`: three controlled SWAPs
- `M4 mod 15`: two controlled SWAPs
- higher powers for `a=2` are identity because the order is 4

The recycled architecture uses one phase ancilla plus the four work qubits, repeatedly measuring/resetting the phase ancilla and applying classical feed-forward. The work register remains coherent throughout the dynamic circuit.

## 1. Pull the repo

```bash
git pull
source ~/ibm-6c2q-venv/bin/activate
```

## 2. Transpile only first — no QPU submission

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture recycled \
  --phase-bits 4 \
  --shots 256 \
  --transpile-only
```

Inspect the physical layout, depth, CZ count, resets, and `measure_2` count.

## 3. Submit the 5-qubit recycled Shor circuit

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture recycled \
  --phase-bits 4 \
  --shots 256 \
  --max-execution-time 60
```

Ideal four-bit QPE peaks for order `r=4` are `0000`, `0100`, `1000`, and `1100`. The zero phase carries no order information; the other three peaks recover `r=4` and then factors `(3,5)` using `gcd(2^(r/2) +/- 1, 15)`.

The script reports both whether factors were recovered at all and a conservative per-shot factor-recovery probability. Noisy bitstrings are counted as factor-bearing only when they are close to a verified nonzero `s/r` QPE peak.

## 4. Optional conventional-wide comparison

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture compare \
  --phase-bits 4 \
  --shots 256 \
  --max-execution-time 90
```

This submits both the 5-qubit recycled circuit and the 8-qubit conventional circuit in one job. The wide circuit uses four phase qubits plus four work qubits and a coherent inverse QFT.

## 5. Eight-bit phase register follow-up

IBM's Shor tutorial uses `m=2n=8` phase-estimation qubits for `N=15`. Once the four-bit hardware test succeeds, run:

```bash
python hardware/ibm_shor15_hardware.py \
  --backend ibm_fez \
  --architecture recycled \
  --phase-bits 8 \
  --shots 256 \
  --max-execution-time 90
```

This still uses only five simultaneous logical qubits in the recycled architecture, but performs eight mid-circuit measurement/reset rounds while preserving the four-qubit modular work register.

## Scope

This is a compiled demonstration for the small public value `N=15`, not a practical RSA attack. The modular multiply networks are special-purpose circuits for `N=15`, matching the standard IBM Shor demonstration. The next step after hardware validation is to substitute a generic reversible modular multiplier for larger self-generated toy semiprimes.
