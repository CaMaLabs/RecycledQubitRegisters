# VERIFIED — N35 public constant-specific prefix carry: deeper arithmetic native CZ reductions with full ideal-gate proof; QPU feasibility FAILS

**Research lead / originating program: Chase Lunsford / CaMaLabs.** Research time: October 16, 2026 Pacific; GitHub Actions results October 17 UTC. **ZERO real QPU jobs, ZERO free or paid IBM Runtime; all IBM Fez "native" gate/depth numbers are authenticated TARGET COMPILATION ON A CPU, NOT quantum device execution.**

## Preserved history, frozen hypothesis and data provenance

The existing [real IBM Fez Open Plan N15 Shor factor-recovery experiment](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) established small-modulus phase recycling on true hardware, but cannot demonstrate cubic preconditioning because the N15 base2 order=4 is unchanged by cube. The [N35 full-register public-permutation compilation](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md) gave ~61% lower native CZ/depth for N35 base2→cube8 order12→4 but BOTH original and cube models failed frozen N35 Open Plan hardware feasibility <=800CZ/<=2000depth. A more algebraically general nested-QFT-adder modular arithmetic lowering was worse, up to 1.7 million native CZ; the subsequent [primitive Toffoli single-multiplier](QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_RESULT.md) passed 128/128 exact emitted-gate ideal computational-basis cases but used 27,929/29,822 CZ for N35 single multipliers base2/cube8.

The immediate [public cached-enable multiplier](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_RESULT.md) reduced these to **base2 CZ18,719 depth42,335**, **cube8 CZ19,912 depth44,381**, each with 32 logical qubits, 128/128 gate-level cases with all 25 auxiliaries cleaned, but still failed the real-QPU native limits. Baselines and raw original receipts remain unchanged.

The current **ONE fixed combined-variant** protocol is preregistered in [`QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_PREREG.md`](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_PREREG.md), git commit **`ca7d523a1c2b0e752d7c69b5c73a416964a11622`**, before native scoring. Fixed public N=35, seed a=2 and cube8, 1 full 6-bit residue controlled multiplier per arm, all X/CX/CCX ideal reversible gates, no private factors, order, precomputed orbit or oracle, IBM `ibm_fez` read-only native target, Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, optimization level1, seed8776, no layout/seed search and NO Sampler/Estimator/Runtime submission.

## New code: direct low-prefix carry and public comparison shortening

[Original single new candidate source](../hardware/qrr_n35_public_prefix_carry_single_modmul.py) *imports and retains* the prior cached-enable `verified.build` constructor and old `reference.predicate` and `reference.multi_x`, and changes ONLY modular-constant addition and unsigned comparator length:

1. Public constant `k` in controlled `+k mod2^w`: go **highest output bit to lowest**. For bit `j`, source lower j bits are still original and unchanged; the output XOR toggle is `k_j XOR [x_low_j >= 2^j - (k mod2^j)]` (carry predicate omitted if low public k=0). Implement the carry predicate using the existing proven clean comparator with target bit j as its XOR destination, plus a single controlled flip if k_j=1. This replaces repeatedly applying controlled ripple increments for each set bit of k. The new circuit is reversible, leaves all predicate carry and scratch ancillas zero between bit updates, and does NOT inject a precomputed true order.
2. For any threshold `t=2^s*u` with `u` odd, `x>=t` iff `x>>s>=u`, and `x<t` iff `x>>s<u`. Shorten the compared register and corresponding clean comparator carry ancillas by the publicly computed trailing zeros s. Apply the same to old modular wrap comparison, output wrap-flag uncomputation and new per-output-bit carry predicates.
3. The old modular correction protocol (wrap flag x>=N-k, conditional +k mod64, conditional -35 mod64 on wrap, uncompute flag from final x<k) is preserved. The verified cached `active=phase&valid` and `enable=active&work[i]` ancilla control latches, controlled work/acc swap and inverse-uncompute, validity restriction y<N remain unchanged. All 25 ancillas (6 accumulator, 2 flags, 6 carry, 9 scratch and 2 cached enable latches) clean after a controlled modular multiply.

**Scientific scope:** This is a TWO-component **combined** engineering ablation; the data cannot independently apportion savings between direct bit-carry rewriting and trailing-zero predicate shortening without new separate controls. The logic uses the public constant and modulus only, no precomputed 12-state orbit, hidden private factors or true multiplicative order. We do not claim scalable factoring advantage based solely on compiler costs.

## Actual gate-level semantic verification

**Before native compilation**, the experiment performs an exhaustive simulation of the ACTUAL Qiskit-emitted **X/CX/CCX gate instruction stream**, not just a separate arithmetic shadow implementation:

- **16 distinct public modular addition constants** `[2,4,8,11,13,16,17,19,23,26,27,29,31,32,33,34]` from the 6 forward and 6 inverse modular weighted adds for a=2 and a=8. For every k, all 35 valid target x with enable ON and all 64 target x with enable OFF were validated against the exact `+k mod35` value, every 6-bit invalid OFF input left untouched and ALL wrap/carry/scratch helpers reset. **16×99=1,584 per-arm modular-add gate-level cases PASS**.
- Build full N35 controlled multiplication of a2 and cube8 over the complete six-bit work register. Every `c∈{0,1}` and y∈[0,63] =**128/128 cases PER base** passed the exact intended public full-residue transformation, unchanged control, correct identity on y>=35, and **all 25 clean auxiliaries**. Since the emitted source is a permutation of computational basis states made solely from X/CX/CCX, this ideal mapping extends coherently to superpositions of the tested `aux=0` input subspace; **not** a proof of noisy hardware fidelity, or of the action for arbitrary garbage-bearing auxiliaries.
- The independent test includes **more than 3,424 total gate-instruction-level cases** across the two base jobs (`2×(1584+128)=3424`). The prior source gates/proofs remain untouched.

## Original CI and immutably preserved outputs

[Original independent native Fez target compile and gate-proof workflow **39006320227**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006320227) **2/2 SUCCESS**, a2 and cube8 (each produced 1584 subroutine tests and 128 full-control tests). There were **no quantum runtime method calls** and no device jobs.

[Independent original-source-artifact auditing and preservation workflow **39006395142**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39006395142) **SUCCESS**. It downloaded the two original JSON artifacts without re-running science, checked prereg/source revision, true public base, exact 16 constants and 1584+128 tests, unchanged frozen baseline JSON on the same Qiskit backend/seed, genuine CCX/CX/X source gates, native counts, correct observed engineering criterion and FAILED hardware feasibility; committed **unchanged original receipts**:

- [base2 original JSON](../results/ibm_shor35_public_prefix_carry/qrr_n35_public_prefix_carry_base2.json)
- [cube8 original JSON](../results/ibm_shor35_public_prefix_carry/qrr_n35_public_prefix_carry_base8.json)

No third-party code/data borrowed and no API key emitted to logs.

## Results: ONE controlled multiplier, not a complete factoring circuit

| Metric, N35 one multiplier | Previous cached base2 | **New base2** | Previous cached cube8 | **New cube8** |
|---|---:|---:|---:|---:|
| Unique mod-add constants independently gate-tested | not separately tested | **16** | not separately tested | **16** |
| Primitive mod-add ideal gate test cases | not separately tested | **1584/1584** | not separately tested | **1584/1584** |
| Full multiplier ideal gate test cases | 128/128 | **128/128** | 128/128 | **128/128** |
| Zeroed auxiliares (full multiplier) | 25 | **25** | 25 | **25** |
| Application logical qubits | 32 | 32 | 32 | 32 |
| Primitive emitted X+CX+CCX count | **1536** | **1817** | **1578** | **1883** |
| Primitive CX | 445 | **1033** | 445 | **1077** |
| Primitive CCX | 1063 | **756** | 1105 | **778** |
| **Compiled native CZ (IBM Fez target)** | **18719** | **12517** | **19912** | **12680** |
| **Compiled native depth** | **42335** | **32312** | **44381** | **33138** |
| Frozen CZ<=800, depth<=2000 | FAIL | **FAIL** | FAIL | **FAIL** |
| Real IBM QPU jobs | 0 | **0** | 0 | **0** |

**Predeclared engineering PASS (both base arms):** base2 CZ `18719→12517` (**−33.13%**) and depth `42335→32312` (**−23.68%**); cube8 CZ `19912→12680` (**−36.32%**) and depth `44381→33138` (**−25.33%**). More primitive source gates overall reflect **far fewer expensive Toffoli CCX** but more CNOT CX; native compiler maps this into substantially fewer CZ/shorter depth. Counts are compile/layout/target dependent, NOT a measured physical-device runtime/fidelity speedup. The cube8 single multiplier is only about 1.3% more native CZ than base2 with this construction; in contrast, full four-round cubic benefit is tied to two public identity rounds, and was NOT tested on this new kernel.

**Predeclared hardware gate FAILED:** smallest compiled arm still has **12,517 CZ** and **32,312 depth**, roughly **15.65× CZ** and **16.16× depth** above the immutable N35 800-CZ/2000-depth heuristic, even before assembling the full four phase-bit multipliers/QFT circuit. Therefore: **NO REAL QPU RUN**; no free runtime consumed, no paid fallback. Every original positive and negative prior experiment remains separately preserved without upgrading conditional claims.

## Next move — not an automatic QPU submission

Before a whole four-bit stage, isolate the remaining dominant expensive controlled comparator and clean-vchain Toffoli cost. Consider separately preregistered A/B tests of (i) shortened wrap-comparator structures alone versus (ii) direct carry logic alone, (iii) shared carry factorization across the two modular-add passes, or (iv) actual in-place fixed-constant Toffoli adders. Preserve existing verified X/CX/CCX gate/ancilla tests. Only consider a four-round public QPE experiment after a dedicated one-kernel resource gate becomes credible; do not claim RSA cryptanalysis, a new theorem or practical quantum advantage from toy public N35.
