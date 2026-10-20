# VERIFIED ROBUST 35-qubit four-controlled-power N35 arithmetic block — sign selector 8/8 both public bases; CPU-only, QPU infeasible

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-20. All costs are **Qiskit CPU compilation against an authenticated read-only IBM Fez backend target**, NOT real QPU hardware jobs, free or paid IBM quantum runtime, device shot results, factor recovery or quantum advantage. This is an actual coherent controlled **modular-exponentiation block with four phase control qubits**, but is NOT the entire Shor phase-estimation circuit: **NO inverse QFT, measurement, classical factor postprocessing or device execution**.

## Previous best and frozen test, no postselection

The prior independently verified [public constant static sign-selector](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md) chose positive or signed-underflow reversible modular addition for each public k=1..34 by a backend-independent Qiskit SOURCE-ONLY cost `S=CX+6CCX+3RCCX`; ties remain positive. The original exact source scoring chose **signed odd k and positive even k**, and the [independent fresh-seed holdout](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md) observed **8/8 base2 and 7/8 cubic8** matched native CPU CZ+depth wins for ONE full-residue controlled multiplier. The newer [bit-complement conjugated constant adder](QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_RESULT.md) failed native robustness and is deliberately excluded. Existing positive/negative N35 original receipt archives are unmodified, including the real IBM Open-plan N15 qubit recycling pilot which did not establish cubic-order benefit at N15.

The distinct [preregistered study](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_PREREG.md), initial git commit **`55ef0e4cbee5381dea331f1c31919966eb0e2b20`** BEFORE any new four-block resource outcome, freezes public bases2 and cubic8, the original public sign decision/source operations, four independent phase controls but shared work and 25 clean ancillas, eight never-before-scored seed values, the prior 8776 exact single-stage historical anchor, target+Qiskit versions/optimization and both-source matched transpiles. **Strict two-base engineering pass** only if each base earns ≥6/8 seeds with BOTH native CZ and depth strictly lower in the same match, negative both paired medians, all source complex-phase tests pass and old 8776 anchor exactly reproduces. **Separate device hard gate CZ≤800 and native depth≤2000**; absolutely no QPU jobs in this study even if an improved gate result occurs.

## Actual built 35-qubit coherent controlled-public-power architecture

New [source](../hardware/qrr_n35_static_sign_four_controlled_powers.py) independently builds two **literal** full-register quantum circuits per public base, one old positive-only robust arithmetic and one unchanged public-k sign-selected source. Registers: **four phase controls +6 work +25 auxiliaries =35 qubits**; the same six-bit target, accumulator6, wrap1, valid1, comparator carry6, scratch9, active1 and enable1 are shared across all four public phase powers. The validity `work<35` flag is computed ONCE and cleaned at the end, each nonidentity multiplication uses full reversible constant-weighted modular arithmetic/controlled work-acc swaps with exact inverse accumulator cleanup and phase-aware temporary carry gates. No precompiled state permutation/orbit, factors, multiplicative order, eigenphase, measurement, or injected answer.

All source powers come solely from `pow(public_base,2**phase_index,35)`:
- **Original base2 powers [2,4,16,11]**: four nonidentity rounds, 48 publicly weighted mod35 additions.
- **Cubic base8 powers [8,29,1,1]**: last two public multipliers equal ONE and are omitted as provable identity operations, so only two nonidentity rounds, 24 public weighted additions. No private order or factoring logic decides this.

The [original frozen per-public-k 34-row source gate vector/selection table](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md) was regenerated and required to match the archived original *EXACTLY* before backend read, along with these ACTUAL emitted quantum-gate semantic checks PER BASE, all PASS:
- **3,366/3,366** original public underflow arithmetic identities;
- **42,672/42,672** original quantum-phase-aware comparator gate cases;
- **6,732/6,732** exact-complex-phase public positive AND signed modadd gate cases;
- **128+128** original versus selected previously frozen ONE-multiplier gate cases, 25 scratch qubits zero and final complex phase+1;
- **1,024/1,024 ORIGINAL and 1,024/1,024 SELECTED entire FOUR-PHASE-BLOCK** cases per base: all16 possible control bit strings and all64 six-bit work values, all25 auxiliaries zero, phase controls unchanged, correct public `work × pow(base,integer_controls,35) mod35` on valid work and identity on invalid work, exact final Qiskit `Operator(inst.operation)` accumulated **complex amplitude +1** for every tested basis input. These original-unitary-basis results extend linearly to coherent superpositions with initially clean auxiliaries in an **ideal**, noiseless gate model, not to physical device fidelity. Across both bases, **4,096 entire block basis cases** passed.

| Actual full four-power-block Qiskit source operations | Base2 old | Base2 selected | Cubic8 old | Cubic8 selected |
|---|---:|---:|---:|---:|
| CX | 1213 | **1107** | 625 | **575** |
| RCCX | 2374 | **2082** | 1236 | **1094** |
| CCX | 648 | **602** | 329 | **309** |
| X | 6890 | **5970** | 3612 | **3052** |
| Total emitted source operations | 11125 | **9761** | 5802 | **5030** |
| Logical qubits | 35 | 35 | 35 | 35 |
| All 25 returned-clean scratch, exact output quantum phase+1 | PASS | PASS | PASS | PASS |

## Full native CPU eight NEW paired seed outcomes — BOTH bases robust PASS

Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47, Fez backend metadata READ ONLY, optimization1, **EIGHT NEW fixed seeds [239,647,1453,3701,6211,9421,16673,27191]**, no layout searches or seed exclusions. Exactly **32 new block native CPU compilations**, old then new per matched seed and base. Four additional historical SINGLE-multiplier 8776 anchor compilations used only for comparability, not the 8-seed numerator. Each seed result is an actual measured compiler count_ops/depth, not estimated by summing previous stand-alone compiles.

Matched delta = sign-selected minus original; negative reduces target resources. Both CZ AND depth must be strictly lower on the same seed.

### Original base2 public full block [2,4,16,11]

| Seed | Old CZ/depth | Selected CZ/depth | ΔCZ | Δdepth | Joint pass |
|---:|---:|---:|---:|---:|:---:|
|239|32887/75879|29171/67537|−3716|−8342|YES|
|647|32676/75265|29579/66740|−3097|−8525|YES|
|1453|32455/76638|28528/66573|−3927|−10065|YES|
|3701|31415/75331|28668/66577|−2747|−8754|YES|
|6211|32937/76508|29044/66484|−3893|−10024|YES|
|9421|32900/75910|29027/65461|−3873|−10449|YES|
|16673|32634/76979|28915/66530|−3719|−10449|YES|
|27191|32277/74931|29521/68394|−2756|−6537|YES|

**Base2: 8/8 matched joint CZ+depth wins**, median paired ΔCZ **−3717.5**, median paired Δdepth **−9389**. Smallest savings 2747 CZ and 6537 depth. Among the tested optimized layouts, min sampled CZ **28528** and min sampled depth **65461** (different seeds).

### Cubic base8 public full block [8,29,1,1]

| Seed | Old CZ/depth | Selected CZ/depth | ΔCZ | Δdepth | Joint pass |
|---:|---:|---:|---:|---:|:---:|
|239|15872/37896|14607/34068|−1265|−3828|YES|
|647|16637/39185|15044/34881|−1593|−4304|YES|
|1453|15895/37669|15385/35470|−510|−2199|YES|
|3701|17390/40393|15173/35493|−2217|−4900|YES|
|6211|15722/37461|15073/34111|−649|−3350|YES|
|9421|16334/39446|15318/35452|−1016|−3994|YES|
|16673|17057/41267|14850/34467|−2207|−6800|YES|
|27191|16020/37359|14471/33951|−1549|−3408|YES|

**Cubic8: 8/8 matched joint CZ+depth wins**, median paired ΔCZ **−1407**, median paired Δdepth **−3911**. Smallest savings 510 CZ and 2199 depth. Min sampled selected CZ **14471**, min depth **33951** (same seed27191).

**Exact original historical 8776 anchor PASS**, confirming single-stage source/target comparability, separately excluded from full four-block scores: base2 old **7887 CZ/18221 depth**, selected **6871 CZ/16626 depth**; cube8 old **7802/18449**, selected **7315/16286**. These anchor circuits have **32** source logical qubits, not the new **35-qubit** block.

## Authentic original GitHub CI, preservation, and limitations

[Source original two-job four-block unitary+compiler CI **39512264987**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512264987) **2/2 SUCCESS**, every quantum-phase gate check and all32 target-native CPU compiler invocations successful. [Independent original JSON artifact audit/archive CI **39512588036**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512588036) **SUCCESS**: downloaded original JSONs without rerunning native compilers, checked exact 8-seed old/new numerical CZ/depth rows, original 8776 anchors, phase/ancilla proofs, immutable public source k map, all native CZ count_ops, distinct phase power schedules and unchanged device-gate failures. **Exact original receipt bytes were independently preserved**:
- [Original base2 full four-block source result](../results/ibm_shor35_four_power_sign_selector/qrr_n35_four_power_sign_source_base2.json)
- [Original cube8 full four-block source result](../results/ibm_shor35_four_power_sign_selector/qrr_n35_four_power_sign_source_base8.json)

**Predeclared robust integrated engineering gate: PASS for BOTH bases (8/8 and 8/8)**, genuine 35-qubit quantum gate source and target compiler, not naive per-multiplier extrapolation. **Immutable actual QPU feasibility: FAIL in all 32 layouts**. Even the smallest *sampled* cubic8 four-control block has **14471 native CZ and 33951 native depth**, ~**18.1×** CZ and **17.0×** depth the 800CZ/2000-depth preflight, BEFORE inverse QFT. Base2 selected min sampled CZ28528. **ZERO QPU calls/shots/free or paid runtime**; no physical device validation, complete Shor factor recovery, RSA/ML-KEM cryptanalysis or asymptotic algorithm theorem. The previous real Open Plan N15 qubit recycling hardware pilot remains separately preserved, not a new N35 success.

**Next:** Freeze and test a true inverse-QFT plus readout compilation to quantify the full 4-control logical factoring-readout circuit overhead, OR pursue a new phase-exact whole-block arithmetic decomposition targeting a much larger physical feasibility reduction, with matched seeds from the outset. No device job is warranted near this resource budget.
