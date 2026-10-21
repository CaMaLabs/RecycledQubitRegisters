# VERIFIED — N35 ideal 4/6/8-bit phase precision: base2 strict CF factor rate 0 → 11.48% → 29.26%; cube8 remains 50% and classically preempted

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Research date:** October 20, 2026 local (October 21 UTC). The six- and eight-bit outcomes below are **mathematical IDEAL no-noise quantum phase-estimation predictions**, cross-checked using two independent implementations of the exact QFT transform. **They are NOT actual emitted 6/8-bit arithmetic circuits, not ISA/native IBM Fez compilations, not physical device shots, not implementation of adaptive/recycled qubit controls, not real hardware factor recovery and NOT practical quantum or cryptographic advantage.** Absolutely **ZERO IBM QPU jobs, Open-plan free runtime, paid Runtime, backend reads or API token use** in this study.

## Previously achieved, verified wins retained intact

The earlier [35-qubit N35 four-WIDE-phase-bit public modular-power + H4 + actual inverse QFT/readout ISA milestone](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md) fully constructed both bases2 and public cube8, with six-bit work and 25 returned-clean ancilla qubits, verified original and sign-selected arithmetic on every control×work basis state (1,024 each variant per base), exact +1 quantum phase, correct public multiplication and invalid-residue identity. It measured CPU-native target resources and confirmed that the entire four-bit circuit **failed** the immutable physical-device preflight (CZ≤800/depth≤2000), without running a QPU.

The follow-up [verified four-bit IDEAL full outcome and public factor scoring](QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_RESULT.md) gave proper-factor scoring base2 strict **0%**, extra bounded public candidate scan **37.5%**, and cube8 strict **50%**, bounded **75%**, with all 16 probabilities and classical GCD checks preserved in original immutable `results/n35_ideal_iqft_outcome/` receipts. It found the base2 bounded score was identical to a *uniform random 4-bit k* baseline, and cube8 already yielded proper public factor **7** via `gcd(8−1,35)`. Neither showed practical factoring advantage. The full four-bit native gate count remains too large. The [real IBM N15 Open Plan qubit-recycling pilot](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) remains a separate genuine toy QPU hardware record; it did NOT prove cubic order reduction.

## Freeze, controlled changes, and calculation boundaries

[Preregistered source protocol](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_PREREG.md), committed **`7f67f62c9b3ee7ee84eda43e2927a0a7430ec6da`** BEFORE the new b6/8 numbers, fixed public N=35, bases **2 and 8**, phase precision **b={4,6,8}**, exact outcome count M=2^b, full work residue0..63 (six bits), unchanged public CF and GCD scoring and no true-order or factor input to source or candidate generation. Old b4 is an original archived scoring **anchor**. The phase precision b6/8 is a forecast conditional on the correctness of an ideal unitary `|c>|1> → |c>|a^c mod35>` with every workspace qubit cleaned. We did **not** build b6/8 versions of the 35-qubit public modular-exponentiation circuit or check their individual actual source gates; the already implemented b4 circuit and a public mathematical ideal extension have DISTINCT scope.

[New reproducible source](../hardware/qrr_n35_ideal_phase_precision_4_6_8.py) FIRST re-ran the old true **35-qubit four-bit source** quantum `Operator` gate basis/complex-phase tests for both original and source-selected arithmetic, **1,024 + 1,024 per public base**, all 25 ancillas clean and output amplitude +1, plus the original inverse QFT/readout checks. It read and required old original b4 JSON results. No native compiler/backend methods were invoked.

For each b and base, the *assumed ideal reduced state*, supported by that b4 source and public extension, was represented in just **b phase +6 work** logical qubits, indexed `c+M*y`:

`|Psi> = M^(−1/2) Σ_{c=0}^{M−1} |c>|pow(a,c,35)>`.

After exact inverse Fourier transformation, each complex amplitude is

`A[k,y] = (1/M) Σ_{c=0}^{M−1} [pow(a,c,35)=y] exp(−2πi*k*c/M)`,

and readout probability `P(k)=Σ_{y=0}^{63} |A[k,y]|²`. **No period or private factor appears in either formula**, and every k including zero and all 64 six-bit work residues was retained. We calculated this two independently implemented ways: a literal Qiskit `Statevector.evolve(QFTGate(b).inverse(), qargs=[0...b−1])`, and a separate NumPy **complex FFT** along the phase axis, normalized identically. Required all **M×64 complex amplitudes** agree within1e−9, ∑P(k)=1 within1e−10, finite and nonnegative probabilities; observed maximum absolute complex differences in the **10^−17–10^−16 range**. The b4 full 16-row probabilities and both CF policy scores reproduced the preserved original results exactly within numerical tolerance, including strict 0% base2.

## Fixed PUBLIC-only classical factor scoring, not a known-order oracle

For each measured phase fraction **k/M**, `k=0` is a failure in both policies, never rescued with q=1 or trivial eigenphase guessing. For k>0 generate all exact *regular continued-fraction convergent denominators* q with 2≤q≤M from only k and M, deduplicate in order. The **strict** policy tests only r=q; the **permissive bounded** policy searches r=mq for m=1,2,3,4. Crucially, both keep **r≤64 even as M rises to 256**; the classical candidate search ceiling was not expanded to artificially improve the longer-precision results. For even public candidates r, only publicly computable `pow(a,r,35)==1` admits a factor attempt; compute ordinary `gcd(pow(a,r/2,35)−1,35)` and `gcd(pow(a,r/2,35)+1,35)`. A success requires a **proper factor**, with first public witness and all candidate attempts preserved. A bounded-multiple hit is EXTRA CLASSICAL SEARCH, not standard strict Shor recovery; false positives/zero-probability outcomes are all retained. A separate post-scoring descriptive check confirmed public group orders a2→12 and cube8→4 **only after all scoring**, without using either to choose q, r or source states.

**Classical controls:** `gcd(a−1,35)`, `gcd(a+1,35)`, fixed public even-exponent scan r=2,4,6,8, and a **uniform random k∈[0,M−1]** baseline scored by the same strict/bounded policies. N=35 is trivially classically factorable. In particular cube8 immediately leaks proper factor7 using `gcd(8−1,35)`; this classical shortcut preempts all claims of quantum speedup even if its ideal readout is sharp.

## Main results: all three widths, both bases, no excluded outcomes

| IDEAL one-readout scoring | Base2 4 bits | Base2 6 bits | Base2 8 bits | Cube8 4 bits | Cube8 6 bits | Cube8 8 bits |
|---|---:|---:|---:|---:|---:|---:|
| Phase outcomes (all counted) | 16 | 64 | 256 | 16 | 64 | 256 |
| **Strict CF public proper-factor probability** | **0%** | **11.4756%** | **29.2552%** | **50%** | **50%** | **50%** |
| **Bounded m≤4 CF proper-factor probability** | **37.5%** | **61.7593%** | **79.7151%** | **75%** | **75%** | **75%** |
| Uniform-k strict CF baseline | 0% | 3.125% | 5.46875% | 12.5% | 21.875% | 27.34375% |
| Uniform-k bounded CF baseline | 37.5% | 59.375% | 65.625% | 68.75% | 82.8125% | 89.453125% |
| **Ideal uninformative k=0 probability** | 9.375% | 8.3984375% | 8.3374023% | 25% | 25% | 25% |
| Public GCD(a−1,35) already reveals factor | NO | NO | NO | **YES, factor 7** | **YES** | **YES** |
| Real QPU execution / shots | 0 | 0 | 0 | 0 | 0 | 0 |

The exact source receipts retain **all 16+64+256=336 individual phase outcomes per base**, each non-postselected probability, rational k/M, CF candidates and gcd result. No device shot sampling or real quantum noise model was applied.

### Interpretation of the base2 precision gain

At four bits, **0% strict** full nontrivial proper-factor recovery was supported by the actual complete ideal four-bit source. At six and eight ideal forecast precision, it improves to **11.48%** and **29.26%**, respectively. This is a *real mathematical increase in ideal phase-readout information under the FIXED strict CF postprocessor*, and the comparison to uniform random k at the same precision (3.125%, 5.46875%) suggests the assumed QFT distribution carries a relevant periodicity signal. However, the bounded policy's additional search is a sizable classical contributor: e.g. b8 bounded 79.72% vs uniform random k 65.625%, and the four-bit bounded case had ZERO enrichment. These are NOT measured on hardware; N35 can be factored trivially and this is not RSA or general factoring speedup. The unchanged fixed candidate exponent ceiling r≤64 also shapes reported probabilities.

### Interpretation of public cubic8

Cube8's public four-bit power sequence **[8,29,1,1]** already exposes two identity rounds and an exact four-state order. The assumed ideal Fourier phase outcomes k=0,M/4,M/2,3M/4 each receive 25% of mass for b=4,6,8; increasing phase precision does NOT improve strict 50% or bounded 75% proper-factor recovery under the same public candidate rules. Indeed, at b8 the **uniform random k bounded** candidate policy alone succeeds **89.453%**, more often than the ideal QFT k distribution's 75%, further demonstrating how generous extra classical search can obscure useful interpretations. Most importantly **gcd(8−1,35)=7** before any quantum state preparation; no alleged quantum factoring advantage is justified.

## Resource-scope forecast: WIDE qubit counts only, NOT device gate counts

Using the old 6-work +25-clean-auxiliary architecture plus b simultaneously present WIDE phase qubits gives the following **hypothetical WIDE register widths and public controlled-power count**. The new b6/8 source circuits were NOT constructed, compiled, checked for noise or placed on a real backend; therefore we explicitly make **NO numeric Fez CZ/depth claims** for them.

| Public predicted ideal architecture | 4 WIDE phase bits (built previously) | 6 WIDE phase bits (UNBUILT) | 8 WIDE phase bits (UNBUILT) |
|---|---:|---:|---:|
| Total register qubits if extending same WIDE kernel | 35 | 37 | 39 |
| Mathematically possible phase readouts | 16 | 64 | 256 |
| Base2 nonidentity public controlled-power stages | 4 | 6 | 8 |
| Cube8 nonidentity public controlled-power stages | 2 | 2 | 2 |
| Extra QFT/readout implementation and native CZ/depth | Full four-bit previously measured (FAILS hardware gate) | **NOT COMPILED / UNKNOWN** | **NOT COMPILED / UNKNOWN** |
| True iterative one-recycled-phase-qubit execution | **NOT BUILT** | **NOT BUILT** | **NOT BUILT** |

The public stage lists base2 at 6 bits **[2,4,16,11,16,11]**, base2 at 8 bits **[2,4,16,11,16,11,16,11]**; cube8 at 6 bits **[8,29,1,1,1,1]**, at 8 bits **[8,29,1,1,1,1,1,1]**. Counts depend only on public `pow(a,2^i,35)`, **not use of a hidden true multiplicative order**. A true iterative recycled control register would require a separate validated mid-circuit measurement, reset, coherent work preservation and adaptive phase feedforward; it cannot be claimed merely by saying the wide prediction needs one phase qubit.

## Immutable primary JSON, original CI caveat and independent second auditor

[**Original two-base source science run 39540677040**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39540677040) passed both actual 35qubit four-bit power-source phase verifications and ALL 3×2 ideal phase precision QFT/FFT amplitude checks, produced complete original numerical JSONs with `status=ALL_4_6_8_IDEAL_QFT_AND_PUBLIC_SCORING_PROOFS_PASS` and `success=true`, and uploaded both original artifacts. **GitHub overall workflow is marked FAILURE because its POST-SCIENCE auditor read `strict_cf_ideal_success_probability` (lowercase `cf`) rather than the source's `strict_CF_ideal_success_probability` field**. This is a downstream auditor capitalization bug, not a failure of the 6/8-bit mathematical experiment; no numeric output, coefficient, scoring policy or circuit proof was changed, and the failed workflow remains visible.

[**Independent original-artifact audit and preservation CI 39540931690**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39540931690) **SUCCESS**: downloaded original two uploaded source-run JSONs without rerunning Qiskit or scoring. It independently reconstructed **every original k's** ideal `P(k)` from an explicit sum of work-register interference terms using Python `cmath` (rather than NumPy FFT or Qiskit QFT); verified all 672 k probability rows, repeated EVERY public continued-fraction q and all m≤4 exponents/witness gcd calls, both strict/bounded scores and uniform baselines, the original entire b4 probability and factor-policy rows, previously verified full 35q source proof and phase+1 flags, all public resource stage schedules, no backend/QPU access and exact old 4bit archive. It saved the **ORIGINAL UNMODIFIED JSON bytes**:

- [Original base2 4/6/8 ideal phase-precision JSON](../results/n35_ideal_phase_precision/qrr_n35_ideal_phase_precision_base2.json)
- [Original public cube8 4/6/8 ideal phase-precision JSON](../results/n35_ideal_phase_precision/qrr_n35_ideal_phase_precision_base8.json)

This complete original numerical table is a meaningful *ideal prediction and mathematical validation milestone*, but it adds NO device evidence and no proof of an actual 6/8-bit or recycled register implementation.

## Next falsifiable experiment

To meet the original **RecycledQubitRegisters** objective, preregister a **TRUE one-reused-phase-qubit semiclassical/iterative inverse-QFT implementation** with mid-circuit measurement, reset, classical feedforward and unchanged coherent six-bit work-register state, and require it to match the independently verified **ENTIRE** b4/b6/b8 ideal WIDE readout `P(k)` (all k, not just factor weighted scores) for both public bases within tight error. Validate branch-history-dependent phase feedforward and outcome-bit orientation before any live QPU or compiler claim. Such a CPU ideal dynamic-circuit proof would be evidence for faithful recycling semantics, **not** experimental physical feasibility or factor recovery. Keep the N35 public/classical shortcut caveat and the immutable preflight **CZ≤800 AND depth≤2000**; absolutely no IBM hardware use without separately scoped Open Plan and authorization.
