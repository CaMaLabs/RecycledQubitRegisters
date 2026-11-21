# Optimized reversible divisor oracle

The classical factor lookup remains removed. The compiler uses only register
widths, accepts N in a quantum input register, and computes quotient/remainder
with generic reversible gates. Final measurement reads both factors from P,Q.

## Optimization

The original divider retained separate difference and borrow registers at every
long-division stage. The optimized divider subtracts P from R in place using
MAJ/UMA ripple arithmetic, records the underflow branch in the quotient bit,
and conditionally restores P. A shared masked-addend/carry workspace is cleaned
after every stage and reused by arithmetic, validity checks and phase marking.
The quotient bits retain the reversible branch information, so the large
per-stage history registers are unnecessary.

The first adder stage is specialized to its known zero incoming carry. The
upper addend bit is known zero and its unnecessary MAJ/UMA pair is omitted.
Borrow is stored directly during restoration, then complemented once to become
the quotient bit, eliminating redundant negative-control X gates.

The underlying MAJ/UMA arithmetic follows the Cuccaro ripple-carry approach:
https://arxiv.org/abs/quant-ph/0410184.
Our divider, shared-workspace arrangement and counted circuits are this
implementation; the paper does not substantiate our measured resource counts.

## Measured logical resource comparison

Counts below are per phase-oracle invocation, excluding preparation, diffusion
and final division/readout. Toffoli is CCX, not a native-device instruction.

| Metric | N=35 before | N=35 after | N=323 before | N=323 after |
|---|---:|---:|---:|---:|
| Total logical qubits | 74 | 26 | 146 | 38 |
| Toffoli gates | 370 | 250 | 926 | 602 |
| CNOT gates | 348 | 372 | 810 | 954 |
| X gates | 348 | 60 | 742 | 94 |
| All gates | 1067 | 683 | 2479 | 1651 |
| Logical gate depth | 480 | 464 | 1042 | 1066 |
| Toffoli-weighted dependency depth | 240 | 200 | 582 | 456 |

Qubit reductions are 64.9% and 74.0%; Toffoli reductions are 32.4% and 35.0%.
CNOT counts increase 6.9% and 17.8%. The 323 configuration's logical depth
increases 2.3%, despite lower Toffoli dependency depth and fewer total gates.
This is a workspace/Toffoli improvement, not a win on every cost metric.

Depth is a conservative all-to-all schedule in which gates sharing a wire
are ordered. Toffoli-weighted dependency depth assigns cost one to CCX and zero
to other gates while retaining wire dependencies. Neither is a measured pulse
time, fault-tolerant reaction depth or hardware routing result.

For 20-bit N=1040399 and ten candidate bits, circuit compilation/counting gives
521 -> 81 logical qubits and 4066 -> 2546 Toffoli gates. That configuration was
NOT run through the complete factor-search simulation. Its depth increases
4106 -> 4370 and CNOT count increases 3400 -> 4320. The default experiment CLI
still caps candidates at eight bits to bound simulation work.

## Readout and postselection

There are no intermediate measurements or discarded branches. The oracle
computes division, marks the valid zero-remainder branch with a phase, then
reverses the arithmetic. Grover diffusion follows. At final readout division
and a success flag are computed again; only successful measured shots are
reported as factor pairs. Failed shots are included in the total.

| Input | Candidate bits | Grover rounds | Exact ideal success | Accepted shots |
|---|---:|---:|---:|---:|
| 35 | 3 | 1 | 100% to floating precision | 2000/2000 |
| 323 | 5 | 3 | 96.13189697% | 1933/2000 |

These probabilities and seeded shot outcomes match the original circuit.
The optimization changes arithmetic resources, not Grover's search scaling or
the number of solutions. Iteration counts are fixed diagnostic choices, not
an adaptive unknown-solution schedule.

## Why the arithmetic is valid

For P>=1 the restoring-division invariant is 0<=R<P at each stage boundary.
After shifting and appending the next N bit, 0<=R<2P. Because P fits m bits,
R fits m+1. Subtracting P modulo 2**(m+1) gives a high bit of one exactly on
underflow: a negative difference lies in the upper half of that register, while
a nonnegative difference is less than P and has high bit zero. Retain that
underflow in Q, add back P conditionally, then complement Q to encode the
division decision. The masked addend and carry are cleaned using the preserved
decision. Reversing the complete divider clears all quotient and work bits.

P=0 has a unitary gate-defined action but no quotient interpretation; it is
excluded by the coherently computed P>=2 flag. P=1 and trivial quotient values
are also excluded. The phase oracle is unchanged for all clean-workspace
candidate inputs. No claim is made that the different-size full unitaries have
identical behavior on arbitrary dirty ancillas.

## Validation completed

- 680 exhaustive padded-adder input pairs, including inverse and carry cleanup.
- 480 exhaustive N/P cases, with N=4..63 and P=0..7, checked against independent
  quotient/remainder arithmetic and the previous phase oracle.
- 125 basis terms across coherent superpositions of different N and P values
  with random complex amplitudes; exact phase, quotient, remainder and cleanup.
- Seven end-to-end Grover comparisons, including prime/even inputs, checked
  success curves and seeded measured pairs against the baseline.

All passed. Python division/modulo operations are used only in independent
tests; the oracle compiler and factor-search circuit do not use a factor table.

## Run

Requires Python 3.10+ and NumPy.

```bash
python -m pip install numpy
python optimized_division.py --selftest
python optimized_division.py --N 35 --candidate-qubits 3 --iterations 1 --qasm circuit.qasm
python optimized_division.py --N 323 --candidate-qubits 5 --iterations 3
python benchmark.py
```

baseline.py retains the original arithmetic. Its run function has only an
optional builder-injection parameter added so identical measurement code can
test both architectures. optimized_division.py uses the same exact sparse gate
simulator and output conventions. OpenQASM export contains the complete gates
and little-endian register comments. These circuits were not run on a QPU or
cross-validated with a separate SDK in this session.

The simulator follows sparse reachable states, not the unrestricted dense
Hilbert space of all allocated qubits. Noise/leakage and physical gate costs
are not modeled. Both variants are correctness prototypes; no globally minimal
qubit count, hardware speedup, error-correction advantage, or factoring
breakthrough is claimed. A nontrivial divisor must fit P, and unsuccessful
shots do not prove primality.
