# Generic reversible modular-arithmetic Shor preflight

This experiment removes the largest algorithmic caveat from the current `N=35`, `a=2`, `r=12` hardware benchmark: the four-qubit work-register unitary is no longer a hand-compiled representation of the known twelve-state orbit.

The new preflight is implemented in:

`hardware/ibm_shor_generic_arithmetic.py`

## What changes

The circuit constructor accepts `N`, `a`, and the number of phase bits.  It does **not** use the multiplicative order to build the circuit.

For each phase-estimation round it classically computes the standard Shor constant

`c_k = a^(2^k) mod N`

and implements controlled multiplication by `c_k` using reversible modular arithmetic.  This classical precomputation is part of ordinary Shor compilation and does not reveal the unknown order.

A controlled modular multiplier is built as follows:

1. Accumulate `c*y mod N` into a clean `n+1`-bit register using controlled constant modular additions.
2. Controlled-swap the result into the `n`-bit work register.
3. Use `c^{-1} mod N` and the new work register to reversibly erase the old input from the accumulator.
4. Return the accumulator and reduction flag to `|0>`.

The constant modular adder uses an exact reversible constant-increment network plus subtract-`N` / conditional-restore reduction.  Its flag qubit is uncomputed before return.

For `N=35`, the generic arithmetic registers are:

- work register: 6 qubits
- arithmetic accumulator: 7 qubits
- reduction flag: 1 qubit
- recycled phase architecture: 1 phase ancilla, for 15 simultaneous logical qubits total
- eight-bit wide phase architecture: 8 phase qubits, for 22 simultaneous logical qubits total

These widths are much larger than the five-qubit affine-orbit recycled experiment because the arithmetic now represents ordinary residues rather than a precompiled 12-state cycle.

## Falsification-first workflow

The V1 script cannot submit a QPU job.  It is intentionally limited to self-test and zero-QPU transpilation.

First run the exhaustive arithmetic network tests:

```bash
python hardware/ibm_shor_generic_arithmetic.py \
  --N 35 --a 2 --phase-bits 8 \
  --self-test-only
```

The self-test checks:

- every input and every constant of the underlying `mod 2^m` constant-adder network;
- every valid residue and constant for addition modulo `N`;
- every valid residue for every controlled multiplier required by the requested QPE precision;
- inactive-control identity behavior;
- cleanup of the arithmetic accumulator and flag.

The multiplicative order is computed only for the validation report and is not passed into either circuit constructor.

If the self-test passes, compile the recycled circuit for an IBM backend without submitting hardware work:

```bash
python hardware/ibm_shor_generic_arithmetic.py \
  --N 35 --a 2 --phase-bits 8 \
  --backend ibm_fez \
  --optimization-level 3 \
  --kind recycled
```

Then compile the wide circuit separately:

```bash
python hardware/ibm_shor_generic_arithmetic.py \
  --N 35 --a 2 --phase-bits 8 \
  --backend ibm_fez \
  --optimization-level 3 \
  --kind wide
```

Separate preflights are recommended because generic arithmetic may be expensive to synthesize.  The script records logical width, abstract gate counts, native entangling-gate count, depth, circuit size, and the full self-test receipt under `results/ibm_shor_generic_arithmetic/`.

No QPU job is submitted by this revision.

## Interpretation boundary

A successful self-test establishes that the work-register unitary is generated from generic reversible modular arithmetic rather than a known orbit.  It does not establish that the resulting circuit is practical on current hardware.

The V1 arithmetic is deliberately transparent and auditable, not asymptotically optimal.  If the transpiled native cost is too large, the next optimization target is the arithmetic itself: lower-cost adders, clean/dirty-ancilla MCX synthesis, constant-propagation, and backend-aware placement.  The mathematical benchmark and the strict/random-output controls should remain frozen while those synthesis choices are compared.

If a generic-arithmetic recycled circuit ultimately recovers the `N=35`, `a=2` order on hardware without using the known order during circuit construction, the result can be described as a reversible modular-arithmetic Shor order-finding implementation rather than an orbit-compiled demonstration.
