# Reversible divisibility oracle without classical answer preparation

This replaces the previous compiled divisibility truth table with a generic
gate-level reversible restoring divider. It does not precompute candidate
factors or compile a phase flip for each known successful candidate.

The gate compiler `build(nbits,pbits)` receives only register widths. The same
oracle supports every N of that width and even coherent superpositions of N.
N is loaded into a quantum input register using X gates. No factors, remainders,
or solution counts are inputs to the compiler.

## Quantum calculation

1. Prepare the P candidate register in a uniform superposition.
2. Divide the quantum N register by P using reversible restoring division.
3. Compute validity P>=2 and Q>=2; Q is the computed quotient.
4. Flip phase exactly when validity holds and the remainder R is zero.
5. Reverse all arithmetic, clearing quotient, remainder, history and flags.
6. Apply Grover diffusion on P. Repeat as explicitly requested.
7. Compute division and the success flag once more for readout; measure P,Q.

Both factors are read from quantum registers. There is no classical N/p step
to produce the second factor. Classical multiplication verifies the measured
answer, as is normal when validating a search result. Candidate 0, candidate 1
and trivial partners 0 or 1 are excluded coherently by the validity flags.
Division by candidate 0 has no mathematical quotient guarantee but is a
well-defined reversible gate sequence and is always excluded by P>=2.

Division is built from explicit X, CX and CCX gates. The full experiment also
uses H and Z. Comparators compute subtraction borrows into scratch; the divider
keeps history to preserve reversibility. Multi-controlled operations are
decomposed into CCX chains with clean scratch, rather than treated as free
opaque operations. The implementation retains substantial history and is NOT
resource optimized.

## Run

Python 3.10+ and NumPy are required; no QPU account or quantum SDK is needed.

```bash
python -m pip install numpy
python reversible_division.py --selftest
python reversible_division.py --N 35 --candidate-qubits 3 --iterations 1 --qasm circuit.qasm
python reversible_division.py --N 323 --candidate-qubits 5 --iterations 3
```

`--output result.json` saves results. The OpenQASM 2 export includes complete
input preparation, all Grover rounds and division readout. Register comments
identify little-endian bit indices; bit strings from a backend typically print
the highest-index classical bit first. Hardware execution and SDK import of
the exported files were not performed in this session.

## Measured ideal simulation results

| N | Candidate qubits | Total qubits including workspace | Grover rounds | Exact ideal success | Accepted shots |
|---|---:|---:|---:|---:|---:|
| 35 | 3 | 74 | 1 | 100% to numerical precision | 2000/2000 |
| 323 | 5 | 146 | 3 | 96.13189697% | 1933/2000 |

For 35 the outcomes were (5,7) 1034 times and (7,5) 966 times.
For 323 they were (17,19) 999 times and (19,17) 934 times.
Failed trials are retained in the totals. The iteration counts are fixed
diagnostic choices, not an adaptive unknown-solution-count algorithm.

| Cost per phase oracle | N=35 | N=323 |
|---|---:|---:|
| X | 348 | 742 |
| CX | 348 | 810 |
| CCX / Toffoli | 370 | 926 |
| Z | 1 | 1 |
| Total | 1067 | 2479 |

These counts exclude initial state preparation, Grover diffusion and final
division/readout. Toffoli is a logical gate, not generally one native hardware
instruction. Complete gate lists are available through --qasm.

## Validation

480 exhaustive N/P cases (N=4..63, P=0..7) independently verified:

- Exact quotient and remainder for nonzero P.
- Nontrivial-factor validity flag, including exclusion of P=0 and P=1.
- Exact oracle phase sign and preservation of input registers.
- Division followed by its inverse restores every workspace bit.

Seven end-to-end Grover runs checked amplification and scratch cleanup,
including prime inputs, even inputs and larger candidate registers. A test
with N itself in coherent superposition checked that one fixed compiled oracle
acts correctly across different target numbers. Python // and % appear only
in independent selftests; they are not used in building or running the oracle.
See selftest.json and example JSON files.

## What changed and what remains

The previous three-qubit demonstration needed a classical truth table that
already identified factors. This version removes that shortcut. It retains
three candidate qubits for the 35 example, but needs 74 total qubits for this
straightforward reversible arithmetic construction. This is a correctness
prototype; fewer-workspace arithmetic is a separate optimization task.

The exact simulator stores a sparse dictionary of occupied computational basis
states and applies every gate. These arithmetic experiments occupy few states,
so simulation is inexpensive despite the large logical qubit count. It is not
an unrestricted 74- or 146-qubit dense simulator, a hardware benchmark, or
evidence of a quantum factoring speedup. Generic noisy states can destroy this
sparsity.

N is supplied as a known input and the program/circuit is generated classically,
as with ordinary quantum algorithms. The removed classical part is the factor
search used to prepare the oracle. Small classical checks in the test harness
validate results; they do not tell the circuit which candidates to mark.

At least one nontrivial divisor must fit P. Candidate capacity is 2**pbits,
including invalid values 0 and 1. Unsuccessful shots do not prove primality.
The CLI caps candidates at eight bits and N at 24 bits to keep this prototype
bounded. The search remains Grover search; no Shor-like scaling is claimed.
