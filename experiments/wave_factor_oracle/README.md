# Wave-inspired factor oracle: qudit encodings and Qiskit execution

This directory preserves the complete progression from ideal optical-style
constraint filtering to a generic reversible divisor oracle. The current
recommended entry point is `qiskit_runner.py`, using the optimized arithmetic
in `optimized_divisor_oracle/`.

This belongs in RecycledQubitRegisters because it studies reversible arithmetic,
clean workspace reuse, qudit register encodings and matched Qiskit checks.
It is separate from the repository's Shor order-finding hardware benchmarks.
These experiments use Grover-style divisor search, not Shor's algorithm.

## Published-design comparison

The [matched comparison](comparison/REPORT.md) now includes an executable
COMP-N-SUB-I component from arXiv:2603.18110v2 inside our existing wrapper.
It outperforms our optimized arithmetic: 166 vs 250 Toffolis per oracle for 35,
and 368 vs 602 for 323, at identical logical width. This is a compatible
component comparison, not a reproduction of the paper's full divider.

The runner supports `--architecture published-cns` (default remains `qrr`).
For 323, two rounds minimize expected Toffoli cost over the tested sweep;
filter-only postselection remains valid but rejects most preparations. Full
results, assumptions and tests are linked in the report.

## Run locally with Qiskit

From the repository root:

```bash
python -m venv .venv-wave
source .venv-wave/bin/activate
python -m pip install -r experiments/wave_factor_oracle/requirements-qiskit.txt
python experiments/wave_factor_oracle/qiskit_runner.py \
  --N 35 --candidate-qubits 3 --iterations 1 --shots 2000 \
  --output experiments/wave_factor_oracle/results/local_35.json
python experiments/wave_factor_oracle/qiskit_runner.py \
  --N 323 --candidate-qubits 5 --iterations 3 --shots 2000
```

Tested with Python 3.12, Qiskit 2.6.2 and Qiskit Aer 0.18.4. This runner uses
local Aer matrix-product-state simulation with no chosen bond-dimension cap and
zero configured truncation threshold. Numerical floating-point error still
exists. These low-superposition arithmetic circuits are suitable for MPS;
that does not imply efficient simulation of arbitrary 38-qubit states.

No IBM credentials, paid services or QPU jobs are used. The runner does not
submit hardware jobs. The `--qasm circuit.qasm` option exports a circuit without
the Aer-only diagnostic snapshots; OpenQASM import/execution is tested.

## Actual Aer results

| Target | Logical qubits including work | Rounds | Accepted shots | Aer ideal success | Error vs independent sparse engine |
|---|---:|---:|---:|---:|---:|
| 35 = 5 x 7 | 26 | 1 | 2000/2000 | 100% within floating precision | 1.11e-14 |
| 323 = 17 x 19 | 38 | 3 | 1930/2000 | 96.13189696% | 1.34e-10 |

See `results/qiskit_35.json` and `results/qiskit_323.json` for full versions,
counts, timing, transpiled resources and numerical checks. Both passed the
mean-Z workspace-cleanup check before final division/readout. The saved
probability for 35 is slightly above one by floating-point roundoff; no
probability greater than one is physically asserted.

The compiler takes only register widths. N is prepared in a quantum register;
the circuit computes quotient and remainder using X/CX/CCX arithmetic, marks
P>=2, Q>=2, R=0, then reverses the calculation. It does not classically enumerate
successful candidates to construct the oracle. Both factors are measured from
the P and Q quantum registers. Classical multiplication checks the measured
answers; it does not supply them to the oracle.

There are no intermediate measurements or postselection. Grover amplification
acts coherently, then final readout retains shots whose good flag is one.
Rejected shots remain in the totals. The Aer expectation/probability saves are
simulator diagnostics, not physical measurements inserted into the circuit.

The current optimization reduces the 35 example from 74 to 26 logical qubits
and 370 to 250 Toffolis per oracle, and 323 from 146 to 38 qubits and 926 to 602
Toffolis. CNOT counts increase and the 323 oracle's logical depth increases
slightly. Oracle-only counts differ from full-circuit counts and transpiled
counts; all are explicitly labeled. No hardware advantage or efficient
cryptographic factoring is claimed. Iteration counts here are fixed diagnostic
choices, not an adaptive unknown-solution-count procedure.

## Source and result inventory

| Folder/file | Contents and status |
|---|---|
| `qiskit_runner.py` | Current local Aer runner, generic optimized oracle |
| `test_qiskit_runner.py` | Independent SDK checks, including QASM round trip |
| `optimized_divisor_oracle/` | Current in-place divider, original baseline, resource comparisons, exhaustive tests and QASM |
| `reversible_divisor_oracle/` | Earlier history-preserving generic divider, retained for comparison |
| `three_qubit_qudit/` | Exactly three qubits emulate one eight-level qudit; compiled truth-table demonstration only |
| `expanded_qudit_registers/` | Additional levels expand factor/product registers; structured simulator and data |
| `qudit_constraint_solver/` | Original dense pair-search model, limit tests, stress scripts and results |
| `results/` | Current independently executed Qiskit Aer results and exports |

The latest scripts, JSON results, documentation, dependency files and QASM
exports from all five earlier experiment families are preserved here, including
the dense solver's limit-test extensions. Zip
archives and generated Python caches are omitted. Historical READMEs describe
the status at their own experiment stage; this overview records the current
Qiskit validation. In particular, the three-qubit truth-table example is not
the current generic oracle and already performed classical divisor checks.

Prior spin-qudit source remains on branch `experiment/a115-spin-qudit-arithmetic`
under `hardware/a115_spin7_2_qudit_arithmetic.py` and
`hardware/a117_multitone_gray_cycle.py`. The expanded-register package records
the exact inspected source blob SHAs and retains its eight-level basis map.
An eight-level spin-7/2 carrier cannot acquire 16/32 levels merely by relabeling;
the larger dimensions remain hypothetical hardware encodings.

## Validation

```bash
python -m unittest discover -s experiments/wave_factor_oracle -p 'test_*.py' -v
python experiments/wave_factor_oracle/optimized_divisor_oracle/optimized_division.py --selftest
```

The original five Aer tests cover unamplified and amplified probabilities, the 38-qubit
divider, prime/no-solution behavior and QASM import/execution. Arithmetic tests
include 680 adder cases, 480 divider/baseline cases, random coherent target and
candidate superpositions, and seven end-to-end Grover comparisons.
Additional comparison tests cover the published primitive, full adapter,
coherent target superpositions and filter-only acceptance accounting.

The path-scoped GitHub Actions workflow runs these tests and all earlier small
selftests. The explicit dense stress scripts remain opt-in because they need
more memory. No action invokes IBM Runtime or submits QPU jobs.

References:

- Cuccaro MAJ/UMA arithmetic: https://arxiv.org/abs/quant-ph/0410184
- Aer MPS simulator: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html

Research lead: Chase Lunsford / CaMaLabs. Repository Apache-2.0 license applies.
