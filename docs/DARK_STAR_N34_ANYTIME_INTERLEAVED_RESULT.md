# Dark Star: fresh N34 anytime resumable Brent + PTP midpoint scheduling — original result

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-29. **Prospective primary anytime merit gate: FAIL. Prospective secondary middle-vs-far discipline gate: FAIL.** This was a real, freshly selected, full CPU classical-factoring experiment with an algebraically safe PTP midpoint sieve and **statefully resumed** Brent, not an unimplemented controller idea. **All 24 N34 synthetic semiprimes correctly factored under all six complete algorithms; 24-case exact pause-versus-uninterrupted state/operation verification passed. Zero IBM QPU, paid/free Runtime or hardware claims.**

## Independent preregistration and frozen data chronology

1. [Public-only exact seven-arm algorithm and precommitted primary/secondary pass criteria](DARK_STAR_N34_ANYTIME_INTERLEAVED_PREREG.md) committed **before** sample selection. Original [true stateful Brent/QR scheduler](../integrations/darkstar_hybrid/darkstar_n34_anytime_scheduler.py), immutable source Git blob SHA **`afdc1e69a94ebfdd7d73fd2b6d5ada6d8c589753`**. A holds a *single* c=1,y=2 Brent state across interrupted PTP QR work, so previous modular squarings and batched-GCD state are not thrown away or rerun. No oracle or hidden factored p,q used.
2. Separate successful GitHub Actions [**41016927212** — N34 cohort freeze plus pre-freeze unit and pause-resume tests](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41016927212), [original frozen public SHA manifest](../results/dark_star_unified/darkstar_n34_anytime_public_frozen_manifest.json). Exactly **24 original, distinct 34-bit semiprimes**, 8 from each prime-constructed factor-separation stratum (near true Fermat midpoint D=0–8, middle D=64–640, far D=4096–16384), synthetic candidate frames **801,218 / 4,630,744 / 16,555,967**, ranked by SHA `DARKSTAR-N34-ANYTIME-20261029|stratum|N`. Canonical public 24-row SHA256 **`b0ff1c6cc46e5db8d3e5ff8c841c9b01b40e027646e4734d43cb7665afa68bd2`**. Synthetic p/q are for constructing and **after-timing validating** the research groups ONLY; they and true D were not included in public algorithm inputs. The fixed source code and prereg pass thresholds preceded this sample.
3. Independent successfully completed GitHub Actions [**41017105426** — original complete scoring, tests, strict evidence verification and archive](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41017105426). [Original scorer](../integrations/darkstar_hybrid/darkstar_n34_anytime_holdout.py), [state-machine/factor-safety tests](../integrations/darkstar_hybrid/test_darkstar_n34_anytime_scheduler.py), [FULL unmodified original machine result JSON with all per-case stage traces, all original operation costs, seven arms, nine rotated timing repeats, exact synthetic truth and rho parity certificates](../results/dark_star_unified/darkstar_n34_anytime_original_24_result.json). All baseline factor recovery and checksum checks succeeded; positive and negative outcomes retained.

## Fixed public algorithms actually compared

- **B:** strong standalone deterministic Brent with one full c=1,seed2,1024-squaring stream, then if necessary separate c=3,seed3,512-squaring stream; complete conventional wheel210 as final fallback.
- **F:** eight plain Fermat x-midpoints before the identical B.
- **Q:** eight plain Fermat steps, full safe PTP QR midpoint scan offsets +8..+639 (at most 64 exact square roots) including fresh public mask construction and all modular membership checks, then identical B.
- **A anytime:** eight Fermat x-midpoints; **resumable Brent c1 to 96**, QR offsets +8..+71; **same c1 state to 384**, QR offsets +72..+199; **same c1 state to 1024**, QR offsets +200..+639, then c3 and complete wheel fallback when needed. All execution halts on verified factor and charges everything already done. Total QR root cap 64 and c1/c3 budgets 1024/512. These are fixed checkpoints based on actual work performed, **not secret factor-distance estimates**.
- **W**, **L**: independent complete conventional wheel210 and PTP LFK searches. **M**: bounded plain Fermat640 (can be unresolved), diagnostic only.

**All six complete algorithms A, B, F, Q, W, L factored all 24 original N**. Independently the resumed and uninterrupted Brent state produced exactly identical factors, modular-squaring/products/GCD counts, completion phase and budget respect on **all 24 original numbers for both c=1 and c=3 streams**. The state machine does not manufacture or erase a factoring advantage from restarting already paid work. All methods use public N only; grouping labels and p/q are validation-only.

## Original fixed gates — both failed

| Synthetic construction stratum | Anytime A faster than strong Brent B | A faster than full-PTP Q | A faster than Fermat+Brent F | Median per-case A/B | Median per-case A/Q |
|---|---:|---:|---:|---:|---:|
| Near D=0–8 (8 original cases) | **8/8** | **0/8** | **2/8** | **0.0273** | **1.3445** |
| Middle D=64–640 (8 cases) | **2/8** | **0/8** | **3/8** | **1.2184** | **3.0469** |
| Far D=4096–16384 (8 cases) | **0/8** | **8/8** | **0/8** | **1.2879** | **0.7957** |
| **All 24** | **10/24** | **8/24** | **5/24** | — | — |

**PRIMARY gate failed on all three required counts:** prereg required A>B on at least **15/24**, A>Q at least **15/24**, and A>F at least **13/24**. Actual **10/24, 8/24, 5/24**.

**SECONDARY discipline gate also failed:** middle A>B required ≥6/8 (actual **2/8**); far A>Q required ≥6/8 (actual **8/8**, met); median far A/B must be ≤1.25 (actual **1.28787**, fails). Thus interleaving avoids the worst far-stratum full-QR overhead, but not enough to equal the cost of going directly to strong Brent.

### Why the anytime method lost

- **Near:** seven of eight actual A wins over Brent ended in the **first eight ordinary Fermat tests before any QR or rho work**; the eighth had D=8 just outside Fermat offsets 0..7, so A paid 96 Brent squarings then found the factor on the **first QR position**. This is predominantly a plain Fermat proximity advantage; A is faster than plain Fermat8+B on only **two of eight** due to small timing noise/overhead. It is not novel PTP mathematics.
- **Middle:** the deferred PTP check often costs more than running QR immediately and more than letting Brent run to completion. A solved **4/8 via QR**, **4/8 via resumed Brent**. Median A/Q **3.0469**: an unconditional PTP-first search can be significantly faster when the synthetic factors are moderately close, whereas the fixed checkpoints introduce extra Brent work before reaching their correct midpoint. Mid median A/B **1.2184**, losing six of eight; original PTP idea remains valid but this scheduler did not improve overall performance.
- **Far:** all eight A cases were solved by Brent; **zero** by QR. Because Brent receives a head start, A often avoids the long late QR scan, and A beats fullQR Q in **8/8**. Yet A still performed up to 192 midpoint-position probes before Brent succeeded, paying QR-mask and scan overhead. The median A/B ratio **1.2879** is still ~29% slower than Brent alone. On two cases the first c1 checkpoint already found the factor; the remaining QR work is paid only when needed; no stratum label leaked.
- Public quadratic-residue masks are mathematically safe and reduce expensive square roots, but neither QR candidate sparsity nor a fixed pause schedule establishes the needed cheap, reliable **public** choice of how long to search near the Fermat midpoint. High-level comparisons of code with different overhead must not be confused with asymptotic complexity improvement.

## Methodological limits and next hypothesis

This is a 34-bit three-stratum **synthetic population** whose group labels are derived from construction-only p/q; those labels are not available to the public factorization algorithm. No independent performance or generalization to arbitrary larger integers, RSA-scale keys, compiled native quantum circuits, or cryptographic asymptotic speedup established. Nine rotated/interleaved submillisecond Python timings can fluctuate; preserve all raw individual times and avoid overclaiming precise speed factors.

**Outcome:** legitimate successful implementation of a non-restarting rho+PTP anytime scheduler and exact factor recovery, but **both strong-preregistered end-to-end speed gates fail**. The next rigorous direction is *not* another speculative QR residue-density predictor: either discover a provable public structural signal that predicts a genuinely nearby factor-pair midpoint, or treat established strong Brent rho (with optional tiny Fermat-first precheck) as the default and continue the separate quantum arithmetic/circuit resource program. A new mathematical hypothesis should be written before committing more compute-heavy synthetic population tests. No QPU charges.
