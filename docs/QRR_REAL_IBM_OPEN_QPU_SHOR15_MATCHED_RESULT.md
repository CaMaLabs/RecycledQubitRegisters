# VERIFIED — first one-shot IBM Fez REAL QPU phase-register recycling matched Shor15 result

**Research lead and program attribution:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-16 America/Los_Angeles (IBM/GitHub UTC timestamp 2026-10-17T02:23:42Z). Zero paid-runtime authorization or fallback. This is an actual hardware result, not a simulator prediction.

## Reproducible original proof and provenance

- Preregistered strict one-shot Open Plan conditions in [`QRR_CROSS_REFERENCE_COHERENCE_AND_OPEN_QPU_PREREG.md`](QRR_CROSS_REFERENCE_COHERENCE_AND_OPEN_QPU_PREREG.md), prior to original attempt.
- [IBM-fez REAL device GitHub Actions run **38994722997**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38994722997) **SUCCESS**; scientific job ID **`db9dod1gv2cc73e5c410`**. Authentication-only, ZERO-QPU prerequisite [38994675557](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38994675557) independently verified secret present, correct platform format, platform auth and at least one Open Plan instance.
- Hardware script [`hardware/qrr_ibm_open_only_real_qpu_pilot.py`](../hardware/qrr_ibm_open_only_real_qpu_pilot.py); existing [`ibm_runtime_guard.py`](../hardware/ibm_runtime_guard.py) queried unique live active instance from IBM `service.active_instance()` matched to `service.instances()`, required actual `plan=open`, verified after backend resolution and **IMMEDIATELY before `sampler.run`**. No paid, simulator, unknown billing, or offline fallback. IBM returned measured data.
- Immutable original [JSON receipt](../results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json) was committed by original hardware CI (commit `e6d41302d3786957bee27f734c580e438e32c311`). Contains actual backend, layouts, circuit native gate counts, original measured QPE bitstring histograms and strict public-gcd factoring results. Contains NO API token or account identifier. GitHub secret encrypted; IBM QPU run did not log key.
- Original trial: **ONE sampler.run** with **two native circuits × 64 shots**, `max_execution_time=30` seconds, IBM backend **`ibm_fez`**, an actual 156-qubit QPU. The numbers below are the **first and only** recorded original QPU pilot from this frozen protocol, without fitting/seeding or resubmitting due to unfavorable outcomes.

## Matched circuits and original raw results

Problem public N=15, a=2; actual controlled-modular-multiplication circuit over a 4-qubit work register initialized |1>, real QPE measurements. The iterative recycled architecture uses one remeasured/reset phase qubit with conditional phase feedback; the wide version uses four phase qubits and inverse QFT. Both actual circuit families create the modular unitary rather than injecting a known eigenphase; postprocessing tests measured public y/m with public modular exponentiation and proper `gcd(2^(r/2)±1,15)`. Factors **3 and 5** are returned without passing the private labels into the recovery routine. This extremely small instance is classically trivial.

| IBM Fez on-device actual test | Recycled | Wide |
|---|---:|---:|
| Original logical circuit qubits | **5** | 8 |
| **Device-width compilation representation** | 156 QPU qubits | 156 QPU qubits |
| Active logical-to-physical qubit locations | [144,143,142,136,141] | [143,144,145,146,136,142,123,141] |
| Transpiled circuit depth | **180** | 221 |
| Native CZ gates | **55** | 87 |
| Native SX gates | 105 | 154 |
| Native RZ gates | 85 | 107 |
| Mid-circuit measurement type | `measure_2` ×4 | final `measure` ×4 |
| `reset` | 4 | 0 |
| Conditional `if_else` | 6 | 0 |
| Measured shots | **64** | **64** |
| **Strict public-factoring success shots** | **49/64 =76.5625%** | **38/64 =59.375%** |
| Proper factors recovered | **3×5 yes** | **3×5 yes** |

Native CZ count reduction **32 fewer / 87=36.78%** for this backend-specific compiled circuit; native compiled depth **41 fewer /221=18.55%**; 3 fewer simultaneously live *logical* circuit qubits **37.5%** vs 8. **These are one particular compilation/layout, not universal native physical cost savings.** Compiled circuit objects expose the full backend's 156-qubit width, which is NOT 156 active application qubits; active logical 5 and 8 locations are listed.

**Actual measured 4-bit phase register outcome counts** exactly as original JSON:

- Recycled: `{"1000":18,"1100":15,"1101":1,"0100":16,"0000":14}`. 49 accepted factor shots, 15 not accepted.
- Wide: `{"1000":11,"1011":2,"1100":8,"1101":1,"0000":21,"0100":19,"0110":1,"0010":1}`. 38 accepted factor shots, 26 not accepted.

The observed factor success advantage is **+11/64 = +17.1875 percentage points** on this one 64-shot per-arm trial, **NOT** a statistically robust claim that recycled QPE is intrinsically more faithful. Different transpiler physical layouts, gate errors, qubit calibration, readout and finite shot noise confound the comparison. No separately randomized layout/pulse noise study, repeated-seed device batches or native same-layout mapping. The structural five-vs-eight logical-width advantage is concrete for this circuit; general hardware fidelity advantage remains unestablished.

## Boundaries: what 'real deal' means here

**This IS a genuine IBM QPU measurement of complete tiny-N modular multiplication based iterative vs wide phase estimation.** It proves that the protected Open Plan pipeline can submit, execute and recover proper factors 3 and5 via public postprocessing.

**This is NOT a real IBM demonstration of the odd-power Dark Star cubic preconditioner.** For N=15,a=2, the order is 4 and `gcd(4,3)=1`, so `ord_15(2³)=4`; cubing does NOT shorten order. It also does NOT validate larger n22 generic reversible arithmetic or classical-vs-quantum factoring advantage, scalable RSA, 2048-bit performance, fault-tolerant physical costs, reliable coherent phase consensus, theoretical superiority of cubic policies, or any free quantum breakthrough. The earlier frozen 22-bit semiprimes were all factored by classical B31/B47/rho and strict public certificate preparation itself can factor.

All historical wins/negative findings and the independently scoped SynthID-inspired spectral-consensus pilot remain preserved: its known-order synthetic signal gate passed, BUT the stable-apparatus-artifact false-positive rate was **100%**, so do not use circular coherence to authenticate real quantum order. Source [`QRR_SPECTRAL_COHERENCE_OPEN_QPU_STATUS.md`](QRR_SPECTRAL_COHERENCE_OPEN_QPU_STATUS.md).

## Next scientific gate

Keep the just-recorded verified hardware milestone before submitting anything else. Under a separately frozen matched experiment, test an actual factor-capable public a versus odd-power a³ order reduction on real Open Plan hardware **only if** device compilation passes genuine native gate, physical-qubit-layout, shot and depth/fidelity feasibility limits. E.g., previous N=209 pilot has validation order 90→30 but generic arithmetic and full-register-native compilations can be far too deep; no additional QPU job should be submitted without a new bounded and explicitly user-authorized sampling plan. Physically randomized layouts, readout mitigation and repeated matched device trials are required before general fidelity claims. Paid Open Plan fallback remains FORBIDDEN.
