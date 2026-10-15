# Dark Star scalable-arithmetic population holdout: completed result

Date: 2026-10-14  
Research lead: Chase Lunsford / CaMaLabs

## Receipt and provenance

- Preregistered protocol: `docs/DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_PREREG.md`
- Implementation: `hardware/dark_star_scalable_resource_population_holdout.py`
- Complete 96-row output: `results/dark_star_ptp/dark_star_scalable_resource_population_holdout.json`
- Independently regenerated three-scout baseline: `results/dark_star_ptp/dark_star_recycled_scalable_arithmetic_audit.json`
- Passing workflow: [QRR zero-QPU holdout, run 38663133662](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38663133662)

The population selection and endpoints were committed before the result-producing workflow. No IBM service or QPU submission was used. The run passed assertions for all 96 selected rows (16 trigger and 16 control per odd prime), both JSON receipts, and zero order-identity/witness-preservation violations. A separate local arithmetic evaluator reproduced the three scout CCX results and matched these six population cells to the displayed precision.

## Frozen design

- Squarefree distinct-prime semiprimes `N=pq`, `65536 <= N <= 131071`, `p,q >= 11`, excluding `ell | N`.
- Odd-power exponents `ell in {3,5,7}`.
- **Trigger:** `N mod ell` not in `{0,1}`; **control:** `N mod ell == 1`.
- Six groups of 16 `N` values selected by frozen public-`N` SHA-256 ranking.
- Fixed deterministic rotated public coprime-base pool; the same `b=a^ell mod N` transform applied in BOTH groups.
- Eligible only if baseline/transformed witnesses are factor-capable, the exact order identity and witness preservation pass, and neither base has the specified **public power-of-two repeated-squaring/GCD shortcut**.
- Staged QPE: precision 4, 6, ..., 34 bits; four ideal nearest-bin shots per stage; strict continued-fraction/order verification model.
- Resource counter mirrors the generic reusable-clean-ancilla polynomial reversible modular-arithmetic construction. This is **logical CCX/Toffoli** cost, not hardware-native CZ, fault-tolerant physical cost, runtime, or measured fidelity.

The baseline/transformed hidden orders and prime factors are validation-only; they are not used to pick bases, preselect cases, or simplify arithmetic circuits.

## Primary results: **do not pool unlike ell groups**

Aggregate ratio is **sum of transformed expected staged arithmetic CCX / sum of matched baseline expected staged arithmetic CCX**, on **eligible** rows only. Below 1 indicates savings. Group controls are *not* zero-treatment placebos: control rows receive the same odd-power transform and can have order reductions.

| ell | group | eligible / selected | aggregate CCX T/B | CCX reduction | median row T/B | improved / tied / worsened | aggregate phase-round T/B |
|---:|---|---:|---:|---:|---:|---:|---|---:|
| 3 | trigger | 11 / 16 | **0.799035** | **20.10%** | 0.783406 | 10 / 0 / 1 | 0.786341 |
| 3 | control | 5 / 16 | 0.869060 | 13.09% | 0.764800 | 3 / 0 / 2 | 0.858976 |
| 5 | trigger | 6 / 16 | 0.906479 | 9.35% | **1.022762** | 2 / 0 / 4 | 0.885887 |
| 5 | control | 9 / 16 | **0.844764** | **15.52%** | 0.701755 | 6 / 0 / 3 | 0.830849 |
| 7 | trigger | 9 / 16 | 0.971187 | 2.88% | **1.007951** | 3 / 0 / 6 | 0.960255 |
| 7 | control | 11 / 16 | 0.983586 | 1.64% | **1.019713** | 1 / 0 / 10 | 0.967691 |

Of the 96 selected semiprimes, **51 survive the public classical-shortcut and factor-witness guardrails**. In those eligible rows, order reductions occur:

- ell=3: trigger **10/11**; control **3/5**;
- ell=5: trigger **2/6**; control **5/9**;
- ell=7: trigger **1/9**; control **1/11**.

### Frozen trigger-vs-control criterion

- **ell=3 passes:** trigger aggregate CCX ratio 0.7990 < control 0.8691; gap 0.0700. The trigger effect is stronger, though small eligible groups limit confidence.
- **ell=5 fails:** trigger 0.9065 > control 0.8448; gap -0.0617. Despite some aggregate savings, this is **not** positive trigger-enrichment evidence on the frozen panel.
- **ell=7 passes the narrow directional criterion:** trigger 0.9712 < control 0.9836; gap 0.0124. The effect is weak, and **6/9 eligible trigger rows worsen**, so it is not a convincing general per-row resource gain.

The selected three scouts were favorable examples. Their 43–69% CCX savings must **not** be presented as population-average savings. The broader panel reveals substantial heterogeneity, in particular the lack of support for ell=5 trigger enrichment.

## Mechanism decomposition

The aggregate `CCX T/B` ratio factors algebraically into `phase-round T/B` times the corresponding `CCX-per-phase-round T/B` ratio, evaluated by the same aggregate sums.

| ell | group | phase-round T/B | CCX-per-round T/B | CCX T/B |
|---:|---|---:|---:|---:|
| 3 | trigger | 0.786341 | **1.016142** | 0.799035 |
| 3 | control | 0.858976 | 1.011739 | 0.869060 |
| 5 | trigger | 0.885887 | **1.023245** | 0.906479 |
| 5 | control | 0.830849 | 1.016747 | 0.844764 |
| 7 | trigger | 0.960255 | **1.011385** | 0.971187 |
| 7 | control | 0.967691 | 1.016425 | 0.983586 |

No group derives its aggregate savings from intrinsically cheaper transformed modular multiplication. The transformed expected arithmetic cost *per executed phase round* is slightly higher in all six cells. Where savings exist they are driven by reduced staged QPE work from earlier stopping.

## Independent recycling-width result

All selected `N` values have 17 bits, so the frozen generic clean-ancilla model uses:

- work: 17; accumulator: 18; reduction flag: 1; clean MCX scratch: 18;
- total coherent arithmetic workspace **54 qubits**, retained in both architectures;
- textbook cap: 34 phase bits;
- matched conventional wide peak: **54 + 34 = 88 logical qubits**;
- matched recycled peak: **54 + 1 = 55 logical qubits**;
- phase recycling therefore reduces peak logical width **37.50%**.

This width saving is independent of which Dark Star transform is used. Dark Star does **not** lower the fixed precision cap or coherent arithmetic workspace. The combined baseline-wide vs transformed-recycled configuration can be reported only after keeping the two component effects separate: 88 -> 55 peak logical qubits from recycling, and the applicable group CCX ratio from earlier Dark Star stopping.

## Caveats, limitations, and next falsification

1. This is a **deterministically sampled 17-bit semiprime** panel, not RSA-scale arithmetic execution or a general population theorem. Eligible group sizes are as small as five. No new significance threshold was invented post hoc.
2. The `N mod ell == 1` control can still have `ell | ord_N(a)`; it is a comparator group, not a placebo with zero opportunity for improvement.
3. Public classical-shortcut exclusion covers the stated power-of-two/GCD audit, **not every conceivable classical factoring or order-finding procedure**, including stronger bounded Pollard-p-1-style preprocessing.
4. The staged success probabilities are from a nearest-bin ideal-QPE scorer using validation orders to test the public-verification-equivalent denominator condition. Real noisy QPE and fully explicit factor-producing continued-fraction verification are further gates.
5. Differences in CCX from changed modular constants persist even when the hidden order is unchanged; therefore report improve/tie/worsen statistics and the per-phase diagnostic, not only aggregate ratios.
6. No measured device speed, hardware fidelity, calibrated Phoenix coupling, asymptotic improvement, or RSA-2048 attack is established.

**Stronger next test:** preregister a fresh independent broader semiprime range with frozen public bases, more eligible cases per ell/group, a bounded *public classical preprocessing* cost baseline (including Pollard-p-1 family), exact factor-producing continued-fraction checks, and a no-transform selector option. Evaluate the complete *public decision policy* rather than selected favorable transforms. Preserve negative as well as positive outcomes.
