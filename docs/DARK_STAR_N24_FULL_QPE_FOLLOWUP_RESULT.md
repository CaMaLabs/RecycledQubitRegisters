# Completed N24 Dark Star full-outcome modeled cost follow-up — four bounded cube wins, both public selectors FAIL
**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-25. **CPU-only; no IBM hardware jobs; no IBM Runtime; no paid runtime.**

## Study design and provenance
The selected **16 N/a pairs were already frozen** on October 20 in
[`dark_star_n24_public_predictor_manifest.json`](../results/dark_star_ptp/dark_star_n24_public_predictor_manifest.json),
selected row SHA256 **`d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889`**.
Their hidden orders and classical factor-witness results were **already known from the prior experiment**.
This is therefore **exploratory reuse**, NOT a genuinely independent prospective holdout.
A separate [full-QPE follow-up scoring protocol](DARK_STAR_N24_FULL_QPE_FOLLOWUP_PREREG.md)
was committed **before** the new phase-outcome calculations.

The protocol evaluates plain base `a`, always cubing `a³ mod N`, and two
**already frozen** public conditional policies: P1 (cube when N mod3=1),
P2 (cube only if fixed public 8-step modular-bitweight cost proxy says cube is cheaper).
Always-cube is the policy primary comparator, not untransformed base.
Scoring is an ideal-QPE **model** with 23 even-bit phase stages m=4..48, four
ideal shots per stage, exact all-bin FFT at m<=18, 65 centered outcomes with
an analytical omitted-tail limit for higher m, 131072 nominal IID
pseudorandom phase draws if order is larger, and a prespecified 2944-comparison
simultaneous 1% empirical Bernstein error budget.
Sampling PRNG and floating evaluation are **not certified randomness or
formally outward-rounded guaranteed intervals**. This is logical CCX modeled
cost per factor-producing session, not a physical/native machine.

## Original 16-shard run, and audit recovery
[Original GitHub Actions run 40245560960](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40245560960):
**all sixteen CPU model scoring jobs passed and saved exact original JSON artifacts**;
the separate archive job initially **FAILED** at import because NumPy
was not installed in that job. No model outcome was discarded or rerun.
[Recovery-only GitHub Actions 40246529597](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40246529597):
**SUCCESS** after installing the missing fixed NumPy+Numba dependencies
in an independent archival runner. It downloaded the 16 ORIGINAL artifacts
from run 40245560960, validated all immutable N/base rows and policy
decisions, and committed their unchanged bytes plus [merged summary]
(../results/dark_star_ptp/dark_star_n24_full_qpe_followup_all_16.json).
The original failed archive was not reclassified as passed.
No QPU or Qiskit Runtime executed in either workflow.

## Completed results: always-cube vs plain
Across 16 frozen 24-bit semiprimes:
- **4 bounded ideal-model cube wins**, all among the four cases where cubing
  shortened the true order by 3 **and** the original half-order factor witness was usable.
- **0 bounded ideal-model cube losses**; **8 inconclusive**; **4
  factor-incapable/uncertified** (undefined per-success cost, not wins).
- **12/16** model factor-capable with either base, **same coverage**.
- **16/16** were already classically factored by the public additional
  B47/rho/trial procedure. The O(N) public continued-fraction certificate
  precomputation **itself found classical factors for 12/16**.

| Frozen N | Public a | Bounded cube/plain modeled CCX per successful factor interval | Class |
|---:|---:|---:|---|
| 12,454,609 | 23 | [0.7822, 0.9347] | bounded cube model win |
| 10,878,391 | 2 | [0.7645, 0.8375] | bounded cube model win |
| 10,494,119 | 23 | [0.7374, 0.8964] | bounded cube model win |
| 12,720,251 | 11 | [0.8055, 0.9530] | bounded cube model win |

The other eight model-capable cases have ratio intervals crossing 1.
The four factor-incapable/uncertified cases retain undefined ratios,
even when their mathematical orders shorten.

## Frozen public selector outcomes versus always-cube — both FAIL
| Selector | Switches from cube to plain | Robust modeled wins from switching | Robust losses | Gate |
|---|---:|---:|---:|---|
| P1: N mod3=1 | 8 | 0 | 2 | FAIL |
| P2: fixed public bitweight | 15 | 0 | 4 | FAIL |

Both preserve the 12/16 factor-capable coverage but FAIL their preregistered
75%-of-switched-rows improvement and no-robust-regression thresholds.
The simple residue and bit-density features miss valuable cube-model cases:
**there is still no reliable cheap public predictor** that outperforms
always-cube. Do not promote any re-fitted residue subgroup.

## Scientific interpretation and next boundary
The full-outcome model is now consistent with a **conditional** mechanism:
shorter order plus usable classical Shor half-power witness can lower modeled
logical CCX per ideal factoring success on toy synthetic numbers. The
mechanism does not make cubing change the standard even-order factor witness:
that witness remains **mathematically invariant** under cubing.
Crucially there is **no demonstrated practical quantum factoring speedup**,
**no classical-computation-adjusted cost win**, **no RSA/ML-KEM break**, and
**no N24 hardware implementation**. The whole 24-bit population was
classically easy, and public certificate precomputation is not free.

**Next useful falsification (fresh separate prereg)**: leave the previously
labeled N24 population behind; design an independent larger classical-first
sample and an **online factor verifier that does not enumerate all
factor-producing denominators via a classical factor-recovering O(N) scan**.
Compare always-cube against public selection and plain in *end-to-end*
quantum-vs-classical resource budgets, with actual architecture/native gate
counts separate from ideal logical CCX. Until that architecture work exists,
do not spend IBM paid Runtime or claim QPU feasibility.
