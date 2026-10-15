# Dark Star + recycled-QPE scalable-arithmetic audit

Date: 2026-10-14

## Question

The previous project tracks established two useful effects separately:

1. **phase-register recycling** can keep the phase/control width fixed while requested precision grows; and
2. **public residue-conditioned odd-power preconditioning** can reduce the actual multiplicative order seen by an adaptive/staged Shor workflow and therefore make it stop earlier.

The strongest Dark Star compiler receipts so far used exact small-N full-register truth-table permutations. Those circuits are intentionally non-scalable. The next falsification gate is therefore:

> Does the Dark Star stopping advantage remain when modular multiplication is represented by a genuinely polynomial reversible-arithmetic construction rather than the small-N full-state permutation synthesizer?

## Frozen resource model

The audit in:

`hardware/dark_star_recycled_scalable_arithmetic_audit.py`

uses an analytic gate-count mirror of the existing generic clean-ancilla arithmetic implementation in:

`hardware/ibm_shor_generic_arithmetic_clean_mcx.py`.

For an n-bit modulus it uses:

- n work qubits;
- n+1 accumulator qubits;
- one modular-reduction flag;
- n+1 reusable clean MCX scratch qubits;
- either one recycled phase qubit or m simultaneous wide phase qubits.

The controlled modular multiply is constructed from controlled constant modular additions, controlled swaps, inverse multiplication, and reusable clean-ancilla linear MCX chains. The abstract arithmetic gate count is polynomial in n and is generated from only public N, the public base, and the standard Shor constants `base^(2^k) mod N`.

No truth-table/full-register permutation is used in this audit.

## Staged stopping model

The stopping rule is kept aligned with the existing Dark Star work:

- start at 4 phase bits;
- increase precision in steps of 2;
- stop at the textbook cap `2*bit_length(N)`;
- use 4 shots per stage by default;
- credit only the nearest ideal QPE bin;
- accept only continued-fraction denominators that satisfy the existing strict public verification criterion.

Validation-only factors and orders are used to generate ideal QPE statistics and verify the scout cases. They are not used to remove rounds or simplify modular arithmetic.

## Cases

The first matrix is deliberately the three already-established classical-shortcut-clean scout cases:

| N | ell | public base | transformed base | validation order |
|---:|---:|---:|---:|---:|
| 209 | 3 | 3 | 27 | 90 -> 30 |
| 713 | 5 | 19 | 563 | 330 -> 66 |
| 781 | 7 | 29 | 380 | 70 -> 10 |

Both the baseline and transformed base must pass the same public repeated-squaring/GCD classical-shortcut guardrail before counting as quantum-relevant.

## Four-way comparison

Each case reports:

- standard wide staged QPE;
- standard recycled staged QPE;
- Dark-Star-transformed wide staged QPE;
- Dark-Star-transformed recycled staged QPE.

Primary metrics:

- peak simultaneous logical qubits;
- expected phase-round executions per attempted staged session;
- expected arithmetic CCX/Toffoli count;
- expected controlled-SWAP count;
- success probability by the textbook precision cap.

Architecture-specific overhead is recorded separately:

- wide inverse-QFT controlled phases and swaps;
- recycled mid-circuit measurements, resets, and classically conditioned phase corrections.

## Preregistered interpretation

A positive result requires the transformed policy to reduce expected arithmetic work under this polynomial resource model, not merely under the old truth-table compiler.

The most important diagnostic is:

`per_phase_round_ccx_ratio_dark_star_over_baseline`.

If this value is close to one while total expected CCX falls materially, then the robust mechanism is **earlier stopping**, not a lucky cheaper set of transformed modular constants.

This matters because earlier N=713/N=781 IBM-target truth-table compilations showed same-precision transformed circuits that happened to compile somewhat cheaper. That secondary compiler effect must not be assumed to generalize.

Phase recycling and Dark Star should also remain conceptually separate:

- recycling reduces simultaneous phase-register width;
- Dark Star changes expected sequential order-finding work;
- neither mechanism removes the coherent modular-arithmetic register;
- the Dark Star transform does not lower the fixed textbook precision cap.

## Claim boundary

This experiment may support a more general **resource** statement because the arithmetic model grows polynomially with modulus width. It still does not establish:

- a measured QPU runtime or fidelity improvement;
- a fault-tolerant physical-qubit estimate;
- a practical RSA-2048 attack;
- an asymptotic improvement to Shor's algorithm;
- novelty of the elementary identity `ord(a^ell)=ord(a)/gcd(ord(a),ell)`.

No QPU service is contacted.
