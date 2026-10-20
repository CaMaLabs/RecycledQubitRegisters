# VERIFIED NEGATIVE — fresh 23-bit high-precision full-outcome Dark Star public cube holdout

**Research lead and originating quantum resource program:** Chase Lunsford / CaMaLabs. **Date:** October 20, 2026 PDT. **Zero real IBM QPU jobs / zero paid or free quantum Runtime.** In-silico ideal-QPE abstract logical CCX only, with full-bin FFT to a fixed phase cap, analytic omitted-outcome tails and nominal 99% eigenphase-sampling confidence. NOT a practical factoring speedup.

## Prior records preserved rather than overwritten

The disjoint fresh [N22 precision full-outcome holdout](DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_RESULT.md) *passed* its frozen trigger ideal-model gate (3/4 N mod3=2 comparisons had bounded cube/plain upper<1; 1/4 factor-incapable), but 4/8 fresh Ns were factor-incapable and the entire public semiprime frame was classically factored. Previous N17/N18 ell5/ell7 residue-enrichment failures, N18 144-row classical-first failures, N22 full-outcome conservative primary failure, and the N22 selector-versus-unconditional-cube negative remain unchanged. The N35 8/8 and 7/8 fresh native CPU placement wins from a public sign-source-gate selector are an **independent circuit-compiler result**, NOT evidence of Dark Star order selection or hardware factoring.

This NEW study tests whether N22's 3/4 positive conditional trigger outcome survives a **different 23-bit modulus-size population**, without changing the ideal-phase estimator based on new outcomes.

## Frozen BEFORE any new N/order/model outcomes

- [Original pre-registered protocol](DARK_STAR_N23_FULL_OUTCOME_CUBE_PREREG.md), git commit **`d50c62b129702e56b35f7b6a6a4ecd69d6d5240f`**, before public sample generation.
- [Public-only SHA-rank / B31 selection](../hardware/dark_star_n23_full_outcome_public_manifest.py), commit **`4d069d6eed77feec2440b447ab27162c10544a91`**. The separate [public manifest FREEZE run 39509108244](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39509108244) **SUCCESS**, committed selected N/base and all public classical B31 candidates BEFORE private validation factors/orders or any ideal-QPE scoring.
- [Immutable frozen eight-N public manifest](../results/dark_star_ptp/dark_star_n23_full_outcome_public_manifest.json), canonical selected SHA256 **`fe345f8c762b58e545cdaeb5d6f28188aa546dfbaba049c9ac58e3b0b1181b37`**.
- [Scorer](../hardware/dark_star_n23_full_outcome_holdout.py), [eight-shard strict verifier](../hardware/analyze_dark_star_n23_full_outcome.py). **Original scoring [GitHub Actions 39509404291](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39509404291) SUCCESS**: all **eight out of eight** independently sharded calculations and the strict all-row integrity/preservation job completed successfully. No CPU evaluation branch selected by observed outcomes.
- [Full raw merged numerical data, classical factor receipts, all ideal-phase stage intervals](../results/dark_star_ptp/dark_star_n23_full_outcome_all_eight.json) and eight preserved original `results/dark_star_ptp/dark_star_n23_full_outcome_{trigger,control}_index{0,1,2,3}.json` receipts. The same frozen SHA is checked on every shard, all 8 unique public Ns, selected index, proper classical factors, exact public witness counts, validation order identity and 22 full phase stages.

The synthetic sample is **23-bit distinct-prime squarefree semiprimes**, 2^22≤N<2^23, p<q primes≥11, with N%3 trigger=2 or control=1. Select first four B31-unresolved Ns per group in public SHA256 order and a separately hashed first coprime public base from the fixed eleven-prime pool. No true order, prime-factor value, ideal quantum effect or model success can enter ranking, policy, or replacement decisions.

## Classical first: all 21 publicly screened semiprimes are solvable without QPU

| Public-N group | Screened by public B31 | Classically factored at B31 | Selected B31-unsolved for ideal model | Subsequently factored by public B47/rho/trial |
|---|---:|---:|---:|---:|
| Trigger (N mod3=2) | 14 | 10 | 4 | **4/4** |
| Control (N mod3=1) | 7 | 3 | 4 | **4/4** |
| **Total** | **21** | **13** | **8** | **8/8** |

Selected eight all receive the frozen public B47 Pollard p−1, fixed two-seed/64-step Floyd rho, then trial-prime fallback when necessary. All eight yield proper classical factors. The public GCD/pow/CF-good-denominator certificate generation used by the simulator may itself reveal factors and includes millions of public modular operations; this is expressly an **offline classical evaluation aid**, not a free practical quantum post-processing step. Its primitive and CPU ledgers are in the row JSON. The fixed public B31 survivors are **not independent draws from all random semiprimes**, and are not a realistic unbreakable classical workload.

## Frozen quantum-simulator method, no estimator refitting

Compare public unchanged base `a` with public cubed base `a³ mod N`. Synthetic prime factors and multiplicative orders are used **ONLY after public manifest commitment** to simulate ideal uniform eigenphases and verify the known identity `ord(a³)=ord(a)/gcd(ord(a),3)`. Success for a phase bin requires strict PUBLIC ordinary CF denominator d, 1<d≤N even, pow(base,d,N)==1, and a nontrivial gcd(base^(d/2)±1,N). An empty set of such public factor-producing denominators means *exactly zero* factor success under this verifier for any QPE phase outcome, not a missed success in an unexamined tail.

The entire method is the prior audited N22 high-precision protocol with the necessary 23-bit modifications frozen before data:
- **22 phase stages m=4,6,...,46**, 4 ideal shots per stage; exact complete uniform-eigenphase QPE FFT distribution for m≤18; every **65 centered outcome bins** per eigenphase for larger m, with analytic omitted-outcome probability ≤1/63 and measured head deficit.
- Exhaustive eigenphases if validation order r≤131072; otherwise **131072** fixed SHA-seeded nominal uniform eigenphase draws shared between plain/cube. Same preregistered seed salt as N22; no cherry-picked random seeds or fitted probability head windows.
- Predeclared **1408-test 99%-simultaneous empirical Bernstein** union budget for accepted head and omitted tail; statistical statement requires truly IID uniform phase draws, and CPython fixed PRNG is **not** formally certified IID. Float/Numba trigonometry is not certified outward-rounded interval arithmetic.
- Propagated model bounds for strict factor-production-by-cap, generic abstract logical CCX per attempted staged session and CCX per successfully factor-producing session under hypothetical independent restarts, including all rows with undefined zero-success costs.
- A model cube win requires **the entire upper cube/plain CCX-per-success interval strictly below 1**; a model loss requires its entire lower interval above1. A crossing interval is explicitly inconclusive. No actual QPU, noisy circuit or physical runtime is measured.

## ALL EIGHT originally frozen N23 case outcomes

Ratios are **cube/unchanged** for *ideal-model logical CCX per successful factor-producing session*; smaller than1 is favorable.

| Group | N | Public base | Validation order a→a³ | Strict public CF certs a/a³ | 99%-phase-confidence plus tail cube/plain ratio | Frozen outcome |
|---|---:|---:|---|---:|---|---|
| **Trigger** | **4,958,741** | 19 | 82,565→82,565 | **0/0** | Undefined | **Factor-incapable** |
| **Trigger** | **6,535,103** | 2 | 1,084,348→1,084,348 | 3/3 | **[0.941356,1.085360]** | **INCONCLUSIVE** |
| **Trigger** | **7,692,497** | 19 | 548,310→182,770 | **0/0** | Undefined | **Factor-incapable**, even with shorter order |
| **Trigger** | **6,957,281** | 29 | 6,032→6,032 | 577/577 | **[1.004388,1.017557]** | **Cube model LOSS** |
| Control | 4,316,413 | 5 | 718,458→239,486 | 3/9 | **[0.768092,0.874714]** | **Cube model WIN** |
| Control | 7,075,567 | 3 | 586,968→195,656 | 6/18 | **[0.770684,0.871192]** | **Cube model WIN** |
| Control | 6,394,693 | 13 | 106,488→35,496 | 30/90 | **[0.799529,0.843385]** | **Cube model WIN** |
| Control | 6,690,841 | 13 | 1,663,321→1,663,321 | **0/0** | Undefined | **Factor-incapable** |

### Prespecified primary result: unequivocal FAIL

The frozen trigger rule required **≥3/4 jointly factor-capable cases**, no loss of cube factor-production coverage and **≥3/4 cases with ratio entire upper bound below1**. Actual trigger yields:
- jointly factor-capable **2/4**;
- plain/cube factor-capable **2/4 each**, no coverage loss;
- confirmed model cube wins **0/4**;
- confirmed model cube losses **1/4**, inconclusive 1/4, exact factor-incapable 2/4.

Thus BOTH the capacity and wins conditions **FAIL**, and the result cannot be repaired by filtering out factor-incapable cases or tuning a different sampler after inspection. The strict loss on N=6957281 has cube unchanged validation order and >1 ratio: the extra arithmetic constant processing slightly increases model CCX, which is a previously observed important countermechanism.

In contrast, the *precommitted CONTROL* contains **3/4 factor-capable whole-band cube wins** and one zero-certificate case, illustrating that public **N mod 3 = 2 is not a reliable sufficient marker of favorable cubic order effects**. The control wins reflect order reductions r→r/3 on the three factor-capable control rows; the trigger’s only r/3 example was factor-incapable. This group inversion within **eight** synthetic classically solvable cases is *not* evidence that the opposite residue is generally optimal; it is an informative falsification of using the original trigger group as a universal predictor. Never mislabel the control successes as passing the preregistered trigger gate.

## Separate phase-recycling width checkpoint

The generic clean-ancilla 23bit arithmetic workspace is **72** logical qubits. Textbook coherent 46-phase-bit wide cap produces **118** peak logical qubits versus **73** peak under one-phase-bit recycling, **45 fewer logical / 38.14% lower simultaneous width**. This is independent of the cubic transform and is NOT an estimate of fault-tolerant physical resources or measured QPU mapping/fidelity. No real Shor factoring circuit or device runtime occurred.

## Next falsification — selection and factor production, not more favorable seed hunting

**Wins preserved:** true public-only manifest frozen before secret validation, reproducible independently sharded high-precision full-outcome-head QPE bound execution, 8/8 numeric and proper classical-factoring audits, 3 rigorous-in-model conditional control wins and a distinct recycling-width result.

**Negatives preserved:** **0/4 model wins** in the predeclared trigger and a **strict model regression**, two factor-incapable trigger cases including one with reduced order, three factor-incapable among the eight NEW N23 cases (separately, four among eight earlier N22 holdout cases), full classical factorization of 21/21 candidates, no demonstrated public selection rule / hardware advantage. Earlier 22bit conditional positive 3/4 trigger must remain visible alongside this new 23bit failure.

The next research question is whether **any public-only predictor** can distinguish useful shortened-order-with-factor-witness cases from zero-certificate and unchanged-order cases *without* conducting expensive public factoring itself. It needs a NEW preregistered 23–24bit public population with matched plain/cube, randomized or all-strata controls, and separately priced classical processing. Alternately, test the independent N35 public source sign-selector across different modulus/target-native layouts; keep zero-QPU and the immutable device feasibility gate. No confident real quantum speedup, new cryptographic attack, asymptotic Shor improvement, N35 hardware-ready factoring or paid IBM Runtime claim is supported.
