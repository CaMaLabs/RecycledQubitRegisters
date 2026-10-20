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

## Verified fresh N22 full-outcome-tail negative gate (October 2026)

**Research lead:** Chase Lunsford / CaMaLabs. [Frozen new public sample](results/dark_star_ptp/dark_star_n22_full_tail_public_manifest.json), [full validated report](docs/DARK_STAR_N22_FULL_OUTCOME_BOUNDED_RESULT.md), [actual successful CPU scoring CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38696858911), [independent untouched receipt audit](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38697122538). A disjoint four-key **22-bit** semiprime sample was committed BEFORE true-order simulation, after **7 public candidates screened and 3 factored at B31**. The remaining **4** were all classically factored with B47 (3) or prime trial (1). Modelled factor-producing ideal QPE uses all **65 centered phase bins** plus analytic `1/63` omitted-tail bound, while simultaneously bounding 16,384 independent pseudorandom eigenphase samples/stage via a stated **99% conditional Hoeffding confidence** (±0.017834 stage probability); results are **NOT deterministic exact full-bin QPE** or QPU results. On the **primary trigger**, one cube/plain successful-session abstract logical CCX ratio interval **[0.3575,1.9894]** includes parity and the other N has **NO valid public factor-producing CF denominator**, even after order shrinks. Both control rows also have intervals crossing 1. **No cube win or loss certified at the preregistered setting; PRIMARY cube benefit claim fails/is inconclusive.** All four trivially classically solved and public denominator precomputation itself can recover factors; no practical factoring advantage. Independently, analytic iterative phase recycling's n22 113→70 logical peak width bound remains intact and distinct from odd-power preconditioning. Every earlier favorable and negative result remains recorded, without retroactive selection.

## Verified frozen N22 precision-only full-QPE audit (October 2026)

**Lead: Chase Lunsford / CaMaLabs.** [Frozen numerical protocol](docs/DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_PREREG.md), [full careful verified result](docs/DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_RESULT.md), [successful 2-job high-precision CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730414791), [successful independent original-receipt audit](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730702345). This **re-uses the exact SAME four public-selected n22 semiprimes** as the earlier inconclusive all-outcome-tail holdout, so is **NOT independent replication or a new population benefit**. We used exact all-bin ideal QPE FFT through 18 phase bits (previously 12), **131072** frozen-seed eigenphase draws at higher stages (8× previous), variance-adaptive empirical Bernstein 99%-simultaneous *conditional* confidence bounds plus observed omitted-head mass and analytic max tail 1/63. All three factor-capable model CCX-per-success ratio intervals became **11–12× narrower**. Previously inconclusive trigger N=3623549 became **[0.7187,0.8574] cube/plain** (one conditional model improvement). Trigger N=3351017 **remains exact public-CF-factor-incapable**; control comparisons **[0.9237,1.1060]** and **[0.9422,1.0788]** remain inconclusive. The **original two-trigger primary claim still fails** and all four semiprimes remain classically factorable with public B47/trial; public certificate preparation itself can disclose proper factors and is not a free quantum operation. These are confidence statements requiring IID ideal sampling assumptions and floating computation, not proven hardware/fault-tolerant quantum speedups. Phase-register recycling's independent n22 analytical logical width remains 113 wide→70 recycled, separate from cubic base transforms.

## New independent 8-case N22 high-precision model holdout + reverse-SynthID methodological review (October 2026)

**Research lead/original quantum work:** Chase Lunsford / CaMaLabs. [Preregistered independent public sample](docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md), [full verified and bounded result](docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_RESULT.md), [public freeze + 2 scientific CI jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38808625980), [independent immutable receipt audit](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38809052306). The fresh **eight** 22-bit semiprime N/base sample, disjoint from prior **16** N22 selected cases, was committed as a public SHA manifest **BEFORE** any validation-factor/order or QPE scoring; from 25 publicly screened N, 17 initially factored with bounded B31 and 8 selected B31 survivors. Applying the PRE-FROZEN 131072-eigenphase, exact FFT QPE outcomes to m18, 65-center-window and analytic missing-tail ≤1/63, variance-adaptive nominal 99%-simultaneous statistical confidence ideal-QPE logic to new cases yielded **3/4** trigger cases that both can produce proper factors through strict public CF and have bounded abstract CCX/success ratio **below 1** (ranges **[0.7888,0.9150]**, **[0.7813,0.9159]**, **[0.8057,0.8525]**); the fourth trigger was exactly factor-incapable. **Preregistered trigger model criterion PASSED.** In control, 1/4 model favorable and 3/4 factor-incapable. **ALL eight were independently factored by publicly bounded classical B47/rho**; public CF factor-certificate enumeration itself is significant classical factor-recovery work. Thus no practical factoring speedup, hardware speed/fidelity or QPU physical-resource result. Separate peak n22 generic model phase-recycling logical width remains **113→70** entirely independent of cubic transformation.

At the same request we inspected [Alosh Denny's reverse-SynthID](https://github.com/aloshdenny/reverse-SynthID) source and noncommercial research license: [credited transfer audit](docs/REVERSE_SYNTHID_TRANSFER_AUDIT.md). Cross-reference Fourier phase consensus, independent control conditions, and blind null/shuffle tests may inspire **future noise-robustness diagnostics**, but **nothing involving image-watermark bypass or its code** was copied or added to the frozen quantum experiment. No direct application to modular-order discovery has been validated.

## October 2026 — spectral-consensus controls and strictly Open-Plan-only QPU preflight

**Research lead: Chase Lunsford / CaMaLabs.** [Full documented controls, experimental data and billing boundary](docs/QRR_SPECTRAL_COHERENCE_OPEN_QPU_STATUS.md), [successful synthetic phase-consensus CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38987863052), and [strict real-QPU preflight run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38987984332). Independent elementary circular Fourier-phase consensus, concept credited to Alosh Denny's reverse-SynthID, detected known toy r4/r6 ideal-QPE synthetic signal at 0%,15%,35% white noise with low shuffled/white-null false positives — BUT **stable apparatus artifacts triggered 100% FALSE positives**, so phase consensus is only a reproducibility diagnostic, NOT authentication of quantum phase/order/factor production. No licensed SynthID code or watermark bypass copied.

For ACTUAL IBM Open QPU, `hardware/qrr_ibm_open_only_real_qpu_pilot.py` prepares matched genuine modular multiplication Shor15 wide/recycled circuits (8 vs5 logical), strictly verifies **the active IBM instance plan=OPEN** before submission (and again after backend resolution), refuses paid/unknown/simulator, and caps ONE 2×64 shot job to 30 sec QPU execution max. **Actual QPU not executed**: the [GitHub Actions preflight receipt](results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json) says `PREFLIGHT_BLOCKED`, `submission_performed=false`, `job_id=null` because GitHub Actions cannot see `IBM_QUANTUM_API_KEY` or a locally saved account. A successful (green) CI indicates **safe non-submission**, NOT hardware success. User may securely add a protected GitHub Actions `IBM_QUANTUM_API_KEY` secret and manually start [the Open-only one-shot workflow](.github/workflows/qrr-open-only-real-qpu-one-shot.yml), or run the script locally with a saved Open Plan Qiskit account. No free-to-paid fallback and no scheduled QPU tasks. N15 is only a small hardware validation, not a cubic Dark Star order reduction or scalable RSA factoring claim.

## REAL IBM Fez Open Plan hardware milestone — Shor N=15 recycled vs wide (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** [Original REAL-QPU run 38994722997](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38994722997), IBM **Open Plan verified before actual submission**, job **`db9dod1gv2cc73e5c410`** on **`ibm_fez`**, no paid plan fallback. [Full documented scientific result](docs/QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) and [original hardware raw shots](results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json). Two ACTUAL device controlled modular multiplication + phase QPE circuits with **64 shots each** recovered proper factors **3×5** of **N=15**: recycled **49/64 =76.56%** vs wide **38/64 =59.38%**. Recycled **5 logical qubits**, 55 native CZ, depth180; wide **8 logical qubits**, 87 CZ, depth221, backend compiled to its full 156-qubit device container with only 5/8 active logical locations. These are *single-run layout-dependent compiler and noisy-device statistics*, NOT a statistically established general fidelity advantage. This N15,a2 hardware milestone validates tiny genuine Shor phase recycling, **NOT the Dark Star cubic transform** (order4 unchanged by cube), large n22 models, physical error correction, practical or RSA-scale factoring. User's IBM key remained securely in GitHub Actions secret, and Open Plan-only guard was enforced immediately before `sampler.run`. Previous credential failures are historically documented and **resolved**.

## N=35 first full-register public cubic IBM Fez *compiler* test — ~61% gate/depth reduction, QPU gate FAIL (October 2026)

**CaMaLabs research lead: Chase Lunsford.** [Preregistered zero-QPU native target study](docs/QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_PREREG.md), [complete original-results report](docs/QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md), [2/2 successful architecture compile jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995707019), [independent frozen JSON audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995864891). On N35, public base2→cube8 reduces validation order **12→4**, with identical Shor gcd witness 29 factoring trivially to 5×7. The public-only **64-state full-residue-permutation** synthesis receives NO hidden order/orbit. Four phase bits, fixed profile/seed, live IBM Fez **COMPILER** (NO QPU submission): recycled CZ **8455→3325** (**−60.7%**), compiled depth **17108→6595** (**−61.5%**); wide CZ **7946→3081** (**−61.2%**), depth **17193→6616** (**−61.5%**). The cube renders two of four controlled modular exponentiation power rounds identity. **CRITICAL NEGATIVE: all four baseline/cube circuits FAIL predeclared <=800 native CZ and <=2000 depth QPU feasibility, so no Open Plan QPU test was submitted.** This full-residue lookup compiler is not scalable arithmetic-efficient Shor; physical fidelity and total factor-production efficiency remain UNTESTED. Existing first real IBM Fez N15 recycling milestone still valid but does not test cubing. [Original full JSONs](results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_recycled.json) and [wide](results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_wide.json) preserved without re-running.

## N35 arithmetic replacement audit: original algorithmic n-bit multiplier still fails native gates (October 2026)

**Lead: Chase Lunsford / CaMaLabs.** [Frozen arithmetic replacement experiment](docs/QRR_N35_ARITHMETIC_REPLACEMENT_PREREG.md), [complete original-result report](docs/QRR_N35_ARITHMETIC_REPLACEMENT_RESULT.md), [four-arm successful Qiskit Fez-target compilation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996345928), [successful independent immutable-receipt preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996529069). Replaced full-64-state permutation synthesis with public-only n-bit reversible shift-add modular arithmetic, cleaned accumulator and helper flags, and simple public identity-round elision. Cubing N35 base2→8 still removes two of four QPE power rounds and halves CZ/depth *within this arithmetic constructor*. But native CPU-transpiler lowering of controlled QFT adders/comparators exploded to **recycled CZ 1,732,072→859,632**, native depth **4,766,896→2,370,305** and **wide CZ 1,733,136→860,151**, depth **4,763,959→2,372,924**; all four fail frozen CZ≤800/depth≤2000 device thresholds. This is far worse at N35 than the prior order-independent 64-state direct permutation compiler (cube recycled CZ3,325, wide CZ3,081), though compiler settings differ, so the cross-family comparison is descriptive. All computations were real-IBM-Fez-*target* compilation, **ZERO REAL QPU JOBS**; no Open Plan usage, hardware results, practical factoring or RSA-scale success. Classical arithmetic shadow validation is not yet an exhaustive gate-level native-unitary proof. Next engineering direction: **ripple-carry/Toffoli explicit clean-ancilla modular constant adder**, starting with single-multiplier controls before any new hardware feasibility claim.

## Verified N35 primitive reversible Toffoli kernel: 128/128 gate proofs and hardware gate FAIL (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** [Frozen one-controlled-multiplier primitive-gate protocol](docs/QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_PREREG.md), [full independently verified report](docs/QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_RESULT.md), [original zero-QPU CPU/IBM Fez target compilation jobs 2/2 PASS](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997012532), and [independent untouched original receipt verification](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997085447). New original **X/CNOT/Toffoli-only n-bit reversible modular arithmetic** for N35, no private order/orbit or QFT adders, passed **all 128/128 actual circuit instruction-level control/residue checks**, including **23/23 helper ancillas returned to |0>** and invalid y>=35 unchanged. Single controlled multiplier source uses 30 logical qubits, base2 1,964 primitive gates vs public cube8 2,062. Actual `ibm_fez` **TARGET COMPILER ONLY** costs base2 **27,929 native CZ, depth59,947**; cube8 **29,822 CZ, depth63,922**—cube ONE multiplier is **6.78% costlier** in CZ, reminding us earlier favorable 4-bit cube circuits gained mainly by skipping **two identity modular power rounds**. The frozen native hardware cutoff **CZ≤800, depth≤2000 FAILS both**; no IBM QPU job, free runtime or paid runtime spent. This strengthens correctness of our gate arithmetic but is NOT a successful hardware factoring device, scalable RSA result, or evidence for running infeasible N35 Shor circuits. Research log records the positive and negative milestones without erasure.

## Cached enable controls reduce N35 native two-qubit cost ~33% — verified, QPU still blocked (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** [Frozen hypothesis](docs/QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md), [verified full result](docs/QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_RESULT.md), [successful original zero-QPU native Fez target experiment](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005624438), [independent immutable JSON verification](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39005699941). Compute clean `active=(control AND valid)` once and `enable=(active AND work_bit)` for each modular-add instead of redoing nested three-way control gates throughout a *public-only* full-residue (not order/orbit compiled) six-bit N35 single controlled multiplier. **Both bases passed 128/128 actual X/CX/CCX instruction-by-instruction computational-basis tests**, with ALL **25 auxiliary bits cleaned**. For same fixed Fez *CPU ISA compilation* (not QPU): base2 native CZ **27,929→18,719** (−32.98%), depth **59,947→42,335** (−29.38%); cube8 CZ **29,822→19,912** (−33.23%), depth **63,922→44,381** (−30.57%). Original source primitives 1,964→1,536 and 2,062→1,578. Added 2 clean ancillas (30→32 logical qubits). **Engineering gate PASSED; device gate FAILED**: even the smallest kernel is **23.4×** over the frozen 800-CZ budget and **21.2×** over 2,000-depth. **Zero additional real QPU, free or paid runtime consumed.** No cubic single-multiplier savings over untransformed base2; earlier four-round cubic advantage derives from public identity round elimination. Do not claim larger real QPU factoring or RSA advantage.

## Public low-prefix carry N35 arithmetic: a further 33–36% native CZ reduction, QPU limits still FAIL (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** The next [frozen public-constant low-prefix carry and threshold-shortcut study](docs/QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_PREREG.md) has [complete original results](docs/QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md), [two successful authentic emitted-gate/IBM Fez TARGET-compilation jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006320227) and [independent original-result JSON preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006395142). For ONE full-residue controlled N35 modular multiplier, retain cached active/enable conditions and replace repeated suffix increments by **high-to-low output bit toggles from public low-prefix carry**, while stripping trailing-zero bits from public compare thresholds. Before any native compilation, all **16 unique public modular-add constants ×99 input/control tests=1,584/1,584**, plus **128/128** full multiplied control/residue tests **PER BASE**, pass actual X/CX/CCX gate-level interpretation with all 25 helper bits returned zero. CPU compilation for IBM Fez using same opt1/seed8776 reduced native CZ **base2 18,719→12,517 (−33.13%)**, depth **42,335→32,312 (−23.68%)**; cube8 CZ **19,912→12,680 (−36.32%)**, depth **44,381→33,138 (−25.33%)**. Source primitive gates INCREASED, but expensive CCX decreased while cheaper CX increased. This is **one combined two-component ablation**; contributions have not yet been separately measured. **Immutable device gate FAILED**: even lowest-cost single multiplier 12,517 CZ/32,312 depth exceeds prior 800CZ/2000-depth limits, so **NO REAL QPU SUBMISSION, free runtime, or paid runtime**. This is compiler-level research for classically trivial public N35, not experimental quantum cubic factoring or cryptanalytic quantum advantage.

## N35 isolated public carry vs threshold optimization: measured compiler interaction, QPU gate FAILS (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Frozen four-arm component preregistration](docs/QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_PREREG.md), [full verified report](docs/QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_RESULT.md), [original **4/4** completed CPU/Fez native-target-only experiments](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007742612), [independent original JSON evidence preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007830864). Isolated **public low-prefix-carry rewriting alone** and **public comparator threshold shortening alone** in the honest full 6-bit N35 controlled modular multiplier (base2 and cube8), holding cached enable, 32 logical application qubits, Qiskit versions, backend target, optimize1/seed8776 fixed. EVERY one of four new arms passes **1,584 actual primitive-gate modular-add cases plus 128 actual primitive whole-multiplier cases**, control/invalid identity and all **25 ancillas clean**. Native CZ (base2): original baseline **18,719**, prefix-only **14,392**, threshold-only **18,010**, both combined **12,517**. Cube8: baseline **19,912**, prefix-only **14,948**, threshold-only **19,344**, both **12,680**. Prefix-only explains substantially more of the separately measured native-CZ reduction than threshold-only; both combined outperform additive component-cost prediction by **1,166 CZ on base2 and 1,700 CZ on cube8**. This is a fixed-compiler *resource interaction*, not physical quantum advantage. **All four new isolated variants fail original immutable CZ≤800/depth≤2000 real hardware gate**, the best previous combined also fails; **ZERO actual QPU submissions, free/paid runtime, or new hardware factoring tests**.

## Shared forward-carry N35 ablation: exact clean-gate proof, but 56% worse CZ than prior best (October 2026)

**Lead: Chase Lunsford / CaMaLabs.** [Frozen standalone shared-carry experiment](docs/QRR_N35_SHARED_CARRY_REUSE_PREREG.md), [complete independent negative result](docs/QRR_N35_SHARED_CARRY_REUSE_RESULT.md), [2/2 successful actual-gate-proof/Fez CPU target compilation CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060426103), and [independent unchanged original-result audit](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060515347). A reversible adder that computes one enabled public-constant carry chain, updates all six register bits and erases the carries from **new** output using a backwards subtract-k borrow recurrence passed **8192** direct emitted X/CX/CCX conditional modulo64 basis checks, **1584** modulo35 controlled-add checks and **128** complete multiplier inputs **per base**; all **25 auxiliary qubits clean**. However, compared with the prior best public low-prefix/threshold circuit, **native IBM Fez CPU compilation became WORSE**: base2 CZ **12517→19552** (+56.20%) and depth **32312→42236** (+30.71%); cube8 CZ **12680→19895** (+56.90%) and depth **33138→43075** (+29.99%). Same 32 application logical qubits. Frozen engineering gain FAILED, physical gate CZ<=800 and depth<=2000 FAILED, **ZERO QPU runtime**. Continue using old best [public prefix carry and shortened threshold](docs/QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md) and preserve the negative to avoid repeating this expensive carry-sharing decomposition. This study is not actual N35 QPU factoring or any cryptographic advantage.

## N35 disjoint comparator: exhaustive gate proof, negative native resource ablation (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Preregistered isolated public threshold-prefix comparator experiment](docs/QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md), [verified full negative result](docs/QRR_N35_DISJOINT_PREFIX_COMPARATOR_RESULT.md), [successful corrected two-arm gate-proof/native-compiler run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071031851), [successful independent original-JSON audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071126315). **Both a=2 and cube8 pass 42,672/42,672 actual X/CX/CCX comparator gate-basis cases, 1,584/1,584 modular addition cases and 128/128 full six-bit controlled multiplier cases, every 25 aux bits returned clean.** Nonetheless replacing the public shortened ripple comparator by disjoint prefix minterms increases Fez **CPU target compiled** native CZ **base2 12,517→21,839 (+74.47%)** and **cube8 12,680→22,727 (+79.24%)**; depth 32,312→49,751 and 33,138→51,441. This is a VERIFIED NEGATIVE native gate-cost ablation; keep the previously verified best `hardware/qrr_n35_public_prefix_carry_single_modmul.py`. The first CI stopped on a documented 21,336 vs actual 42,672 test-count assertion, repaired without changing source gate operations before native compilation. **Every QPU hardware-feasibility gate remains FAILED; no real quantum device, free runtime or paid runtime used.** This does not establish a new factoring theorem, RSA-scale cryptanalysis or a hardware-level speedup.

## N35 relative-phase ripple carries: new best native CZ 9,263 / 9,426 — exact quantum-phase gate proof, QPU still blocked (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Precommitted experiment](docs/QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md), [full independently audited result](docs/QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md), [successful 2/2 source-run exact phase-aware gate proof and native IBM Fez **CPU TARGET** compilation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072693905), [successful independent original-receipt preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072788179). A prior [relative-phase clean `multi_x` V-chain attempt](docs/QRR_N35_RELATIVE_PHASE_CLEAN_VCHAIN_PREREG.md) yielded a **verified null**: no 3+-control gates survived the original enable-latch optimization (0 full-source RCCX; unchanged CZ/depth), with exact [original failed-intervention/phase-passing receipts independently preserved](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072844818). In contrast, compute and uncompute the **comparator's temporary carry** register with relative-phase RCCX and its **actual operator inverse**, while leaving all semantic output flips, public modular arithmetic, controls, width32 and 25 clean auxiliaries unchanged. **Direct complex-amplitude interpretation of ACTUAL emitted quantum gates** shows final **exact phase +1** as well as correct outputs and clean scratch across **42,672 comparator cases, 1,584 modulo35-adder cases and 128 complete six-bit multiplier cases PER public base**. Full source has **596 RCCX** base2 and **616 RCCX** cube8; source exact CCX drops from 756→160 and 778→162. Fixed seed8776/optimization1 native `ibm_fez` *CPU compilation* reduces **base2 CZ 12,517→9,263 (−26.00%), depth32,312→21,772 (−32.62%)**, and **cube8 CZ12,680→9,426 (−25.66%), depth33,138→21,933 (−33.81%)**. **Engineering win VERIFIED, but the full native device heuristic still FAILS:** even one base2 multiplier is ~11.58× above 800-CZ gate and ~10.89× above depth2000. **ZERO real N35 QPU jobs, free or paid runtime; no cubic factoring QPU demonstration or RSA-break claim.** Original real IBM N15 phase recycling remains an independent, preserved milestone.

## Active-only RCCX cached latch: passes BOTH N35 public base/compiler gates; enable-only cubic depth regression (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** The [four-arm preregistered, original-result-verified phase-exact N35 cached-control latch ablation](docs/QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_RESULT.md) isolates temporary long-lived `active` vs short-lived per-term `enable` control gates. [Original 4/4 source phase/operator proof and native IBM Fez CPU target experiment](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074602823) and [independent unchanged original JSON audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074706319) **SUCCESS**. Every public base2/cube8 `active_only` and `enable_only` variant passed **8 local + 42,672 comparator + 1,584 modular add +128 complete public full-residue controlled-multiplier actual emitted quantum gate basis checks**, with exact final complex phase **+1**, unchanged control and all 25 auxiliary bits reset, source register width32. Fixed Qiskit~=2.5.2/runtime~=0.47, Fez native target read-only, opt1 seed8776, no true multiplicative order/orbit injection. **Active-only, only 2 source CCX→RCCX latch compute/uncompute replacements, improves BOTH public bases**: a2 CZ**9263→9042**, depth**21772→21541**; cube8 CZ**9426→9156**, depth**21933→21820**. This is the newly VERIFIED conservative two-base phase-correct engineering improvement. **Enable-only, 24 source latch replacements**: a2 CZ8756/depth21007 but cube8 CZ9424/depth**21995 (WORSE)**. The earlier both-latches combination gives best base2 CZ8542/depth19819 but cubic depth22005 (WORSE) and also fails the two-base engineering gate. [Original both-latch mixed outcome](docs/QRR_N35_RELATIVE_PHASE_CACHED_LATCH_RESULT.md) independently archived. **All N35 device heuristics STILL FAIL**: smallest ONE multiplier remains >800 CZ and >2000 depth, so **NO real N35 QPU jobs, Open Plan free runtime or paid IBM Runtime were used**. CPU ISA-gate count savings are not a full four-bit QPE, experimental N35 factoring or RSA quantum advantage. Our genuine real N15 Open Plan recycling result remains independent and preserved.

## N35 active-only relative-phase latch eight-seed matched robustness: NOT ROBUST on both public bases (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Precommitted 8-seed protocol](docs/QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_PREREG.md), [full independent report and original matched seed table](docs/QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md), [original full-32-CPU-native-compilation GitHub Actions run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080813622), and [independent original-artifact verification/preservation success](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39080960758). Exactly **8 fixed Qiskit Fez CPU compiler seeds×2 public bases×2 circuits=32** full source multiplier ISA compilations, each pairing the original phase-aware `neither` comparator circuit and the `active_only` RCCX-latch version with identical compiler settings. Before target access, ACTUAL emitted operator complex-phase/clean-state proofs passed **8 local latch +42,672 comparator +1,584 modadd +128 original full-multiplier +128 active full-multiplier PER BASE**, 32 logical source qubits and all 25 helpers zero with exact final phase+1. **Seed8776 exactly reproduced** previous archived CZ/depth results, but only **5/8** base2 and **1/8** cubic8 seeds improved *both* CZ and depth in the same matched pair. Median paired native CZ/depth changes active−original: base2 **−218.5 / −541** (favorable but below strict ≥6/8 joint-win criterion); cubic8 **+106.5 / +346.5** (unfavorable). Thus **both preregistered two-base robust engineering gates FAIL**. The original source run's scientific proof and all 32 compiles succeeded but GitHub marked its workflow FAILURE because a subsequent auditor used a mismatched JSON field `device_feasible_active_only` vs actual `device_feasible_active`; original artifacts were independently audited and permanently committed **without recompilation** in a separate SUCCESS workflow. **QPU feasibility fails for all 32 circuits** against the frozen native CZ≤800/depth≤2000 gate. **ZERO real quantum device jobs, free Open Plan or paid Runtime used**. This compiler seed test is not QPU-noise performance, full four-QPE-round factoring, or RSA cryptanalysis; preserve our original base2/cubic results and the true N15 Open-Plan hardware recycling pilot separately.

**Completion correction (same October 2026 experiment):** The downstream JSON field-key typo was corrected without touching the science in [commit `d9cfe355`](https://github.com/CaMaLabs/RecycledQubitRegisters/commit/d9cfe355e9c54f0f55298edf7f93395af1097a28). The [fully rerun eight-seed source workflow **39084396945**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084396945) is now **GREEN, 2/2 base jobs**, including both scientific and independent postcompilation audits. A [separate original-artifact reconciliation workflow **39084519756**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39084519756) is also **GREEN**; it compared **all 32/32** new target-CPU native CZ/depth and full native ISA gate dictionaries to the immutable originals and found **exact equality**. New raw rerun receipts and a SHA-256/per-seed comparison manifest are preserved [separately](results/ibm_shor35_active_only_multi_seed_green_rerun_39084396945/). Original historical red CI and result receipts remain visible, as do the unchanged **negative** scientific robustness and physical-device gates. ZERO QPU work.

## Public N35 constant-bit/carry fusion: exact quantum arithmetic PASS, two-base eight-seed native robustness FAIL (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Frozen prior to scores](docs/QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_PREREG.md), [complete two-base eight-seed report with unfiltered original comparisons](docs/QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_RESULT.md), [original 2/2 successful IBM Fez **CPU-only target compilation** jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082263845), [successful independent untouched-original-JSON audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082382115). A **single public constant-add gate rewrite** replaces a controlled `carry>=threshold` flip XOR controlled public `k_j=1` flip with **one controlled `carry<threshold` flip** when the public lower constant bits are nonzero. It retains the same full N35 six-bit residue controlled multiplier, phase-correct RCCX temporary comparator carries, cached controls, 32 logical qubits and all 25 clean helpers. Actual emitted Qiskit instruction `Operator` complex-phase gate proofs **PASS** for all 8,192 6-bit public constant additions, 42,672 comparators, 1,584 modular additions and **128 reference + 128 new full controlled multiplier cases PER PUBLIC BASE**, with exact final complex quantum phase+1 and no garbage.

The edit actually removes **51 source CX for base2 and 55 CX for public cube8**, substituting 102/110 transient X inversions while leaving source RCCX/CCX unchanged. Under **32 native Fez target CPU compilations** (eight exact matched Qiskit seeds ×2 bases×2 circuits), however, only **3/8** base2 and **2/8** cube8 seed pairs reduce **both** native CZ and depth in the same layout, failing the preregistered ≥6/8 robustness rule. Median paired candidate−original CZ/depth deltas are base2 **−31/−15** and cube8 **−169/+170.5**; cubic depth regresses despite most seed CZ counts improving. Historical old seed8776 native resource outputs reproduced exactly. **Correct arithmetic does not guarantee physical gate savings.** The best shared verified comparator-only source remains the reference; do not promote a favorable individual seed or discard this negative result. Every single-multiplier circuit still exceeds immutable physical preflight CZ≤800/depth≤2000; **zero QPU jobs, Open Plan runtime or paid runtime**, and no complete quantum N35 factoring experiment was performed. All original N15 true hardware and N35 negative/conditional-positive milestones remain preserved.

## N35 OR-carry comparator: 8/8 matched-seed native CZ savings on BOTH bases; cubic depth robustness misses gate (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Precommitted phase-correct public OR-carry lowering and strict two-base eight-seed protocol](docs/QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_PREREG.md), [full verified result with ALL 16 matched native CPU seed pairs and exact complex phase proofs](docs/QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md), [2/2 original successful Qiskit IBM Fez TARGET CPU compiler jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095494407), and [independent original-artifact audit and preservation success](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095605020). The only new unitary source intervention is the exact public comparator OR identity `x OR p = p XOR (x AND NOT p)`: replace two controlled CNOTs+relative-phase Toffoli in an OR carry with **one CX, two temporary X gates and same RCCX**, then reverse the temporary carries with true RCCX.inverse(), preserving exact +1 coherent quantum phases and all 25 returned-clean ancillas. Source CX **base2 1033→691**, cubic base8 **1077→717**; RCCX and exact CCX counts unchanged, source logical qubits32. Before any native compiler target read, ALL actual emitted-operator complex-phase checks passed on **4 Boolean/actual adjoint checks, 42,672 comparator, 1,584 modular-add, 128 old and 128 new full-residue multiplier basis input cases PER BASE**. Exactly 8 preregistered matched Qiskit seeds for each base yielded native CZ strictly lower for **8/8 base2 AND 8/8 cubic8** paired circuits. Median native CZ delta candidate−old **base2 −359 and cubic8 −277**, median native depth delta **base2 −419 and cubic8 −278.5**. But frozen robust requirement was **at least 6/8 seeds improving BOTH CZ and depth on EACH base**: base2 **6/8 PASS**, cubic8 **5/8 FAIL**; therefore TWO-BASE overall gate FAILS despite universal paired CZ savings. Seed8776 old values reproduce exactly: new base2 native **8311 CZ/depth19981**, cubic8 **9141 CZ/depth21528** for **ONE N35 modular multiplier**, versus old 9263/21772 and9426/21933. **Every one of 32 CPU compilations still FAILS the frozen real-QPU device preflight CZ≤800 AND depth≤2000**. **ZERO real quantum jobs, free Open Plan or paid Runtime used**; this is NOT a full Shor N35 QPE hardware/factor recovery or a cryptographic quantum advantage. All positive/negative older history remains preserved under CaMaLabs attribution.

## N35 source-negated OR-carry: two-base matched-seed unitary robustness PASS, De Morgan remains preferred (October 2026)

**Research lead: Chase Lunsford / CaMaLabs.** A [separately preregistered alternate OR-carry gate polarity](docs/QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_PREREG.md) was checked with ACTUAL emitted Qiskit quantum `Operator` complex phase +1 for **42,672 comparator, 1,584 modular addition and 128 complete multiplier input cases PER design/base**, all 25 helper qubits returned clean. It implements public `x OR p = x XOR ((NOT x) AND p)` inside reversible temporary ripple comparison, removing 2 CX and adding 4 temporary X per complete OR compute/uncompute; the earlier separately studied one-CX comparator instead inverted p. The [original two-arm eight-seed run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099579484) **2/2 SUCCESS**, [independent original source-artifact audit and preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099703212) **SUCCESS**; [full 16 matched-seed original JSON rows and research interpretation](docs/QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_RESULT.md). Relative to matched original shortened-ripple comparator: **base2 8/8 joint CZ+depth wins** with median paired native CZ **−464.5** and depth **−1362**; cubic8 **6/8 joint wins**, CZ median **−311.5**, depth median **−1053.5**. Exact historical seed8776 source baseline reproduced. **Strict two-base engineering robustness PASS, but this is NOT the best design:** the independently [verified zero-CX De Morgan source](docs/QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) remains preferable with 8/8 joint two-base wins vs the previous one-CX source and lower CZ/depth than this source-negation variant at seed8776. Native Fez **CPU target compilation only**, not real device measurements or a full Shor factoring circuit. Every CZ≤800/depth≤2000 device preflight **FAILED**, **ZERO IBM QPU jobs or free/paid runtime**.

## De Morgan plus active-only N35 cached control: exact source phases, but eight-seed robustness FAILS for both public bases (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** The independent [De Morgan zero-CX public comparator 8/8 two-base matched-seed success](docs/QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) was retained as the baseline while evaluating **ONLY** two reversible `active=phase&valid` clean cached-control CCX→RCCX/actual inverse changes. [Frozen new protocol](docs/QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_PREREG.md), [2/2 successful actual gate-phase and CPU Fez ISA compilation jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100095129), [independent ORIGINAL JSON receipt audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100203559) and [full native seed tables/report](docs/QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_RESULT.md). Both original and candidate circuits passed actual emitted Qiskit quantum `Operator` phase **+1** and clean all25 auxiliaries across 4 Boolean identity cases, 8 local cached-latch tests, 42,672 public comparator tests, 1,584 modular-addition tests and 128 full controlled 6bit N35 multiplier cases *PER DESIGN/BASE*. Every one of the 32 pinned Fez **CPU TARGET-only** native compilations finished with old seed8776 De Morgan baseline exactly reproduced. **Predeclared engineering robustness FAILS:** base2 only **3/8** jointly lower CZ/depth, median paired CZ −138 but median paired depth **+112.5 (regression)**; cubic8 **5/8** joint wins, median CZ −131 and depth −379, below frozen **≥6/8**. The attractive cubic8 seed8776 alone (original CZ8758/depth20575→candidate **CZ8036/depth19202**) does **NOT** establish robustness, while base2 at same seed **regressed** (CZ7993/depth18604→8225/19554). Prior De Morgan-only remains the preferred pre-registered cross-seed architecture; original results and all negative controls preserved. Hardware feasibility **CZ≤800/depth≤2000 FAILS** even for one multiplier, **ZERO QPU jobs, free Open Plan or paid runtime**, not full Shor quantum factor recovery or RSA/cryptanalytic advantage.

## N35 public single-bit carry bypass: 8/8 base2, 7/8 cubic8 two-base robust matched-seed engineering PASS (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Frozen 8-seed two-base experimental preregistration](docs/QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_PREREG.md), [detailed result including EVERY seed](docs/QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md), [successful original native CPU experiment](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105116012) and [SUCCESS independent untouched original-JSON verification/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105265764). Using the strongest previously verified **8-seed robust** N35 public De Morgan zero-CNOT comparator as the SAME-SEED baseline, the next public modular constant addition change replaces a **redundant single-bit carry comparator** with a direct EXACT controlled source-bit XOR when public constant lower j bits equal `2^(j−1)`. This is order-blind, works for all 64 six-bit work values, and skips exactly **23 public source comparisons and 46 source CX** per full controlled N35 one-multiplier kernel on BOTH a2 and cube8, with unchanged 32 source qubits, all **25 ancillas zero**, same 596/616 temporary RCCX and 160/162 exact CCX source operations. **True quantum-phase tests** using the emitted Qiskit gate `Operator` monomial complex matrices passed **320 public arithmetic identities, 42,672 comparator cases, 1,584 modular additions for EACH baseline and candidate and 128 full control×work inputs for EACH**, exact final amplitude+1 on both public bases, all before backend read. Exactly **8 immutable matched transpiler seeds ×2 public bases×2 circuits =32 native Fez CPU-target compiles**: **8/8** base2 and **7/8** cubic8 seeds have BOTH native CZ AND depth strictly lower than their same-seed De Morgan baselines, and all paired native CZ/depth medians are favorable (**base2 −352.5 CZ, −911 depth; cubic8 −341 CZ, −1448 depth**). Original seed8776 anchors match prior unchanged receipts: **base2 7993/18604→7887/18221**, **cube8 8758/20575→7802/18449**. **Cubic seed409 worsens depth +60**, and is preserved in the full seed table. **Frozen strict two-base engineering robustness gate PASSED.** Nonetheless **ALL compiled one-multiplier circuits still FAIL native hardware CZ≤800 AND depth≤2000**; these are CPU ISA compiler proxies, not QPU gate fidelity or real factor recovery, and **ZERO QPU execution, Open/free IBM Runtime or paid IBM Runtime** occurred. No full four-round N35 QPE or cryptanalytic breakthrough claimed. Preserve independent actual real N15 IBM Fez Open Plan recycled phase pilot separately.

## N35 public signed modular correction: base2 improves across 8/8 matched seeds, cubic8 4/8 (not two-base robust) (October 2026)

**Original research lead: Chase Lunsford / CaMaLabs.** We continued from the **latest two-base-ROBUST [public one-bit carry-bypass baseline](docs/QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md)** (not a prior weaker active-latch iteration) and preregistered a single constant-dependent arithmetic equivalent: `k≤17` keeps `+k` then conditional `−35` correction, while `k≥18` uses `−(35−k)` then conditional `+35` correction with clean underflow/flag uncomputation. Full [preregistered source/matched-seed result](docs/QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_RESULT.md), [original 2/2 successful eight-seed experiment](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108692489) and [independently verified, unchanged source receipt preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108827186) are committed. **Each base passed 3,366 public arithmetic cases + 42,672 actual comparator phase cases + 1,584 old AND 1,584 new modular-add operator phase cases + 128 old AND 128 new complete full-residue controlled-multiplier cases**, every 25 helper bits clean, final complex quantum phase +1 and 32 source qubits. Exactly seven of 12 weighted additions per full multiplier use public signed correction. At fixed IBM Fez CPU target opt1, seeds [11,37,101,409,8776,12011,20261,45673], **base2 has 8/8 strict paired CZ/depth wins**, median paired ΔCZ **−394**/Δdepth **−1,133** and seed8776 original **7,887 CZ/18,221 depth** → new **7,345 CZ/16,858 depth**. **Cubic base8 has only 4/8 joint wins** (median ΔCZ−80/Δdepth−173.5) and actually **REGRESSES** seed8776 **7,802/18,449 → 8,199/19,269**. Therefore the predeclared **two-base robustness gate FAILS** despite a genuine base2-specific optimization. The original previous robust one-bit-bypass implementation remains our shared best verified baseline. All 32 authentic native ISA CPU compilation results, including unfavorable seeds, are preserved; **native QPU gate CZ≤800 and depth≤2000 FAILS everywhere** even for ONE N35 multiplier. **ZERO physical IBM quantum jobs, free/Open Plan or paid runtime**; no complete QPE factoring demonstration or practical cryptanalysis. Earlier genuine N15 IBM Fez real Open Plan phase-register recycling milestone remains independent.

## N35 source-only public constant sign selector: new 8/8+8/8 matched native CZ/depth win, zero QPU (October 2026)

**Research lead Chase Lunsford / CaMaLabs.** [Frozen 34-k source-gate score protocol](docs/QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_PREREG.md), [verified detailed two-base result](docs/QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md), [2/2 original successful eight-seed native source run](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367204317), and [independent unchanged raw JSON receipt audit/preservation](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367462324). Compared with the previously [robust public one-bit-bypass N35 kernel](docs/QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md) (not the prior signed k>17 cube8-negative branch), this **one public-constant-local intervention** selects signed/underflow or positive modulo35 correction based on **SOURCE-only** Qiskit score CX+6CCX+3RCCX. It chose **signed for every odd k**, original positive for every even k, and made six base2 / seven cube8 signed weighted add calls WITHOUT any native backend/compiler score, factors, true order, state-orbit shortcut, or hand-selected seed in the choice. **Exact Qiskit emitted quantum complex +1 phase checks passed** 3,366 public arithmetic identities, 42,672 unsigned comparator basis cases, **6,732 BOTH positive/signed public modadd operator cases**, and **128 original+128 new full-controlled-multiplier cases PER BASE**, all 25 aux returned clean, source width32. Original eight paired compiler seeds [11,37,101,409,8776,12011,20261,45673] under Qiskit2.5.2/runtime0.47.0 and read-only IBM Fez target opt1: **8/8 BOTH CZ AND depth strict native wins for base2 AND 8/8 for cubic base8**, negative per-base paired medians. Previous→new native seed8776 **base2 CZ7887→6871 (−12.88%), depth18221→16626 (−8.75%)**, **cube8 CZ7802→7315 (−6.24%), depth18449→16286 (−11.72%)**. Strong *compiler-level* arithmetic milestone, **NOT** a quantum hardware advantage or full Shor result. Same eight seeds used in earlier designs, so fresh unseen placement holdout remains an important next test. **Every original and candidate one-multiplier ISA circuit still FAILS immutable CZ≤800 AND depth≤2000 hardware preflight, so ZERO real N35 QPU jobs, Open/free or paid IBM Runtime and no physical N35 factor recovery.** The actual N15 Open Plan phase-qubit recycling QPU pilot is preserved separately.

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
