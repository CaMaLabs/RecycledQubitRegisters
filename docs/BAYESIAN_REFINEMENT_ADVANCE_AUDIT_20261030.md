# Search for the missing advance: Bayesian refinement and a Cassini obstruction

Research lead: Chase Lunsford / CaMaLabs. Date: October 30, 2026.

**A reproducible numerical improvement was found. An RSA-breaking advance was
not found.** This study changes scalar phase-estimator numerics, not the cost
of reversible modular arithmetic or the availability of fault-tolerant hardware.
External compute spend and QPU jobs: zero. No hosted CI was requested.

## Candidate that survived the numerical test

The inspected upstream implementation of Van Kirk/Gidney's adaptive Fibonacci
phase estimator splits a cell by preserving its old total mass and distributing
that mass using observations since the cell's birth. This is an adaptive
quadrature approximation. It does not, after refinement, generally equal
the full-transcript midpoint quadrature on the resulting partition.

The new adapter uses global evidence bookkeeping. At each split, it assigns
the children their cell widths times the likelihood of the **entire observed
transcript**, keeping all cells on one common normalization scale. The
estimator sees only the measurement transcript. The synthetic true phase
enters the measurement source and subsequent accuracy audit, not reweighting.

A second arm reweights only at the end, on the original partition and original
transcript. That arm requires **zero additional quantum probes**. Neither
midpoint quadrature is an exact continuous posterior, and the upstream
approximation should not be described as a floating-point implementation bug.
No novelty claim over the Bayesian numerical-analysis literature is established.

## Original experiment and outcome

Before scoring, the plan fixed two fresh seed cohorts, counts, the authors'
parameter formulas, and the primary gate. There were648 independent phase
cases and1,296 paired arm executions: per cohort,256 cases at n4,64 at n64,
and4 at n2048. Here n is the paper's scalar-estimation parameter: the n2048
cases **do not simulate RSA-2048 modular arithmetic or factor an RSA modulus**.

The small n4 cases were also checked against an independent65,536-point
uniform-grid likelihood quadrature on the original transcript. Total variation
distance between cell-mass distributions was:

| Cohort | Cases | Median upstream distance | Median final-reweighted distance | Improved cases |
|---|---:|---:|---:|---:|
| Replication | 256 | 0.040158 | 0.003891 | 256/256 |
| Holdout | 256 | 0.041721 | 0.003818 | 256/256 |

Thus the holdout numerical discrepancy was about10.9 times smaller. These
are distances from a finite numerical reference, **not false-certification
probabilities, posterior calibration guarantees, or a10.9x factoring speedup**.
At larger settings, full-transcript midpoint consistency was checked, but a
dense reference was not available; the small-n numerical gain must not be
extrapolated as a certified RSA-scale posterior bound.

The adaptive global-split estimator recovered from two holdout final-probe-cap
events: one n4 case used52 versus2,061 probes, and one n64 case207 versus2,189.
Consequently, the pooled holdout probe ratio was0.89235. The paired median
probe difference was **zero in both cohorts**. The arithmetic mean is dominated
by these two cap events; it is not evidence of a typical11% probe reduction.
In the four n2048 holdout cases, mean probes were1162.25 versus1162.0 and
mean local CPU time was3.25 versus2.66 seconds. The larger-setting adapter
has not demonstrated a resource advantage.

The prospective primary requirement was a statistically significant reduction
in false certifications, with no more than5% mean-probe overhead. Both arms
had **zero observed false certifications**, so there were no discordant
false-certification events. The one-sided paired-test p-value was1; the primary
gate **did not pass**. Zero observed failures does not prove zero failure risk.

## Candidate that failed an exact mathematical check

The traveling state has adjacent accumulator eigenphases F[k-1]*theta and
F[k]*theta. Exact conjugation of the actual multiply/swap maps was verified
over10,976 tiny unit-pair/register/level cases; this is a valid place to try
an extra phase probe without reconstructing the state.

But take two candidate phases separated by

`Delta = F[k-1] / F[k] (mod 1)`.

The right accumulator has zero phase difference modulo1. Cassini's identity
gives `F[k-1]^2 = +/-1 (mod F[k])`, so the left accumulator differs by only
`+/-1/F[k]` modulo1. For bounded integer coefficients a,b,

`(a F[k] + b F[k-1]) Delta = +/-b/F[k] (mod 1)`.

This is a hard global alias for cheap, bounded linear combinations of the two
current accumulator probes. A binary sinusoidal companion measurement changes
its outcome distribution by at most pi/F[k]. By the sequential total-variation
bound,48 such companion probes change the complete transcript distribution by
at most48*pi/F[k]. At k197 this bound is approximately **2.28e-39**.

This rules out a universal constant-probe companion-only validation shortcut
in that restricted model. It is **not** a factoring lower bound and does not
exclude going back to other levels, different unitaries, or different algorithms.
It explains why an attractive adjacent-register idea cannot be credited as the
missing RSA breakthrough without paying additional costs.

## Other new results considered

- https://eprint.iacr.org/2026/2665 (October28): a cat-qubit resource estimate
  reports about23,000 cat qubits and3.14 days for RSA-2048 under explicit noise
  and timing assumptions. This is an architectural resource advance, not free
  hardware available to this project or an executed RSA-2048 factorization.
- https://eprint.iacr.org/2026/2131 (September20): a1024-bit RSA forgery
  implementation reports1,380 core-years and2^32 raw signing-oracle queries.
  It changes the attack model; the public-key-only RSA challenge supplies no
  such oracle. It is not an applicable zero-cost public-key break here.

## Reproduce and inspect

The adapter and tests are new code. Upstream source is an external dependency,
not vendored or represented as CaMaLabs work:

- https://github.com/katherinevankirk/streaming-regev
- commit `b4fee3bf08373bf759beec539d5a3ec78b63416f`
- simulator SHA256 `1baf81d1e8ff0c822ac5656f608e018ed4f6c2be50e9f1eecafc5e6397292306`
- paper https://arxiv.org/abs/2610.06733, downloaded PDF SHA256
  `e87e8ed4c9310e8bd16fd8bcb19a986cde5f233eb9587dddd87936f3a490709f`

From the repository root, with Python3.12:

```bash
python3 -m venv .venv-bayesian
. .venv-bayesian/bin/activate
python -m pip install -r requirements-bayesian-audit.txt
git clone https://github.com/katherinevankirk/streaming-regev.git /tmp/qrr-streaming-regev
git -C /tmp/qrr-streaming-regev checkout b4fee3bf08373bf759beec539d5a3ec78b63416f
QRR_UPSTREAM_SIMULATOR=/tmp/qrr-streaming-regev/simulator.py python -m unittest discover -s hardware -p test_qrr_bayesian_refinement_audit.py
python hardware/qrr_bayesian_refinement_audit.py --upstream-simulator /tmp/qrr-streaming-regev/simulator.py --output results/bayesian_refinement_20261030/rerun.json
```

Original raw results are losslessly preserved in `audit.json.gz`, accompanied
by readable `summary.json`, frozen `audit_plan.json`, and checksums in
`verification.json`. Four numerical/algebraic contract tests pass. Commits
carry `[skip ci]`; this study requests no paid or hosted execution.

The justified next scientific step is a separately frozen rare-failure study
large enough to test calibration, while charging classical replay costs. The
present result supports retaining the numerical adapter as an experiment. It
does not support claiming practical RSA factoring or a new complexity bound.
