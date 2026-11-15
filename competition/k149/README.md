# K149 — fixed-point seed + two Newton steps for Helios invsqrt

Status 2026-11-14: **Numerical feasibility achieved, quantum resource feasibility NOT achieved. No official score win.**

This responds to the Quake III fast inverse-square-root seed/Newton idea **without** importing its IEEE-754 32-bit floating interpretation or bit-hack magic constant. It uses a small fixed-point lookup over normalized input followed by exact-integer Newton arithmetic.

## Novelty check
K117 normalized input and evaluated Chebyshev degrees; K118 fixed-point Horner; K120 piecewise cubic approximation; K121 coefficient audit; K122 QROM; K123 a reversible multiply-add reference; K148 proved 128 equal *linear* regions insufficient for the 2^-24 numerical tolerance. **None ran this cheap piecewise-constant LUT + two fixed-point Newton iterations over the complete 3,133,452-input domain.** The approach is a numerical/architectural candidate, not a ready quantum circuit.

Algorithm: x=2^(2k)*m with k=floor((bit_length(x)-1)/2), 1<=m<4; the table uses B seeds uniformly in [1,2), B seeds uniformly in [2,4) (total 2B). Seed y0 is rounded to signed Q-bit fraction. Each Newton update uses nearest-rounding fixed-point integers:

    u = round_Q(y*y)
    v = round_Q(m*u)
    y = round_Q(y*(3-v)/2)

The output is y/2^k. Exponent parity needs no irrational sqrt(2) multiplier.

## Full-domain numerical results independently run in local Python

All **3,133,452** inputs checked by exact int64 Newton iterations and floating inverse-square-root oracle. Relative error limit 2^-24 ≈5.9604644775e-8. This is **the K117/K120 numerical surrogate**, NOT a formal Kickmix phase-tolerance proof.

| Fixed fraction Q | Total LUT entries | Final failures | Worst error / limit |
|---:|---:|---:|---:|
| 24 | 64 | 228830 | 2.18728 |
| 24 | 128 | 227046 | 2.18769 |
| 24 | 256 | 228185 | 2.21445 |
| 26 | 64 | 0 | 0.54708 |
| 26 | 128 | 0 | 0.55093 |
| 26 | 256 | 0 | 0.54934 |
| 28 | 64 | 0 | 0.26538 |
| 28 | 128 | 0 | 0.13697 |
| 28 | 256 | 0 | 0.13630 |
| 30 | 64 | 0 | 0.21915 |
| 30 | 128 | 0 | 0.03415 |
| 30 | 256 | 0 | 0.03404 |

A 64-entry, Q26 design passes the surrogate but uses over half the numerical tolerance. The 64-entry, Q28 design is more comfortable. For Q28, B=32, worst relative error ~1.5817844e-8; this covers ~26.5% of nominal tolerance.

## Reversible resource gate (critical)
Each Newton iteration has **three multiplications of variable values**: y*y, m*y², y*(3-m*y²). **Two iterations = six variable multiplications**. In a simple n-bit low-product schoolbook construction, n(n+1)/2 bit products are needed *per multiplication* (not a universal mathematical lower bound), so for Q28 that is **6 × 406 = 2,436 bit-products** before adding carries, lookup, scratch clearing, phase application, or inverse computation. For Q26, this proxy is 6 × 351 = 2,106.

Straightforward liveness would require 22 input qubits + Q estimate + Q temporary product = **78 qubits at Q28** or **74 at Q26**, greater than current **62**. These estimates are construction proxies, **not** proof that optimized in-place arithmetic or wider multiplication algorithms cannot do better; an original in-place/inverse implementation requires a detailed reversible width/cost proof.

**No approval to implement a generic 28-bit reversible multiplier** on this evidence: K123's original naive 32-bit multiplier reference was already very expensive and six multiplies are unlikely to beat the 1,243 average executed Toffoli-like baseline without a radical redesign. Do not confuse all-input numerical accuracy with a scored quantum circuit.

## Reproduction
```bash
cd ~/quantum-a26-check
mkdir -p competition/k149
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/701320cbad806db5ac3fcde4139a53b90fb54ec9/competition/k149/k149_newton_seed.py -o competition/k149/k149_newton_seed.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k149/k149_newton_seed.py
```

Output `competition/k149/results/newton_seed_report.json`; script verifies pinned source SHA e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183. No candidate KMX or submission is generated.

## Decision
**Numerics GO; naive reversible architecture NO GO pending resource proof.** Next progress must be a genuinely lower-cost quantum multiplication / in-place approximate Newton scheme or a different iteration that uses substantially fewer nonlinear operations and a width <=62. If none can be demonstrated, close K149 without creating an expensive quantum implementation.

## Independent user VM reproduction (2026-11-14)

The user ran the committed K149 script using `$HOME/.venvs/kaggle-k001/bin/python`. `K149_SELFTEST PASS`; `K149_RESULT` returned **12 configs, 9 passing, smallest LUT pass Q26 with 32 bins per octave (64 entries), worst tolerance fraction 0.5470793314693763**. Q28/32 bins has worst fraction 0.2653793893664381; Q28/64 bins 0.13696963832520562. The Q24 entries failed with ~227k–229k violations. This matches the previously recorded full-domain numerical simulation. **No Kickmix candidate, full verifier test, or leaderboard improvement.** Next go/no-go is counted in-place reversible liveness and exact output-correction economics; do not repeat a generic polynomial or unconstrained multiplier implementation.
