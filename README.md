# RecycledQubitRegisters

[![Qiskit Ecosystem](https://qisk.it/e-68e87191)](https://qisk.it/e)

**Experimental Qiskit research toolkit for dynamic phase-register recycling, matched QPE/Shor hardware benchmarks, and calibration-aware qubit placement.**

> **Qiskit Ecosystem member:** RecycledQubitRegisters was accepted into the [Qiskit Ecosystem](https://qisk.it/e) through [Qiskit/ecosystem#1375](https://github.com/Qiskit/ecosystem/pull/1375). Ecosystem membership recognizes project/community criteria; it is not independent validation of the research claims in this repository.

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
  Qiskit Ecosystem membership/submission record
```

## Reproducibility

Hardware results depend on calibration, physical-qubit placement, routing, backend state, and Qiskit/runtime versions. Principal comparisons therefore use matched same-job execution wherever possible, preserve shared initial work-register placement within each compared pair, and report uniform-output baselines alongside algorithmic metrics.

The transpiler may move logical state away from requested initial sites during execution; "same work register" refers to the enforced initial physical placement, not permanent pinning.

Raw credentials and account identifiers are intentionally excluded from the repository.

## Verified Dark Star public-selector n18 holdout (zero QPU; October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** [Frozen protocol](docs/DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_PREREG.md), [full verified result](docs/DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_RESULT.md), [successful trial (3/3 CI jobs)](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664537058), and [validated receipt-preservation run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38664867576). Complete [ell3](results/dark_star_ptp/dark_star_public_selector_n18_ell3.json), [ell5](results/dark_star_ptp/dark_star_public_selector_n18_ell5.json), [ell7](results/dark_star_ptp/dark_star_public_selector_n18_ell7.json) JSON receipts are committed. New public-SHA256-selected sample: **120 18-bit semiprimes**, public conditional odd-power vs unchanged-base selector, explicit public continued-fraction factor extraction and bounded classical Pollard p−1 stage1 B31. **85/120 (70.83%)** were factored *classically* before any modeled quantum computation; only **35/120** are classically unresolved. On eligible model-factor-producing trigger cases, public selector vs unchanged base had conditional modeled CCX-per-success ratios **ell3=0.7693 (7 improved/1 worse; PASS)**, **ell5=0.7907 (4 improved/3 worse; fragile PASS)**, **ell7=1.0295 (0 improved/1 worse; FAIL)**. Remaining jointly success-positive cohorts were only **8, 7, 1** keys. The ell5 result is on a **different population/metric** from the earlier [failed ell5 trigger enrichment](docs/DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md) and does not erase that failure. Control selector intentionally leaves the base unchanged and cannot prove lack of benefit from transforming control residues. Separately, recycled phase estimation reduces the generic logical peak from **93 to 58 qubits** (37.63%) under this n18 arithmetic construction, independent of Dark Star. These are ideal nearest-bin-QPE **logical resource estimates**, not a QPU hardware speedup, classical-plus-quantum time/energy estimate, or RSA-scale factoring capability.

## Verified public multichoice classical-survivor holdout (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** [Preregistered protocol](docs/DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_PREREG.md), [complete verified result](docs/DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_RESULT.md), [four-job successful original CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667303027), and [successful independent receipt-preservation CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667614971). Deterministically screened **200** fresh 18-bit synthetic semiprimes using only public gcd/power-two/GCD and Pollard p−1 B31: **160 were already classically factored** and 40 distinct public-classically-unresolved N were modeled (10 for each replication/locked holdout × public N%3 trigger/control cohort). Stronger B47 classical audit can factor **4 more**. Of 40, only **27** had jointly positive factor-producing ideal nearest-bin-QPE success for compared policies. On locked trigger, public multi-exponent ladder/plain conditional modeled logical CCX per factor-producing success ratio **0.7764 (8 improve, 1 worsen)**; on replication trigger ratio **0.7708 (5 improve, 0 worsen)**. **Crucially ladder = always3 on all trigger keys**, so the study finds **NO additional multi-exponent selector advantage** over the simple unconditional cubic transform; the **locked control fails** the preregistered majority-benefit criterion (3 improve/4 worsen) despite weighted ratio <1. A public four-bit gate-cost selector picked unchanged base in 39/40 cases and had no meaningful predictive benefit. All outcomes, failed controls and 40 complete survivor + 160 screened classical records are preserved. Phase-register reuse separately changes this model's 18-bit logical peak **93→58**, independent of transformation. **No QPU measurement, fault-tolerant physical resource claim, proven practical factoring speedup or RSA-scale break.**

## Verified complete ideal-QPE measurement-outcome study (October 2026)

**Research direction: Chase Lunsford / CaMaLabs.** [Prerecorded independent protocol](docs/DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_PREREG.md), [verified result and important limits](docs/DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_RESULT.md), [successful corrected 4/4-job CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669467890), [independently validated original JSON receipts](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669565271). We computed **all** possible ideal-QPE phase-register measurement outcomes through a 20-bit textbook cap using the exact FFT eigenphase-mixture autocorrelation, with public factor-producing continued-fraction/GCD checks, and compared against the older single-nearest-bin approximation. In a fresh **12**-case public-selected *10-bit* semiprime study, a fixed public B7 classical filter factored **8/12**, leaving four; **one** B7 survivor had **zero quantum-model factor-production success** for both bases. Among only **three** other comparable model-factor-producing keys, the cubic transform retained lower modeled expected logical CCX per factor success under the full all-bin distribution: cube/plain **0.5275** replication trigger, **0.5357** locked trigger, **0.5398** locked control. The nearest-bin proxy overstated the cube benefit slightly on the two trigger examples. The original CI had a corrected external validation-variable-shadowing bug; model/sampling unchanged, and all four corrected jobs plus separate immutable-artifact verification passed. **Critical: trial division ≤√N≤32 trivially factors every tiny semiprime**; no actual quantum-factoring value, population benefit, hardware speed/fidelity result, new theorem or RSA attack. The separate logical phase-recycling width bound remains **53→34** at this 10-bit generic arithmetic scale, wholly independent of cube.

## Verified analytically tail-bounded full-QPE on n17/n18 (October 2026; zero QPU)

**Research lead: Chase Lunsford / CaMaLabs.** [Frozen protocol](docs/DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_PREREG.md), [verified result and primary negative boundary](docs/DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_RESULT.md), [4/4 successful independent numerical CI jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677647156) and [successful immutable JSON receipt preservation CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677791142). On new public-selected 17–18-bit semiprimes, an exact-head + analytically bounded omitted-tail method now provides **complete ideal-QPE factor-producing-success and generic logical CCX cost intervals** without evaluating up to 2^36 phase bitstrings. A fixed 65-bin/eigenphase window has universal omitted-tail bound ≤1/63; observed maximal stage tail ~0.003118, numerical roundoff not formally interval-certified. Eight distinct N surviving bounded B31 public factoring were selected from 21 screened (13 already classically solved). **ALL eight were then factored by PUBLIC Pollard rho**, so none represents practical quantum utility. The strict cube/plain **successful** ideal-model CCX interval is below 1 in five cases, above 1 in one, and undefined for **two 18-bit trigger Ns with zero public factor-producing CF denominators**. Thus the prespecified primary 18-bit trigger comparison **FAILED** even though order reduction sometimes occurs; the sample is small. Exact original receipts and all negative results are preserved. Independently of cube, iterative phase recycling's logical peak remains **88→55** at n17 and **93→58** at n18, not a physical/fault-tolerant resource measurement. Previous 144-row v2 classical-first negative/underpowered findings are unchanged.

## Verified new 22-bit public selector versus unconditional cube (October 2026)

**Research lead/original direction:** Chase Lunsford / CaMaLabs. [Preregistered public-only protocol](docs/DARK_STAR_N22_SELECTOR_VS_CUBE_PREREG.md), [verified result and important failures](docs/DARK_STAR_N22_SELECTOR_VS_CUBE_RESULT.md), [successful frozen-manifest-plus-four-job Actions run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694538017), [successful independent receipt audit](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694776139). New public SHA-ranked 22-bit semiprime frame, 31 publicly screened Ns: **19 classically factored at B31** and 12 public survivors frozen as a separately committed N/base manifest **before QPE order simulation**. Stronger publicly bounded B47 and Pollard rho completely factored **all twelve**: zero practical quantum need. Strict public factor-producing CF/GCD + nearest-bin ideal-QPE 8192-phase model, two independent numerical seeds. On the frozen CONTROL subset, ladder (3/5/7 conditional) vs simple always-cube had modeled CCX per success ratios **0.965595 and 0.965751**, but **only 3/6 cases improved and 3/6 worsened** in both seeds; preregistered majority criterion **FAILED** and row-bootstrap interval includes parity. Trigger subset ladder=always-cube *exactly* (1.0 both seeds); simple cube vs plain ratio **0.786726/0.784368**, 6/6 model improvements, all six still classically solved. This is a **conditional ideal-QPE logical-CCX resource effect only**, not full-bin exact measurement simulation, hardware speedup, physical-qubit benefit, improved classical factoring or RSA break. Independently, the n22 generic arithmetic model peak **113 wide→70 recycled** simultaneous logical qubits due to phase recycling—not exponent selection. Complete frozen manifest and original receipts are committed.

## Research record

Useful starting points:

- [`docs/QRR_SHOR35_PREPRINT_DRAFT.md`](docs/QRR_SHOR35_PREPRINT_DRAFT.md) — formal preprint draft
- [`docs/N35_NOVELTY_AUDIT_2026-09-14.md`](docs/N35_NOVELTY_AUDIT_2026-09-14.md) — novelty/priority boundary
- [`results/hardware/SHOR35_AFFINE_HARDWARE.md`](results/hardware/SHOR35_AFFINE_HARDWARE.md) — Fez affine hardware record
- [`results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md`](results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md) — unoptimized cross-backend controls
- [`results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md`](results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md) — optimized Marrakesh runs
- [`results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md`](results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md) — same-job layout control
- [`docs/QISKIT_ECOSYSTEM_SUBMISSION.md`](docs/QISKIT_ECOSYSTEM_SUBMISSION.md) — Ecosystem membership/submission record

## Citation and license

Citation metadata is available in [`CITATION.cff`](CITATION.cff).

Licensed under the [Apache License 2.0](LICENSE).
