# VERIFIED — N=35 public cube four-bit IBM Fez native compiler ablation; real-QPU gate FAILED

**Research lead / original concept: Chase Lunsford, CaMaLabs.** Study performed 2026-10-16 Pacific (2026-10-17 UTC). **No quantum job was submitted, no actual quantum device measurement or paid runtime consumed.** Native target metadata came from current IBM Fez backend; Qiskit circuits were compiled on GitHub CPU runner.

## Historical motivation and frozen protocol

The [first real Open Plan N=15 IBM Fez hardware result](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) measured actual factor production with recycled vs wide QPE (49/64 and 38/64 shots, respectively), but the N=15,a=2 order r=4 is unchanged by cubing. **That hardware test does NOT validate Dark Star cubic preconditioning.** We therefore preregistered [the present ZERO-QPU N=35 native compiler comparison](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_PREREG.md) in commit `bc14c01e87b3847b6edea9d633aeb6539a20bbad` before compilation.

N=35, seed a=2, public cube b=a³ mod 35=8, public trigger N mod 3=2. Mathematical validation orders 12→4 (factor 3 order stripping). The factor-producing half-order residue is invariant and publicly testable:

`2^6 mod 35 = 8^2 mod 35 = 29`,
`gcd(29−1,35)=7`, `gcd(29+1,35)=5`.

N=35 is classically factored by trial division. **Do not interpret this toy problem as a practical quantum factoring workload.** None of the exact true orders or private factors are provided to the circuit constructor.

## Actual source and measurement scope

- [Two independent zero-QPU GitHub Actions jobs **38995707019**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995707019): **2/2 SUCCESS**, one `recycled`, one `wide`, each compiling the same public baseline (2) and cube (8), using the same target Qiskit IBM Fez snapshot, `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, **4 phase bits, `1_clean_kg24` HLS, optimization 2, seed 8776**. Each job verified the full computational-basis modular permutation semantics before compilation, including the invalid-residue states. This is the repository's existing [public-only preconditioning source](../hardware/ibm_shor35_public_odd_power_preflight.py) plus [full residue direct transposition synthesis](../hardware/ibm_shor35_generic_permutation_direct_transposition.py).
- **No Sampler constructed or called**; no QPU/Estimator/Runtime job, Open Plan allowance not consumed. Reading live `ibm_fez` backend target for transpilation is NOT real-hardware execution. Both circuits compile to the backend device's **156-qubit representation**, not 156 application qubits: the logical circuit widths are 11 and 14, respectively.
- [Independent original-artifact receipt preservation CI **38995864891**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995864891): SUCCESS. Downloads both untouched original GitHub artifact JSONs, checks N/base/order/public construction, success on every four original compile rows, fixed architecture/synthesis/transpiler seeds, exact CZ and depth comparison math, and frozen hardware feasibility 800 CZ/2,000 depth, then preserves exact original receipts [recycled JSON](../results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_recycled.json) and [wide JSON](../results/ibm_shor35_generic_permutation/qrr_n35_cube_feasibility_4b_wide.json).
- Initial receipt-copy attempt [38995789970](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38995789970) failed due to artifact archive containing relative repository directories; only the independent preservation path selector was fixed, **no scientific experiments or compilation parameters were rerun or changed**.

## Full frozen comparison: native target synthesis

| Metric | Recycled base 2 | Recycled cube 8 | Wide base 2 | Wide cube 8 |
|---|---:|---:|---:|---:|
| Validation multiplicative order | 12 | **4** | 12 | **4** |
| Original circuit logical qubits | 11 | 11 | 14 | 14 |
| **Compiled native CZ gates** | **8455** | **3325** | **7946** | **3081** |
| **Compiled native depth** | **17108** | **6595** | **17193** | **6616** |
| 4-bit QPE round multipliers | 11,16,4,2 | 1,1,29,8 | 2,4,16,11 | 8,29,1,1 |
| Direct synthesized high-control MCX by QPE bit | 20,20,26,29 | **0,0,14,21** | 29,26,20,20 | **21,14,0,0** |
| Basis-change CNOTs by QPE bit | 62,62,74,88 | **0,0,60,78** | 88,74,62,62 | **78,60,0,0** |
| Dynamic mid-measure+reset | 4+4 | 4+4 | 0 | 0 |
| `if_else` conditional blocks | 6 | 6 | 0 | 0 |

The cube reduces **recycled CZ 8455→3325**, **60.674%**, and **recycled depth 17108→6595**, **61.451%**. It reduces **wide CZ 7946→3081**, **61.226%**, and **wide depth 17193→6616**, **61.519%**. The transformation does not reduce logical circuit width when the same number of phase bits is used. The 3× smaller order makes the high-index modular power rounds identity; the circuit synthesis entirely omits two formerly expensive modular-permutation rounds. The two remaining nontrivial full-residue controlled permutations still require thousands of CZ. These are backend-native compiler counts, **not measured gate-fidelity or speed**.

The user-relevant physical comparison is not a handpicked small sequence or hidden-order-assisted oracle circuit. It uses the full **64 basis-state** permutation `|x>→|b x mod35>` for valid residues and reversible extension elsewhere, generated from only public N/base. Unlike the prior [affine 12-state orbit compiler](../hardware/ibm_shor35_affine_matched.py), it does NOT know the 12-state orbit in circuit construction. However, full-table permutation synthesis is still exponential in modulus size and not asymptotically scalable generic modular arithmetic.

## Real-QPU feasibility gate: FAIL

The preregistration froze **at most 800 native CZ gates and depth 2000 for each of ALL FOUR compared circuits**, plus semantic and backend gates. None of the four cases passes. Even the best preconditioned wide circuit requires **3081 CZ and depth 6616**, about 3.85× and 3.31× the chosen heuristic limits. The best preconditioned recycled uses **3325 CZ and depth 6595**, about 4.16× and 3.30× the limits. These limits are conservative qualitative preflight tests, not a calculated physical fidelity cutoff. Actual fidelity/noise not simulated here, and 4 phase bits alone may be insufficient for fair order-12 factor extraction versus order-4.

**Frozen interpretation: native compilation mechanism improvement VERIFIED; proposed real-QPU submission of the generic full-residue compiler BLOCKED.** Do NOT relax the threshold post-result to claim feasibility, do NOT silently replace it with the cheaper order-specific affine orbit circuit, and do NOT run or charge Open Plan hardware for this failed-gate setup.

## Next scientific move

The credible next step is another **zero-QPU** architecture comparison with *true arithmetic-efficient public-only controlled modular multiplication* (clean-workspace reversible multiplier), or a separately preregistered minimal compiled-orbit demonstration that is explicitly described as a **compiled toy** and has matched plain/cube circuits, independent factor-producing test and strict Open Plan budget. Retain the current full-register negative cost feasibility as a transparent control against misleadingly favorable order-reduction models. More phase bits only increases this already infeasible generic full-table pipeline; focus on reducing multiplier synthesis cost first.

All earlier 22-bit classical factor baseline caveats and first real hardware N15 recycling milestone are unaffected.
