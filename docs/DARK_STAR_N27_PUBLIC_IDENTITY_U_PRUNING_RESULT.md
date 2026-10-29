# Dark Star public-identity controlled-modular-U pruning: separate exact N35 + fresh N27 audit

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-28. **Exact source-level pruning succeeds where public multipliers are 1; fresh N27 cohort is a verified zero-gain null.** Source CCX/CX/controlled-SWAP is a mathematical cost accounting model, not physical/native CZ, fidelity, depth or IBM QPU runtime. ZERO QPU / paid or free IBM Runtime.

## Proven mechanism

In modular order finding, each phase-control round uses an arithmetic multiplier `mult_k=a^(2^k) (mod N)`, which is **publicly computable** from N and a using successive modular squaring. If `mult_k==1`, the intended reversible modular multiplication `U_1:x→(1*x) modN` is the identity on the encoded modular residue space. Thus controlled-`U_1` is also identity and the whole controlled arithmetic block may be omitted without asking for the true multiplicative order, factors, hidden QPE phase, or a measured result.

The original repository [source-model counter](../hardware/dark_star_recycled_scalable_arithmetic_audit.py) used to charge the full generic clean-MCX multiplication even for public multiplier1. We added `stage_arithmetic_count_public_identity_pruned()` and `public_identity_rounds()` as **opt-in** helpers. Crucially `stage_arithmetic_count()` was left unchanged so **none of the original scientific CCX reports are silently rewritten**. The new counter copies all nonidentity modular multipliers' original source counts exactly; only public identity multipliers' full blocks are dropped. This requires no assertion that physical scratch can be removed or that native routing improves.

## Preregistered independent benchmark and provenance

- [Preregistration before experiments](DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md).
- [Same public SHA-frozen fresh N27 manifest, frozen in earlier run 40811162116](../results/dark_star_unified/unified_n27_restored_public_manifest.json): **`12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10`**, 12 public N/base cases. This audit does not use order/factors to select cases or modify the public cohort.
- [Independent source audit implementation](../hardware/dark_star_n27_public_identity_source_audit.py).
- The first audit [GitHub Actions run **40811424129**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811424129) **failed due ONLY to a Python module import entry-point error** (`python3 hardware/x.py` did not resolve the repo package). This was **not a quantum semantic or cost failure**, and no result was counted. The corrected workflow uses `python3 -m hardware.dark_star_n27_public_identity_source_audit` and successful [Actions run **40811595809**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811595809) verified and committed the unmodified original science receipt.
- [Full verified 152-row JSON, including original and optimized source counts](../results/dark_star_unified/unified_n27_public_identity_U_source_audit.json), saved on GitHub main; strict follow-up output check confirmed phase multiplier values and all three exact gate-count differences.

## Complete result

**152 independently checked phase-width/base/model configurations:** 32 predeclared historical anchors (N=35 plain2/cube8, N209 plain3/cube27, N713 plain19/cube and N15/21 additional small controls) and **120 new frozen N27 configurations** (12 N ×2 public bases plain/cube ×5 phase widths m=4,8,16,32,54). Plus **714 exhaustive small encoded-residue controlled-identity checks** for N15/21/35/77/209 at both control values.

| Subgroup | Source configurations | Configurations with nonzero identity savings | Exact source CCX saved |
|---|---:|---:|---:|
| Historical small anchors | 32 | **12** | **237,918** of 3,231,563 total source CCX (7.36% pooled, weighted by source work) |
| Fresh N27 plain bases | 60 | **0** | **0** of 1,491,733,696 source CCX |
| Fresh N27 cubed bases | 60 | **0** | **0** of 1,506,725,153 source CCX |
| **Total configurations** | **152** | **12** | **237,918**, all from historical toy anchors |

The expected N35 public-identity anchor is independently reproduced: at **N=35, a=8, phase bits m=4**, public multipliers are **[8,29,1,1]**, so phase rounds **k=2,3** are exact identities. Original generic structural source cost was **20,295 CCX**, with **9,828 CCX** mathematically unnecessary once those two identity U's are omitted. The remaining source cost is 10,467 CCX, approximately **48.4% fewer** *in this one 4-phase-bit source model case*. Original ideal factor recovery and phase distribution are unchanged by a correctly implemented no-op removal.

**Null result preserved:** None of the twelve newly frozen N27 bases (neither original nor cubed) attained `a^(2^k)≡1 modN` within the tested phase widths, so there was **zero** identity-U removal opportunity. It is wrong to claim that reintroducing this optimization made the new N27 factoring pipeline faster. In the separate [fresh N27 whole-factorization report](DARK_STAR_N27_FRESH_RESTORED_END_TO_END_RESULT.md), its source CCX figures remain unchanged after applying the opt-in identity calculation.

### Boundaries and important previous negatives

- This is a **mathematical identity on the intended modular-residue action**, plus exact source-operation accounting; a specific Qiskit arithmetic circuit's handling of out-of-range encoded states, ancilla cleanup, optimized native compilation, qubit routing, and hardware execution has not been established by this audit. Native semantics must be proven for the specific compiled circuit before submitting it.
- The earlier N35 [actual public identity-preflight arithmetic compile](../hardware/qrr_n35_public_modarith_identity_pruned_preflight.py) exists but is a **separate method**; the current CPU proof neither ran nor required a paid backend or QPU.
- Independently, earlier [N35 nine-idle-scratch removal](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md) reduced *source* width from **32→23**, yet **FAILED** a preregistered multi-seed native CZ/depth robustness gate. Identity-U removal does NOT imply width reduction, and idle-scratch removal does NOT imply reliable device-gate savings.
- No full circuit QPU performance, secure RSA-class key breaking, ML-KEM attack, or asymptotic algorithmic improvement is claimed.

**Conclusion:** The original technique is now represented in the unified source arithmetic model through an explicitly opt-in public-only counter. It can genuinely eliminate expensive redundant controlled-U blocks, but only when a small power-of-two exponent gives the public identity. The freshly frozen N27 null result and all past negative native results remain part of the record. Future work should route this exact public test into source construction when applicable, then measure compiled native-device resources independently, without confusing a source-gate reduction for a deployed physical benefit.
