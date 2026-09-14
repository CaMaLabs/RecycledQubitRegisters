# Generic modular-arithmetic Shor path

## Goal

Remove the largest algorithmic caveat in the current `N=35, a=2, r=12`
hardware result: the four-qubit affine work register is an exact but
instance-compiled encoding of the known 12-state modular orbit.

The next implementation must construct the modular unitary from only `N` and
`a`, not from the order `r` or a precomputed orbit labeling.

The current generic-arithmetic work has three deliberately different synthesis
paths:

- `hardware/generic_modarith_shor.py` and the IBM HLS preflights;
- `hardware/ibm_shor_generic_arithmetic.py` and
  `hardware/ibm_shor_generic_arithmetic_one_power.py`, which use explicit
  reversible constant-addition / default-MCX networks;
- `hardware/ibm_shor_generic_arithmetic_clean_mcx.py`, which keeps the same
  arithmetic semantics but replaces large MCX gates by reusable clean-ancilla
  linear Toffoli chains.

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

## Direct reversible arithmetic path

`hardware/ibm_shor_generic_arithmetic.py` constructs the same class of Shor
modular powers from `N` and `a` without using the order, but replaces the
problematic high-level controlled arithmetic with explicit reversible
constant-addition networks built from X/CX/CCX/MCX and a clean modular-reduction
flag.

For `N=35` it uses:

- 6 work qubits;
- 7 accumulator/sign qubits;
- 1 modular-reduction flag;
- plus the phase register.

That gives:

- one-power recycled/wide sanity check: **15 logical qubits** each;
- eight-bit recycled: **15 logical qubits**;
- eight-bit wide: **22 logical qubits**.

### Direct one-power compiler receipt

The zero-QPU Fez preflight passed its arithmetic self-test and compiled one
controlled modular multiplier successfully:

| Metric | Recycled | Wide |
|---|---:|---:|
| phase bits | 1 | 1 |
| logical qubits | 15 | 15 |
| abstract depth | 905 | 904 |
| abstract MCX | 716 | 716 |
| abstract CCX | 179 | 179 |
| abstract CSWAP | 6 | 6 |
| compiled depth | 180,783 | 180,783 |
| compiled size | 290,759 | 290,758 |
| CZ gates | 72,229 | 72,229 |
| compile time | 1.02 s | 0.97 s |

This is a substantial synthesis improvement over the HLS fallback:

- CZ count reduced by about **5.94x**;
- depth reduced by about **6.55x**;
- logical width reduced from 26 to 15 qubits for the one-power test.

However, **72,229 CZ gates for one modular power is still far too costly for a
credible QPU experiment**, and scaling this version directly to eight phase
bits is not justified.  No QPU job was submitted.

The dominant remaining issue is now explicit: the circuit contains **716 MCX
gates**, and default no-ancilla lowering is extremely expensive.

## Clean-ancilla linear-MCX pivot

The next synthesis experiment is
`hardware/ibm_shor_generic_arithmetic_clean_mcx.py`.

It preserves the same generic reversible modular arithmetic but replaces each
k-control MCX with a reusable clean-ancilla chain using:

```text
clean ancillas = k - 2
toffolis       = 2k - 3
```

For the current seven-bit accumulator the largest carry operation has nine
controls, so seven reusable clean scratch qubits are sufficient.  They are
returned to zero after every MCX and reused throughout the entire circuit.

Nominal widths become:

- one phase bit: **22 logical qubits** for both architectures;
- eight-bit recycled: **22 logical qubits**;
- eight-bit wide: **29 logical qubits**.

The width increases relative to the 15/22-qubit default-MCX design, but the
trade is intentional: Fez has abundant width, while entangling-gate count is the
actual bottleneck.  This experiment tests whether spending seven clean ancillas
can collapse the MCX decomposition cost enough to make generic arithmetic
plausible.

Zero-QPU command:

```bash
python hardware/ibm_shor_generic_arithmetic_clean_mcx.py \
  --backend ibm_fez \
  --phase-bits 1 \
  --kind both \
  --optimization-level 1
```

Do not submit generic-arithmetic circuits to hardware until this and any further
synthesis variants are compared by native CZ/depth.

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

### 2. Preserve compiler boundary results

The HLS fallback and direct default-MCX one-power tests are preserved as
negative/resource-boundary results.  They establish that semantic correctness
alone is not sufficient; the arithmetic synthesis strategy dominates native
hardware cost.

### 3. Clean-MCX one-power preflight

Run the reusable-clean-ancilla linear-MCX variant at one phase bit.  If it is
materially smaller than 72,229 CZ, continue optimizing this family.  If it is
not, pivot to a different constant-adder/multiplier construction instead of
scaling phase precision.

### 4. Scale compiler-only circuits only if justified

Only if one modular power reaches a substantially lower native cost should the
compiler-only circuit be scaled to 2/4/6/8 phase bits.  Optimization level 1 is
the first sizing pass.  Higher optimization levels are worth trying only after
the raw synthesis boundary is known.

### 5. Arithmetic optimization targets

Likely targets are:

- ripple-carry constant addition with bounded clean ancillas;
- relative-phase Toffoli / MCX synthesis;
- in-place constant multiplication rather than compute/swap/uncompute;
- modular doubling and fixed-constant multiplication specializations generated
  from the supplied multiplier, not from the known order;
- eliminating redundant carries and repeated add/unadd structure;
- topology-aware synthesis before physical placement;
- comparing candidate arithmetic by **native IBM CZ/depth cost**, not abstract
  gate count.

Any optimization may depend on `N`, `a`, and the classically precomputed Shor
constants `a^(2^k) mod N`; it must not use the unknown multiplicative order to
construct a reduced orbit circuit.

### 6. Circuit-level ideal verification

Before hardware execution, verify the selected modular multiplier and complete
phase-estimation circuit in simulation.  The critical criterion is that it
recovers the same ideal finite-precision `r=12` distribution as the existing
reference while the circuit builder itself never receives `r`.

### 7. Matched physical-layout experiment

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
