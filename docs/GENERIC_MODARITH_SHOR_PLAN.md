# Generic modular-arithmetic Shor path

## Goal

Remove the largest algorithmic caveat in the current `N=35, a=2, r=12`
hardware result: the four-qubit affine work register is an exact but
instance-compiled encoding of the known 12-state modular orbit.

The next implementation must construct the modular unitary from only `N` and
`a`, not from the order `r` or a precomputed orbit labeling.

The new core is:

- `hardware/generic_modarith_shor.py`
- `hardware/ibm_shor35_generic_modarith_preflight.py`

The first file implements reversible modular arithmetic over the complete
six-qubit residue register for `N=35`.  The second lowers those circuits to a
real IBM backend target but **never submits a QPU job**.

## What is different from the affine experiment

The affine circuit knows a special four-qubit encoding of the twelve states
visited by `2^x mod 35` and uses a very short affine permutation to advance
through that orbit.

The generic-arithmetic circuit does not use `r=12` or that orbit encoding.
For every QPE power it computes the standard Shor constant

```text
m_k = a^(2^k) mod N
```

from `N` and `a`, then applies reversible multiplication by `m_k` to the full
binary residue register.  For all six-bit basis states:

```text
y < N   -> m_k * y mod N
y >= N  -> y
```

A validity flag explicitly protects the unused computational states.  The
accumulator, constant register, modular wrap flag, validity flag, and HLS
scratch qubits are returned clean.

This removes dependence on the known order from circuit construction.

## Arithmetic construction

The modular constant adder uses the reversible identity

```text
wrap = [x >= N-k]
x    = x + k mod 2^n
if wrap: x = x - N mod 2^n
wrap ^= [x < k]
```

For valid residues the final predicate exactly equals the original wrap bit,
so the flag is uncomputed.

Controlled multiplication uses compute/swap/uncompute:

```text
acc <- m*y mod N
swap(work, acc)
acc <- acc - m^-1*work mod N
```

Qiskit `ModularAdderGate` and `IntegerComparatorGate` are left as high-level
arithmetic objects until transpilation.  Dedicated clean scratch is included so
the HLS stage can choose polynomial comparator synthesis where practical.

## Width for N=35

`N=35` needs a six-qubit residue register.  The first clean implementation uses:

- 6 work qubits;
- 6 accumulator qubits;
- 6 reusable constant qubits;
- 1 modular-wrap flag;
- 1 valid-residue flag;
- 5 clean HLS scratch qubits.

That is 25 arithmetic qubits before the phase register.

Therefore at eight phase bits:

- recycled: **26 simultaneous logical qubits**;
- wide: **33 simultaneous logical qubits**.

The phase-recycling saving remains seven qubits, but it is now being measured
against a much more realistic arithmetic footprint instead of the four-qubit
compiled orbit.

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

The test exhaustively checks every valid modular-add input and every full
six-bit work-register basis state for every controlled QPE multiplier.  The
expected report says:

```text
order_used_in_circuit_construction: false
full_register_semantics: multiply modulo N for y<N; identity for y>=N; arithmetic ancillas clean
```

### 2. One-power IBM compiler preflight

This is still zero-QPU.  It measures the cost of one real controlled modular
multiplier after lowering to the backend ISA:

```bash
python hardware/ibm_shor35_generic_modarith_preflight.py \
  --backend ibm_fez \
  --phase-bits 1 \
  --architecture both \
  --optimization-level 1
```

Start here.  Do not jump directly to an eight-bit QPU experiment.  The result
will tell us whether the present structured arithmetic is remotely tractable or
needs another synthesis pass first.

### 3. Scale the compiler-only circuit

If one power is tractable, repeat with `--phase-bits 4`, then `6`, then `8`.
Optimization level 1 is the first sizing pass; level 3 is only worth trying
after the circuit size is known.

### 4. Arithmetic optimization

Likely optimization targets are:

- eliminate the explicit six-qubit constant register with a constant-specific
  adder;
- compare Qiskit `ModularAdder` HLS choices;
- reduce comparator scratch/controls;
- exploit repeated powers for `N=35, a=2` without using the order in circuit
  semantics;
- topology-aware synthesis before physical placement;
- compare ripple-carry and Fourier arithmetic by *native IBM CZ/depth cost*, not
  by abstract gate count.

### 5. Circuit-level ideal verification

Before hardware execution, verify the selected modular multiplier and the
complete phase-estimation circuit in simulation.  The critical criterion is
that the implementation recovers the same ideal finite-precision `r=12`
distribution as the existing reference while the circuit builder itself never
receives `r`.

### 6. Matched physical-layout experiment

Only after the arithmetic circuit is frozen should we build a calibration-aware
placement search and submit recycled/wide in a same-job matched control, using
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
