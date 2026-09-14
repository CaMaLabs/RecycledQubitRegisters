# Generic modular-arithmetic Shor path

## Goal

Remove the largest algorithmic caveat in the current `N=35, a=2, r=12`
hardware result: the four-qubit affine work register is an exact but
instance-compiled encoding of the known 12-state modular orbit.

The next implementation must construct the modular unitary from only `N` and
`a`, not from the order `r` or a precomputed orbit labeling.

The current generic-arithmetic work has two deliberately different synthesis
paths:

- `hardware/generic_modarith_shor.py` and the IBM HLS preflights;
- `hardware/ibm_shor_generic_arithmetic.py` and
  `hardware/ibm_shor_generic_arithmetic_one_power.py`, which use explicit
  reversible constant-addition / MCX networks.

All of these are zero-QPU until a circuit is explicitly promoted to a hardware
runner.

## What is different from the affine experiment

The affine circuit knows a special four-qubit encoding of the twelve states
visited by `2^x mod 35` and uses a very short affine permutation to advance
through that orbit.

The generic-arithmetic circuit does not use `r=12` or that orbit encoding.
For every QPE power it computes the standard Shor constant

```text
m_k = a^(2^k) mod N
```

from `N` and `a`, then applies reversible multiplication by `m_k` to a binary
residue register.  The intended Shor subspace is the ordinary residue basis,
not a hand-labeled twelve-state orbit.

This removes dependence on the known order from circuit construction.

## HLS arithmetic path

The first clean implementation uses a six-qubit work register, six-qubit
accumulator, six-qubit constant register, modular-wrap flag, valid-residue flag,
and five HLS scratch qubits.  At eight phase bits its nominal width is:

- recycled: **26 simultaneous logical qubits**;
- wide: **33 simultaneous logical qubits**.

Its semantic self-test passed exhaustively for `N=35, a=2, phase_bits=8`:

- `1190` modular-add cases;
- `1024` controlled modular-multiply cases;
- every six-bit basis state tested for every QPE multiplier;
- `order_used_in_circuit_construction: false`;
- valid residues multiply modulo 35, invalid six-bit states are identity, and
  arithmetic ancillas return clean.

### IBM compiler boundary observed 14 September 2026

The initial annotated-HLS route first exposed Qiskit synthesis compatibility
problems for controlled `IntegerComparatorGate`.  An explicit compatibility
fallback then successfully lowered one full controlled modular multiply to the
`ibm_fez` target.

That successful compiler receipt was nevertheless a decisive negative result:

| Metric | Recycled | Wide |
|---|---:|---:|
| phase bits | 1 | 1 |
| logical qubits | 26 | 26 |
| compiled depth | 1,183,808 | 1,183,808 |
| compiled size | 1,866,556 | 1,866,554 |
| CZ gates | 428,681 | 428,681 |
| compile time | 10.41 s | 10.04 s |

The recycled/wide equality is expected at one phase bit.  The important result
is the absolute arithmetic cost: **428,681 CZ gates for one controlled modular
multiplication is far beyond a sensible QPU experiment.**  No QPU job was
submitted.

Therefore the HLS/QFT fallback is preserved as an auditable upper-bound / failed
synthesis path, not as the candidate for hardware execution.

## Direct reversible arithmetic pivot

The next candidate is `hardware/ibm_shor_generic_arithmetic.py`.  It constructs
the same class of Shor modular powers from `N` and `a` without using the order,
but replaces the problematic high-level controlled arithmetic with explicit
reversible constant-addition networks built from X/CX/CCX/MCX and a clean
modular-reduction flag.

For `N=35` it uses:

- 6 work qubits;
- 7 accumulator/sign qubits;
- 1 modular-reduction flag;
- plus the phase register.

That gives a much smaller nominal width:

- one-power recycled/wide sanity check: **15 logical qubits** each;
- eight-bit recycled: **15 logical qubits**;
- eight-bit wide: **22 logical qubits**.

The one-power zero-QPU backend preflight is:

```bash
python hardware/ibm_shor_generic_arithmetic_one_power.py \
  --backend ibm_fez \
  --optimization-level 1 \
  --kind both
```

This run is the next go/no-go test.  If native CZ/depth are still extreme, the
next optimization should target the controlled constant adder / MCX synthesis
itself rather than scaling to more phase bits.

## Validation ladder

### 1. Pure semantic self-test

No IBM account and no QPU use:

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull
source ~/ibm-6c2q-venv/bin/activate

python hardware/generic_modarith_shor.py \
  --N 35 \
  --a 2 \
  --phase-bits 8
```

The passed report establishes that the order is not supplied to circuit
construction and that the full six-bit HLS arithmetic semantics are correct.

### 2. Direct one-power IBM compiler preflight

This is also zero-QPU:

```bash
python hardware/ibm_shor_generic_arithmetic_one_power.py \
  --backend ibm_fez \
  --optimization-level 1 \
  --kind both
```

Do not jump directly to an eight-bit QPU experiment.  The native resource
receipt from this run determines whether the direct arithmetic is remotely
tractable.

### 3. Scale compiler-only circuits only if justified

If one direct arithmetic power is tractable, scale to 2/4/6/8 phase bits.
Optimization level 1 is the first sizing pass.  Higher optimization levels are
worth trying only after the raw synthesis boundary is known.

### 4. Arithmetic optimization targets

Likely targets are:

- controlled constant-addition synthesis;
- MCX decomposition strategy and available clean/dirty ancillas;
- in-place constant multiplication rather than compute/swap/uncompute;
- eliminating dedicated constant registers;
- modular doubling / constant-multiply specializations that are generated from
  the supplied multiplier rather than from a known order;
- topology-aware synthesis before physical placement;
- comparing ripple-carry and Fourier arithmetic by **native IBM CZ/depth cost**,
  not abstract gate count.

Any optimization may depend on `N`, `a`, and the classically precomputed Shor
constants `a^(2^k) mod N`; it must not use the unknown multiplicative order to
construct a reduced orbit circuit.

### 5. Circuit-level ideal verification

Before hardware execution, verify the selected modular multiplier and complete
phase-estimation circuit in simulation.  The critical criterion is that it
recovers the same ideal finite-precision `r=12` distribution as the existing
reference while the circuit builder itself never receives `r`.

### 6. Matched physical-layout experiment

Only after the arithmetic circuit is frozen should a calibration-aware placement
search be built and recycled/wide submitted in a same-job matched control, using
the existing strict direct-order, permissive, Hellinger, TV, and uniform-output
analysis.

## Claim boundary

A successful hardware run of this version would support wording substantially
stronger than the current affine result:

> We execute a reversible modular-arithmetic Shor order-finding implementation
> for `N=35, a=2` using dynamic phase-register recycling on superconducting
> quantum hardware; circuit construction uses `N` and `a` but not the known
> order or a compiled orbit encoding.

It would still be a small-number hardware demonstration, not cryptographic-scale
factoring.  Efficient fault-tolerant Shor requires much more optimized
arithmetic, error correction, and vastly larger resources.
