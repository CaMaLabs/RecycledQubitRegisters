# VERIFIED — fresh 22-bit public holdout: ladder fails to establish gain over always-cube

**Lead/original research direction:** Chase Lunsford / CaMaLabs. **Date:** October 14, 2026 Pacific (CI October 15 UTC). AI-assisted preregistration, design, implementation, numerical CI and analysis. All results are strictly in-silico **nearest-bin-only ideal-QPE resource model**, not full-QPE, quantum hardware, fault-tolerant physical resources or real factoring advantage. **Zero QPU/IBM jobs.**

## Preceding research record, wins and negatives retained

- Dynamic phase-register recycling has independently measured compiled-orbit hardware evidence and estimated generic arithmetic coherent-width reduction; it is not an exponent-selection win. The 22-bit generic clean-ancilla width estimate from the current script is **113 wide→70 phase-recycled peak logical qubits** (43 fewer / **38.05%** lower); coherent arithmetic workspace is **69** and is unchanged by the cube/ladder.
- Original positive selected Dark Star scouts and the later independently frozen 96-case n17, 120-case n18, 144-case stronger classical-first n18, 40-case n18 B31 survivors, tiny n10 exact full-outcome, and eight n17/n18 analytic-tail tests are all preserved in [RESEARCH_LOG.md](RESEARCH_LOG.md). The broader 144-row v2 **ell3 trigger** had only **2 improves / 3 worsens** among eligible rows; ell5 trigger-enrichment and ell7 replication were negative. Do not erase these failures.
- The [20bit 72-case v3 public survivor result](DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_RESULT.md), CI [38677893149](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677893149), found favorable ladder/plain trigger ratios 0.8329/0.7991/0.8066 but not reliable superiority over unconditional cubing. [Independent 8192-phase convergence CI](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38678433078) confirmed direction versus plain, but one tiny ell5 ladder-vs-cube paired outcome flipped. The longer-scale effect relative to cube, not plain, was the unresolved target.

## Provenance — freeze-before-outcomes independently verified

1. [Preregistered 22bit comparison](DARK_STAR_N22_SELECTOR_VS_CUBE_PREREG.md), commit **`51b9584865081f6f829a7b5a592b72b7f687acad`** BEFORE fresh N selection and any scoring.
2. Public-only [deterministic SHA manifest script](../hardware/dark_star_n22_public_manifest.py), commit `7fdb04f9ef13083d724f52211b7883ba31ada6d2`; [scorer](../hardware/dark_star_n22_selector_vs_cube.py) commit `d59fc42ae11942b2ec4c0514cb1e3c2029b32c6c`.
3. [Successful original freeze+4-job trial **38694538017**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694538017): the PUBLIC-ONLY manifest was separately committed **`b9326ab1a77eb50b24f9d145b5f68807e4752d92`** *BEFORE* four independent group×seed model jobs ran, all **4/4 SUCCESS** with full external strict public-decision and factor-verification assertions.
4. Public selected manifest: [`results/dark_star_ptp/dark_star_n22_public_manifest.json`](../results/dark_star_ptp/dark_star_n22_public_manifest.json). SHA256 selected rows **`290a964bff4fc9ec4474d9fbd6e29fda111143113f93a1274cfafc94a8f02d98`**. Frozen public N, base, policy exponent, screening source/operation ledgers and public classical findings; NO p,q/validation order/quantum outcome included in precommit.
5. [Independent original-artifact preservation CI **38694776139**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38694776139), **SUCCESS**: retrieved the unchanged original four trial artifacts, checked SHA, all 12 exact selected N, both independent seed panels, per-row proper classical factors, policy exponents, order identities, success/cost denominators, and exact zero-QPU status. Immutable raw results committed `5e0f89d1a0204d340efb4b644380be24cf9936ca` at `results/dark_star_ptp/dark_star_n22_{trigger,control}_seed_{A,B}.json`; complete per-phase receipts are available there.

Frozen 22bit population: distinct-prime semiprimes (2^{21}≤N<2^{22}), p<q≥11, two N%3 groups: trigger=2 and control=1. Select FIRST six surviving public B31-factor-filter per SHA rank per group; no validation-order/factor or QPE resource based resampling. **31 public N screened**, 19 classically solved already by public baseline, leaving **12 distinct selected B31 survivors** (trigger 6 from 15 screened, control 6 from 16 screened). These 12 are **not a uniform random semiprime sample**, but publicly conditioned B31 survivors.

## Classical baseline — zero practical quantum factoring need

On every selected N, publicly run *additional* Pollard p−1 B47, bounded Floyd rho seeds 2/3 with at most 64 steps/seed, prime trial through 97 then prime trial through √N if needed. Both independent CI seeds see identical first proper factor per N; ALL 12 selected are factored WITHOUT any quantum step. Of these 12, **five** first factored at B47 and **seven** at fixed public rho; none needed trial division. Including original 19/31 B31 successes, the implemented classical cascade factors **31/31 screened candidates** if applied to this full public frame. Classical CPU timings and operation counts are archived by N, but CPU modulo operations cannot be added to abstract quantum CCX as commensurate units.

## Quantum cost estimator, semantics and uncertainty

Use unchanged code from prior n20 [public factor-producing nearest-bin QPE](../hardware/dark_star_n20_public_survivor_v3.py) with *precommitted n22 process settings*: stages m=4,6,…,44 (four shots per stage); validation eigenphases enumerated fully for order r≤8192, otherwise **8192** seeded uniform eigenphase numerator draws per stage. Two separate seed salts `QRR-n22-phase-seed-A-20261014` and `QRR-n22-phase-seed-B-20261014` share identical frozen public N, bases, classical checks, algebra and policies. For any phase bin y, CF denominator d must be even, 1<d≤N, `pow(base,d,N)==1` and a proper public nontrivial factor from `gcd(base^(d/2)±1,N)`. The known multiplicative-order theorem and witness status are checked using synthetic validation p,q **after** the public manifest is frozen; private data never select N, a or exponent.

Compared 3 strictly public choices on identical samples: `plain=a`, `always3=a³ mod N`, and `ladder=a^ell` with ell the first among (3,5,7) for which N%ell not in (0,1), else no transform. Trigger ladder ≡ always3 **by rule**, making that panel an exact negative selection control; control ladder selected ell5 for 3 Ns, ell7 for 3 Ns. Per-attempt cost on ALL six N and expected abstract logical CCX *per successfully factor-producing session with independent restarts* on both-positive cases are separate endpoints. Both seeds preserve 6/6 factor-producing model coverage under every policy in both groups. Pairwise model cost ratios are not hardware speeds, real quantum time/energy or fault-tolerant physical gate counts.

Each 8192 finite eigenphase-sample per-stage ideal success probability has coarse worst-case 95% Hoeffding absolute bound about 0.0150, NOT a bound on nonlinear aggregate CCX ratios. The two numerical seeds assess reproducibility, not independent N-population discovery. Across-N 2000-resample bootstrap percentile intervals are descriptive and do not cover phase-sampling error or broader classical survivor selection.

## Frozen results — primary comparison ladder versus always-cube

Aggregate = sum of modeled logical CCX *per successful factor-producing staged session with independent restarts* on six both-success-positive rows, numerator `ladder`, denominator `always3`. Lower than 1 favors ladder in the ideal estimator. Every comparison retains six cases and success coverage 6/6.

| Fresh 22-bit public stratum | Seed A ladder/cube | Seed B ladder/cube | Improvements/ties/worsenings | Between-N 95% bootstrap CI (Seed A) | Frozen decision |
|---|---:|---:|---|---|---|
| **CONTROL: primary** | **0.965595** | **0.965751** | **3 / 0 / 3** both seeds | **[0.8368, 1.0854]** | **FAIL** majority strict improvements |
| Trigger: policy identity control | **1.000000** | **1.000000** | 0 / 6 / 0 both seeds | [1,1] | Correct identity, NO selection gain |

Even though the CONTROL aggregate modeled ratio indicates **3.44% less abstract per-success CCX** in either seed, only half the rows improve. The frozen primary required a strict majority of improved rows on both seeds, a sample count at least 3, no coverage loss, and a ratio <0.98. It FAILS the majority criterion; the bootstrap CI includes 1. This means **the larger-scale public 3/5/7 ladder has NOT established a reliable incremental advantage over simple cubing**, despite a numerically stable aggregate weighted ratio in this particular six-row conditioned holdout.

Per-case CONTROL ladder/cube ratio (two independent numerical seeds):

| N | Public ladder exponent | Seed A | Seed B | Paired outcome |
|---:|---:|---:|---:|---|
| 2647753 | 5 | 0.991258 | 0.991223 | small gain |
| 3230443 | 5 | **0.722649** | **0.724571** | gain |
| 2750971 | 7 | **1.251021** | **1.248198** | **worse** |
| 3799363 | 5 | 1.005105 | 1.005103 | worse |
| 2131621 | 7 | 1.010397 | 1.010398 | worse |
| 4089931 | 7 | **0.869735** | **0.871688** | gain |

The sign of **every paired comparison remained the same across both new phase seeds**. The aggregate saving is concentrated in a few large improvements, notably N=3230443; another case N=2750971 incurs roughly 25% MORE modeled per-success CCX. This heterogeneity cannot be dismissed by an aggregate result.

## Secondary comparisons and mechanism

| Public stratum | Policy / plain | Seed A expected CCX per success | Seed B expected CCX per success | Improved / tied / worse |
|---|---|---:|---:|---|
| Trigger | **always3 / plain** | **0.786726** (21.33% fewer) | **0.784368** (21.56% fewer) | **6 / 0 / 0** |
| Trigger | ladder / plain | 0.786726 | 0.784368 | 6 / 0 / 0 (identical cube) |
| Control | always3 / plain | 0.949410 | 0.949205 | 2 / 0 / 4 |
| Control | ladder / plain | 0.916745 | 0.916696 | **2 / 0 / 4** |

The 22bit trigger samples again demonstrate a consistent modeled **cube vs unchanged** reduction when conditional on B31 classical survival and factor-producing nearest-bin ideal-QPE, but ladder offers exactly zero additional benefit there. In control cases, both cube and ladder worsen more individual cases than they improve, notwithstanding favorable aggregate ratios. Earlier negative ell5/ell7 residue-stratified results are unaltered. Savings primarily accompany reduced expected phase rounds, not improved classical factoring or intrinsically less expensive modular constants.

**Separate logical peak-width result:** 22bit clean-ancilla arithmetic workspace **69** coherent logical qubits, conventional 44-qubit phase cap **113 wide** logical, iterative/recycled phase register **70** peak, i.e. **43 fewer / 38.05% lower** simultaneous logical width in the analytic circuit-resource construction. The transformation itself does not produce this width reduction. Not a physical-qubit/surface-code or IBM compiled-native-gate result.

## Next falsification gate

**Record the win:** a separately preregistered, *new 22-bit public-selected population* with a manifest committed BEFORE validation orders, independent numeric seeds, complete public classical factoring, and success-aware paired comparisons. The modest cube-vs-plain trigger numerical trend is replicated, but it is a conditional ideal-QPE resource effect, not an efficient deployable factoring method.

**Record the failure:** the **primary ladder-vs-always-cube strict majority criterion FAILED** on control. All 12 selected 22bit Ns were classically factored with a frozen B47/rho budget; there is no credible end-to-end classical+quantum factoring speedup or reason for a paid QPU test.

Before any stronger claim, prioritize separating phase-sample numerical error from structural variation and using the previously derived analytically tail-bounded *full-outcome* model on a small independently selected subset of the new larger-N panel. If compute/precision allows, evaluate a genuinely larger, preregistered representative sample, keeping classical factor coverage and public selection strict. Do not tune exponent policy on these 12 observed heldout outcomes and re-test on them as if independent.
