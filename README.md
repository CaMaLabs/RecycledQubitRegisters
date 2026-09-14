# RecycledQubitRegisters

**Experimental Qiskit research toolkit for dynamic phase-register recycling, matched QPE/Shor hardware benchmarks, and calibration-aware qubit placement.**

RecycledQubitRegisters (QRR) asks a narrow systems question: when an algorithm allows measurement and classical feed-forward, can a quantum program reduce **simultaneous coherent width** by measuring temporary quantum state, storing the result classically, resetting the physical qubit, and reusing it later?

The project uses Qiskit dynamic circuits to compare conventional wide phase registers with iterative/semiclassical constructions that recycle one phase ancilla. The work includes exact simulation checks, matched same-job IBM hardware controls, explicit random-output baselines, negative/null results, and backend-specific placement experiments.

> **Status:** experimental research software. The strongest results are compiled-orbit hardware benchmarks, not a scalable general-purpose Shor implementation and not a practical cryptographic attack.

## Why this is a Qiskit project

QRR builds directly on Qiskit and Qiskit IBM Runtime:

- circuit construction with Qiskit;
- dynamic circuits with mid-circuit measurement, reset, and classical feed-forward;
- backend-aware transpilation and explicit physical layouts;
- IBM hardware execution through `SamplerV2`;
- calibration-aware placement searches over connected physical regions;
- exact and hardware-level comparisons between wide and recycled phase-estimation architectures.

Tested dependency line:

```text
qiskit ~= 2.5.2
qiskit-ibm-runtime ~= 0.47.0
```

The project is licensed under **Apache-2.0** and follows the **Qiskit Code of Conduct**.

## Key hardware result: compiled `N=35`, `a=2`, `r=12`

The main benchmark uses a compiled Shor order-finding instance for

```text
N = 35
a = 2
order r = 12
```

The twelve-state modular orbit is represented exactly in a four-qubit coherent work register using an affine basis encoding. The phase register is implemented in two ways:

- **wide:** eight simultaneous phase qubits + four work qubits = 12 logical qubits;
- **recycled:** one repeatedly measured/reset phase ancilla + four work qubits = 5 logical qubits.

This is a **compiled orbit encoding** specific to the tested instance. It is not a generic reversible modular multiplier.

### IBM Fez

On the first eight-bit matched Fez run:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| CZ gates | 331 | **175** |
| Depth | 788 | **607** |
| Permissive factor recovery | 12.50% | **40.23%** |
| Strict direct-order recovery | 2.34% | **5.86%** |
| Hellinger fidelity to ideal | 0.1951 | **0.5236** |
| TV distance to ideal | 0.8448 | **0.5723** |

The exact eight-bit uniform-output references are 12.890625% permissive recovery and 2.34375% strict direct-order recovery. Recycled produced 30 strict successes in 512 shots where the uniform model predicts 12 in expectation. The fixed-baseline binomial tail quoted in the project is a **shot-noise-only** calculation; it does not model calibration drift or correlated hardware errors.

A clean unmodified Fez repeat strengthened recycled strict recovery to **36/512 = 7.03%**. A later zero-QPU placement search reduced the recycled circuit to **160 CZ / depth 572** and preserved the 36/512 strict rate while improving the broader measured distribution.

See:

- [`results/hardware/SHOR35_AFFINE_HARDWARE.md`](results/hardware/SHOR35_AFFINE_HARDWARE.md)
- [`results/hardware/SHOR35_OPTIMIZED_HARDWARE.md`](results/hardware/SHOR35_OPTIMIZED_HARDWARE.md)
- [`docs/QRR_SHOR35_PREPRINT_DRAFT.md`](docs/QRR_SHOR35_PREPRINT_DRAFT.md)

### IBM Marrakesh cross-backend control

Marrakesh behaved differently, which is an important part of the result rather than something hidden from the record.

Two unoptimized Marrakesh runs preserved a broad recycled advantage but failed to reproduce strict order recovery above the uniform floor. A backend-specific zero-QPU placement search then found a cleaner physical region. The decisive control submitted **four circuits in one QPU job**:

1. legacy recycled,
2. legacy wide,
3. optimized recycled,
4. optimized wide.

Same-job results:

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 22.27% | 1.37% | 0.2606 | 0.7755 |
| Legacy wide | 13.48% | 1.37% | 0.1897 | 0.8441 |
| Optimized recycled | **33.98%** | 3.71% | 0.3908 | **0.6281** |
| Optimized wide | 32.03% | **6.25%** | **0.4688** | 0.6438 |

This control supports a strong **architecture × placement × backend** interaction. On Marrakesh, placement materially improved both architectures; after optimization, wide was stronger on the strict-order metric even though recycled still used far fewer simultaneous logical qubits and CZ gates.

The project therefore does **not** claim that recycling is universally superior. The narrower conclusion is that coherent width is an experimental resource whose cost interacts strongly with topology, calibration quality, routing, measurement, and feed-forward overhead.

See [`results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md`](results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md).

## Earlier QPE and Shor benchmarks

QRR also includes:

- exact simulator checks showing iterative/recycled QPE reproduces the ideal wide-QPE distribution;
- matched hardware QPE phase-width scaling on IBM Fez;
- `N=15` same-job Shor comparisons where recycled phase width scaled more favorably than the wide phase register;
- replicated compiled `N=21`, `a=2`, `r=6` hardware tests;
- failed and noise-floor `N=35` implementations retained for provenance;
- exact toy gate-level modular-permutation synthesis and statevector validation;
- random-entanglement stress tests showing that narrow recycled working sets do **not** replace arbitrary wide coherent entanglement.

## What this project does not claim

QRR does not claim that a few physical qubits can emulate an arbitrary large coherent register. Classical memory can store **measurement outcomes**, not arbitrary unmeasured quantum state.

In a Shor-style decomposition, iterative QPE can recycle the phase/control register, but the coherent modular-arithmetic work register and its ancillas are still required. The current `N=21` and `N=35` hardware experiments use compiled orbit encodings to keep depth feasible on present devices.

This repository therefore makes no claim of:

- a scalable general Shor implementation;
- factoring large RSA keys on current hardware;
- a universal advantage of recycled over wide circuits;
- asymptotic speedup caused by recycling itself.

Iterative/semiclassical QPE is established prior art. The research contribution explored here is **architecture/compiler/hardware co-design**: when to retain coherence, when to measure and recycle, and how to place the remaining coherent workload on real hardware.

## Quick start

Do **not** place an IBM API key in this repository or shell history.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The repository also includes an isolated IBM Open Plan setup helper:

```bash
chmod +x hardware/setup_open_plan.sh
./hardware/setup_open_plan.sh
source ~/ibm-6c2q-venv/bin/activate
python hardware/save_open_plan_account.py
python hardware/preflight_open_plan.py
```

A small dynamic-circuit probe can be run before larger jobs:

```bash
python hardware/ibm_6c2q_hardware_test.py \
  --probe \
  --shots 128 \
  --max-execution-time 30
```

## Representative experiments

Matched compiled `N=35` baseline:

```bash
python hardware/ibm_shor35_affine_matched.py \
  --backend ibm_fez \
  --phase-bits 8 \
  --shots 512 \
  --optimization-level 3 \
  --max-execution-time 120
```

Zero-QPU placement search:

```bash
python hardware/ibm_shor35_layout_optimizer.py \
  --backend ibm_fez \
  --phase-bits 8 \
  --optimization-level 3 \
  --candidate-plans 12 \
  --ancilla-pool 32 \
  --seeds 8776,20260914,314159 \
  --top 8
```

Uniform-noise / strict-order audit of a saved result:

```bash
python hardware/analyze_shor_noise_floor.py path/to/result.json
```

Simulation suite:

```bash
python simulation/hybrid_6c2q_experiment.py
python simulation/hybrid_register_isa_experiment.py
python simulation/rsa_shor_end_to_end.py
python simulation/rsa_shor_statevector.py --bits 8 9 --trials 10 --shots-per-base 8 --max-bases 8
python simulation/rsa_gate_level_modmul.py --bits 6 7 8 9 --trials 5 --seed 8776 --outdir results/rsa_gate_level
```

## Repository map

```text
hardware/
  IBM/Qiskit dynamic-circuit probes
  wide-vs-recycled Shor/QPE runners
  N=35 affine encoding
  calibration-aware layout optimizer
  frozen-plan runner
  same-job layout A/B runner
  uniform-noise and strict-order analyzer

simulation/
  exact QPE / hybrid-register experiments
  toy RSA/Shor simulations
  explicit statevector validation
  exact gate-level modular-permutation synthesis

results/
  hardware summaries and raw-result-derived tables
  simulation results
  negative/null experiments retained for provenance

docs/
  architecture notes
  preprint draft
  novelty audit
  Qiskit Ecosystem submission draft
```

## Reproducibility

Hardware results depend on calibration, physical-qubit placement, routing, backend state, and Qiskit/runtime versions. Principal comparisons therefore use matched same-job execution wherever possible, preserve shared initial work-register placement within each compared pair, and report uniform-output baselines alongside algorithmic metrics.

The transpiler may move logical state away from requested initial sites during execution; "same work register" refers to the enforced initial physical placement, not permanent pinning.

Raw credentials and account identifiers are intentionally excluded from the repository.

## Research record

Useful starting points:

- [`docs/QRR_SHOR35_PREPRINT_DRAFT.md`](docs/QRR_SHOR35_PREPRINT_DRAFT.md) — formal preprint draft
- [`docs/N35_NOVELTY_AUDIT_2026-09-14.md`](docs/N35_NOVELTY_AUDIT_2026-09-14.md) — novelty/priority boundary
- [`results/hardware/SHOR35_AFFINE_HARDWARE.md`](results/hardware/SHOR35_AFFINE_HARDWARE.md) — Fez affine hardware record
- [`results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md`](results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md) — unoptimized cross-backend controls
- [`results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md`](results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md) — optimized Marrakesh runs
- [`results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md`](results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md) — same-job layout control
- [`docs/QISKIT_ECOSYSTEM_SUBMISSION.md`](docs/QISKIT_ECOSYSTEM_SUBMISSION.md) — prepared Ecosystem form text

## Citation and license

Citation metadata is available in [`CITATION.cff`](CITATION.cff).

Licensed under the [Apache License 2.0](LICENSE).
