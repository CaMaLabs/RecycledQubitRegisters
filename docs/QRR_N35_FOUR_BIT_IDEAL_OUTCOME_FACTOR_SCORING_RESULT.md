# VERIFIED — N35 four-bit WIDE ideal inverse-QFT probabilities and strict public factor recovery: base2 0% strict /37.5% bounded; cube8 50% strict /75% bounded but ALREADY factored classically

**Research lead and originating project: Chase Lunsford / CaMaLabs.** **Research date: 2026-10-20 local / 2026-10-21 UTC.** This document records a **completed exact IDEAL quantum-outcome calculation** on a 4-phase-qubit WIDE N35 phase-estimation readout circuit that had previously been **built and ISA-compiled but never executed on a physical quantum processor**. The result **is not physical QPU measurements**, not adaptive/recycled-phase hardware, not a quantum advantage, not a new factoring theorem and not evidence of practical RSA-scale cryptanalysis. **Absolutely ZERO quantum runtime and QPU jobs/shots** used in this study.

## Original verified full-QPE readout milestone — preserved as a distinct win

The [complete previous 35-qubit N35 FOUR-control public modular-power + work |1> + H^4 + inverse QFT + four terminal measurement circuit](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md), [original 2-arm native-target CPU experiment 39514204062](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39514204062), and [independent untouched original receipt audit 39514510289](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39514510289) are preserved unchanged. Each public base was tested with original positive arithmetic and a public sign-k selected source on all **1024=16 controls×64 work** input computational-basis values, exact quantum phase +1 and all 25 helper qubits cleaned; 16×16 true inverse QFT matrix and complete four terminal measurement instructions were verified. Both public bases recorded **8/8 seed-matched native CZ + depth reductions** using public static sign source selection; full chosen circuit still failed frozen physical gate **CZ≤800 and depth≤2000** by over an order of magnitude (smallest optimized cubic8 ~14,517 CZ / depth33,890), so **NO device jobs or quantum factoring shots** happened.

The earlier full 35-qubit experiment deliberately did **NOT** calculate quantum phase readout probabilities or score factors. The new mathematical outcome study addresses precisely that gap, not the physical hardware feasibility.

## Preregistered ideal distribution and public-only scoring

The protocol was committed **BEFORE new ideal outcome numbers** in [`QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_PREREG.md`](QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_PREREG.md), original git **`0602117b47808e9edcbc7e200c1f1e8d1c5f1a1e`**. It froze N=35, public base 2 and public cubic8, wide **four simultaneous phase qubits** (four-bit k=0..15), input work|1>, public controlled powers **[2,4,16,11]** vs **[8,29,1,1]** (two cube8 publicly identity stages skipped), mathematically exact inverse QFT, all16 outcomes without postselection, strict and bounded continued-fraction classical factor tests and classical precheck + uniform-k baselines. It expressly forbids using factored N or the true group period in **candidate generation or distribution calculation**, and forbids physical QPU/IBM runtime access.

## Reverified 35-qubit gate source and independent ideal ten-qubit statevector

New source [`hardware/qrr_n35_four_bit_ideal_outcome_scoring.py`](../hardware/qrr_n35_four_bit_ideal_outcome_scoring.py) re-runs the previous **actual emitted Qiskit operator** source proof for both original and sign-selected 35-qubit four-control powers, **1024/1024** clean-input phase-gate cases PER variant PER base, with correct public multiplication, identity for invalid y>=35, all25 scratch qubits clean and actual final complex amplitude **+1**. It rechecks the original archived arithmetic selection, source gate histogram and stage schedule, the entire analytic **16×16 QFT†** and **H^4** state preparation and the four terminal measurement instructions. No 2^35 state vector is falsely claimed.

Given that strict verified clean-source map, the reachable initial |work1>|scratch0> subspace has EXACT ideal reduced **4+6=10 qubit** pre-IQFT state

`|ψ> = (1/4) Σ_{c=0}^{15} |c>|a^c mod35>`.

Thus, after the actual four-phase inverse QFT, the amplitude for phase outcome k and output work residue y is

`A[k,y] = (1/16) Σ_{c=0}^{15} [a^c mod35 = y] exp(−2πi kc/16)`,

and the phase readout distribution is `P(k) = Σ_{y=0}^{63} |A[k,y]|²`.

The experiment computed ALL **1024** complex amplitudes analytically and, in an INDEPENDENT Qiskit calculation, explicitly assembled the corresponding ten-qubit 1024-vector (Qiskit basis index **c+16y**) and applied the literal `QFTGate(4).inverse()` using `Statevector.evolve(...,qargs=[0,1,2,3])`. Every amplitude agreed within 1e−9 (**max absolute diff base2 9.77e−16, cube8 1.40e−15**). ∑P(k)=1 for both bases. The original and sign-selected implementations have the same ideal outcome distribution because they implement the same verified exact quantum unitary; their benefit is on compiled resource cost, NOT an artificial change of phase-estimation success.

## Entire FOUR-bit phase outcome probability and factor-scoring table

A strict recovery policy uses **ordinary continued-fraction convergent denominators q≥2, q≤16** of public fraction k/16, never k=0 or q=1, and tries **r=q only**. Candidate r must be EVEN, `a^r mod35=1` tested with PUBLIC modular exponentiation, and standard `gcd(a^(r/2)±1,35)` must return a proper factor 1<g<35. An explicitly **more permissive bounded** policy tries r=mq for public m=1,2,3,4 (r≤64) with those same tests. It is **NOT ordinary strict Shor recovery**, and uses extra classical modular-exponent search; it never uses a known order, hidden factor or classical predictor when selecting q or r. No actual quantum outcomes were sampled.

| Four-bit outcome k | Base2 ideal P(k) | Base2 strict / bounded success | Cubic8 ideal P(k) | Cubic8 strict / bounded success |
|---:|---:|:---:|---:|:---:|
| 0 | 3/32 | No / No | **1/4** | No / No |
| 1 | 1/16 | No / No | 0 | No / No |
| 2 | 1/32 | No / No | 0 | No / No |
| 3 | 1/16 | No / No | 0 | No / Yes | 
| 4 | 3/32 | No / **Yes** | **1/4** | **Yes / Yes** |
| 5 | 1/16 | No / **Yes** | 0 | No / Yes |
| 6 | 1/32 | No / **Yes** | 0 | No / Yes |
| 7 | 1/16 | No / No | 0 | No / Yes |
| 8 | 3/32 | No / No | **1/4** | No / **Yes** |
| 9 | 1/16 | No / No | 0 | No / Yes |
| 10 | 1/32 | No / **Yes** | 0 | No / Yes |
| 11 | 1/16 | No / **Yes** | 0 | No / Yes |
| 12 | 3/32 | No / **Yes** | **1/4** | **Yes / Yes** |
| 13 | 1/16 | No / No | 0 | No / Yes |
| 14 | 1/32 | No / No | 0 | No / No |
| 15 | 1/16 | No / No | 0 | No / No |

*Cube8 entries shown as 0 off k∈{0,4,8,12} are mathematically exact zeros in the ideal model; numerical floating point receipts store residual errors around 10^−31. The scoring results for zero-probability k are included honestly but contribute no weighted success probability. Original JSON receipts include all sixteen non-postselected k values, exact raw numerical probabilities, candidates, GCDs and first proper factor witnesses.*

### Preregistered probability scoring results

| Ideal one-readout score (NOT actual QPU success) | Public base2 | Public cubic8 |
|---|---:|---:|
| Mathematical order (VALIDATION AFTER scoring; never selection) | 12 | 4 |
| Strict CF proper-factor recovery P_success | **0%** | **50%** |
| Extra-classical-search CF bounded m≤4 P_success | **37.5%** | **75%** |
| **Uniform random k comparator**, strict policy | **0%** | **12.5%** |
| Uniform random k comparator, bounded policy | **37.5%** | **68.75%** |
| **Uninformative k=0 probability** | 9.375% | 25% |
| PUBLIC trivial GCD(a−1,35) | 1 | **7 (proper factor!)** |
| PUBLIC GCD(a+1,35) | 1 | 1 |
| First-four-even-exponent PUBLIC test r=2,4,6,8 factors N | No | **YES** |
| Physically feasible full QFT circuit native CZ≤800, depth≤2000 | **NO** | **NO** |
| Actual QPU measurement shots | 0 | 0 |

**Important base2 negative:** Exact ordinary CF denominators available with only four control bits yield **zero** strict accepted factor outcomes under the frozen stated policy. Its permissive 37.5% heuristic success rate equals the **37.5% uniform randomly selected k baseline** under that same classical bounded search. Thus this policy shows **NO observed ideal-distribution enrichment for this base**, even in a noise-free mathematical calculation. A longer phase register or properly structured iterative recycled phase estimation would be required to learn more about factor recovery.

**Important cubic8 caveat:** Its exact period4 results in ideal k=0,4,8,12 each at 25%; strict accepted k4 and k12 imply 50%; bounded m≤4 also accepts k8 (75%). BUT **gcd(8−1,35) = gcd(7,35)=7** is an immediate proper factor from PUBLIC input, before even constructing a circuit. Also the frozen four-even-exponent classical scan accepts r=4 and recovers a factor without Fourier interference. Consequently this toy base cannot support an honest *quantum advantage or new factoring power* interpretation, even if ideal readout probabilities favor it versus uniform k. The standard identity `ord(a³)=ord(a)/gcd(ord(a),3)` and odd-cube half-order GCD witness invariance remain standard known number theory, not a new theorem.

### Provenance and exact original receipts

[**Original 2/2 Qiskit source / IDEAL distribution run 39539165648**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39539165648) **SUCCESS**, both completed source 1024+1024 exact complex-phase checks and 1024 independent-statevector-amplitude comparisons, strict+bounded public CF scoring, uniform-k + classical GCD baselines, saved complete 16-row outputs. No IBM backend target read, token, Sampler/Estimator, hardware action, free or paid runtime in this new experiment.

[**Independent unchanged-source-artifact audit and preservation CI 39539345288**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39539345288) **SUCCESS**, downloaded the original two source-run JSON artifacts without rerunning science or tuning any outcome model, independently calculated every P(k) via work-state interference sum, verified all16 strict/bounded proper factor witness candidates, both initial GCD baselines, normalized QFT probabilities, exact archived readout source and new complex-amplitude checks, and committed ORIGINAL unmodified numerical JSON receipts:

- [Original base2 ideal fourbit output and exact classical score](../results/n35_ideal_iqft_outcome/qrr_n35_ideal_iqft_outcomes_base2.json)
- [Original cubic8 ideal fourbit output and exact classical score](../results/n35_ideal_iqft_outcome/qrr_n35_ideal_iqft_outcomes_base8.json)

These are new ideal distribution calculations, not statistically estimated rates or real-device samples.

## Conclusion and next falsifiable task

The previously preserved 35-qubit four-phase inverse-QFT full-source circuit is IDEALLY CORRECT and source-optimizer gate gains survive readout compilation, but **four bits do not reliably yield usable factor data for public base2 under strict CF**. Cubic8 shows a cleaner short-period distribution yet its factor is already publicly available by trivial GCD. **The frozen hardware gate still FAILS** (even best native optimized full readout ~14,517 CZ/depth33,890), so no QPU run was or should be submitted. Preserve the genuine N15 Open Plan phase-recycling QPU milestone separately, and do not conflate it with the four-bit-wide N35 study.

**Next question:** Evaluate **precisely preregistered larger phase precision** (e.g. six to eight phase bits) as ideal reduced-state/analytical output probabilities with the **same bounded PUBLIC classical factor-recovery policy**, including absolute resource forecasts and perhaps a true **iterative/recycled phase-control implementation**, not merely calling a wide model recycled. Better controls on public classical factor-prechecks and nontrivial fresh semiprimes are essential before making any advantage claim. No automatic real QPU submission.
