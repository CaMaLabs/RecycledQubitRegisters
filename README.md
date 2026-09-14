# RecycledQubitRegisters

Experimental hybrid quantum/classical register architecture for **reusing a small physical-qubit working set across a larger logical computation**.

The project started from a simple question: instead of keeping every logical register position quantum at once, can hardware keep most state classical and recycle one or two high-value quantum positions whenever coherence is actually required?

The first concrete benchmark is quantum phase estimation (QPE), where a conventional phase register can be compared directly with an iterative implementation using a recycled ancilla, mid-circuit measurement, reset, and classical feed-forward.

## Current hardware result

On IBM `ibm_fez`, using a shared physical-qubit neighborhood and an exact six-bit phase `0.328125 = 21/64 = 0.010101`:

| Metric | Conventional wide QPE | Recycled iterative QPE |
|---|---:|---:|
| Target success | 41.80% | **81.25%** |
| Logical qubits | 7 | **2** |
| Compiled depth | 276 | **103** |
| CZ gates | 105 | **12** |

Across a separate 4-bit three-phase sweep, the recycled implementation reached 88.28-91.80% target success versus 69.53-74.22% for the conventional wide implementation. At 7 phase bits on target `0101011`, recycled QPE reached **83.20%** versus **39.06%** wide, using 2 versus 8 logical qubits.

See [`results/hardware/RESULTS.md`](results/hardware/RESULTS.md) and [`results/hardware/hardware_summary.csv`](results/hardware/hardware_summary.csv).

## End-to-end simulated RSA/Shor result

The repo now includes two self-generated toy-RSA benchmarks:

- `simulation/rsa_shor_end_to_end.py`: strict end-to-end functional Shor simulation from `N` only through QPE samples, continued fractions, factor recovery, private-key reconstruction, and ciphertext decryption.
- `simulation/rsa_shor_statevector.py`: explicit toy-size modular-work-register statevector validation using the reversible permutation `|y> -> |a*y mod N>` and a real measure/reset/feed-forward recycled phase ancilla.

Sanity check: with one coprime base and one QPE shot, the compact simulator succeeded on **26.0% of 200 fresh 16-bit keys** and **27.5% of 200 fresh 20-bit keys**. With four shots per base and up to four bases, success rose to **97% at 16 bits** and **100% at 20 bits**, with no lucky `gcd(a,N)` shortcuts counted.

In the explicit statevector validation, the balanced 8-bit case `N=143=11x13` passed **30/30** wide and recycled trajectories at **24 vs 9 logical qubits**. A separate 9-bit varied-modulus run (`299`, `319`, `341`, `377`, `403`) passed **10/10** for both architectures at **27 vs 10 logical qubits**; a literal dense 27-qubit complex128 statevector would occupy 2 GiB.

See [`results/rsa_shor/RESULTS.md`](results/rsa_shor/RESULTS.md).

## What this does *not* claim

This is not a claim that two physical qubits emulate an arbitrary large coherent register. It also is not a claim that Shor factorization requires only two total qubits. In a Shor-style decomposition, iterative QPE can recycle the **phase/control register**, while the modular-arithmetic work register and ancillas are still required.

Iterative/semiclassical QPE is an established technique. The research focus here is the **architecture and scheduling problem**: deciding when to preserve coherence, when to measure and move information into classical storage, when to reset/recycle a physical qubit, and which backend/physical qubits make that trade favorable.

## Repository layout

```text
hardware/
  ibm_6c2q_hardware_test.py   IBM hardware probe + wide/recycled QPE comparison
  preflight_open_plan.py      zero-QPU-cost backend/account check
  save_open_plan_account.py   credential setup using hidden token entry
  setup_open_plan.sh          isolated Python 3.13 + uv environment setup

simulation/
  hybrid_6c2q_experiment.py
  hybrid_register_isa_experiment.py
  rsa_shor_end_to_end.py      compact end-to-end toy RSA/Shor benchmark
  rsa_shor_statevector.py     explicit modular-work-register validation

results/
  hardware/                   summarized real-QPU results
  rsa_shor/                   simulated RSA/Shor results
  simulation/                 simulation/ISA CSV outputs

docs/
  ARCHITECTURE.md

integrations/darkstar_hybrid/
  self-generated-semiprime preprocessing + hybrid-QPE integration experiments
```

## IBM Open Plan setup

Do **not** put an IBM API key in this repository or in shell history.

```bash
chmod +x hardware/setup_open_plan.sh
./hardware/setup_open_plan.sh
source ~/ibm-6c2q-venv/bin/activate
python hardware/save_open_plan_account.py
python hardware/preflight_open_plan.py
```

The setup script uses an isolated Python 3.13 environment because the tested Qiskit stack is not intended to depend on the system Python installation.

Run the tiny feedback probe first:

```bash
python hardware/ibm_6c2q_hardware_test.py \
  --probe \
  --shots 128 \
  --max-execution-time 30
```

Shared-layout comparison example:

```bash
python hardware/ibm_6c2q_hardware_test.py \
  --run \
  --backend ibm_fez \
  --shared-layout \
  --bits 6 \
  --phase 0.328125 \
  --shots 256 \
  --max-execution-time 45
```

The hardware runner records the selected physical region, `measure_2` calibration, CZ calibration, compiled depth/gate counts, shot distributions, job metadata, and account usage before/after the run.

## Simulation

```bash
python -m pip install -r requirements.txt
python simulation/hybrid_6c2q_experiment.py
python simulation/hybrid_register_isa_experiment.py
python simulation/rsa_shor_end_to_end.py
python simulation/rsa_shor_statevector.py --bits 8 9 --trials 10 --shots-per-base 8 --max-bases 8
```

The ISA experiment tests exact iterative-QPE semantics, normalized feedback-latency tradeoffs, batch throughput, random entanglement stress, and a learned resource router.

## Early simulation findings

- Recycled QPE reproduced the ideal wide-QPE probability distribution to floating-point precision in the exact simulator.
- Under the normalized latency model, local feedback becomes competitive with wide QPE as phase precision grows; host round-trip feedback is much more expensive.
- Random-circuit entanglement stress shows the key limit: narrow recycled quantum working sets do **not** substitute for arbitrary wide entanglement.
- A learned resource router reached about 89% exact resource-class accuracy on a held-out synthetic circuit set in the initial experiment.
- End-to-end self-generated RSA/Shor simulation now reaches factor recovery and ciphertext decryption without supplying hidden factors to the factoring routine.

## Dark Star integration

`integrations/darkstar_hybrid/` contains the clean research integration used to explore whether classical periodic-prime-space preprocessing can feed a heterogeneous classical/quantum router. It uses self-generated semiprimes for benchmarking. The classical wheel/residue preprocessing should not be interpreted as a general RSA break; its clearest measured benefit is close-factor/Fermat midpoint pruning, while the order/lambda diagnostics remain exploratory.

## Reproducibility notes

Hardware results depend on backend calibration, routing, queue state, Qiskit version, and physical-qubit selection. An early run on `ibm_kingston` performed poorly while the same iterative circuit on `ibm_fez` performed well, motivating the shared-layout and calibration-aware comparison now used by the runner.

The compact RSA/Shor simulator classically computes the modular-multiplication order internally only to sample exact ideal QPE statistics efficiently; the factoring/post-processing path receives only `N` and measurement samples. The explicit statevector benchmark is the stronger toy-size check that evolves the modular work register directly. Neither benchmark models a full fault-tolerant reversible modular multiplier at realistic RSA sizes.

Raw account identifiers and credentials are intentionally not committed. Public result files contain only non-secret benchmark measurements.
