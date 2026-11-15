# K148 — backward error-band feasibility against Helios

Date: 2026-11-14. **ANALYTICAL RESOURCE GATE ONLY — no Helios circuit optimized or verified.**

## Source versus prior work
- Published: Gu, Kemeny, Yelin and Lukin, *Discovering state-of-the-art quantum circuits with large language models* (2026), https://arxiv.org/abs/2610.22367. Source: https://github.com/andigu/uncompute/tree/main/tasks/coulomb-potential/circuits/discovered
- Published Coulomb potential circuit uses 128 piecewise-linear fitted lookup leaves, and back-propagates a **±32-unit integer final-output error band** through the exact rounding and rescaling of its **different task**. Measurement-corrected unlookup costs 17 Toffolis in that task.
- Helios baseline 62 qubits, score 95369.00696815242, nominal numerical surrogate *relative* error 2^-24, valid integer x from 1 to 3133452. This is not the same precision contract or arithmetic target.
- K117 already investigated normalized Chebyshev; K118 fixed-point Horner; K120 **16-piece cubic, 32 fractional bits**, passed numerical full-domain checks but no full circuit cost; K121 coefficient bitplanes; K122 reversible lookup; K123 unoptimized multiplier. **Do not repeat those** or claim backward-fitting is a brand-new numerical approximation technique.
- K147 found zero eligible strict coherent CCX uncomputation candidates. K146 true Polytof pipeline preserved rank 23 and added 16 compiler ancillas in top local region.

## New falsifiable piece: formal 3-point lower bound
K148 implements a necessary-condition certificate for *uniform* piecewise-linear fits to normalized f(m)=m^-1/2 on [1,2). In the first interval of width 1/N choose exactly representable integer inputs x0=2^20, x1=x0+2^20/(2N), x2=x0+2^20/N (all in official domain). At f0,f1,f2, convexity gives positive D=(f0+f2)/2-f1.

Every affine interpolant L has L1=(L0+L2)/2. For *all three* outputs to meet the nominal relative-error band eps*f_i, the necessary inequality is

  D <= eps * (f1 + (f0+f2)/2).

If violated, **no real-valued affine line can pass even those three inputs**, regardless of coefficient precision, rounding, reversible arithmetic optimization, or lookup design. This test is distinct from K120's finite coefficient fit and supplies a mathematical *no-go*, not an empirical unsuccessful search.

Calculated at eps=2^-24 with 95-digit Decimal sqrt:
- 128 equal regions: required min error is at least **47.6276×** tolerance -> impossible.
- 256 regions: **11.9533×** -> impossible.
- 512 regions: **2.9942×** -> impossible.
- 1024 regions: **0.7493×** -> not ruled out; NOT proof of sufficiency.
- 2048 regions: **0.1874×** -> not ruled out.

**Do not generalize this to all adaptive lookup trees** or higher-degree approximations. A nonuniform allocation might use narrower bins near m=1. This certificate applies to uniform bins and the 2^-24 numerical surrogate; official phase error tolerance/score require the actual verifier.

## Run on user's VM
```bash
cd ~/quantum-a26-check
mkdir -p competition/k148
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/cbac7860f044bd4e0c418511e4d7ba92425237dc/competition/k148/k148_backward_band_certificate.py -o competition/k148/k148_backward_band_certificate.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k148/k148_backward_band_certificate.py
```

Output: `competition/k148/results/backward_band_no_go.json`. Script refuses any other than the pinned baseline SHA256.

## Go/no-go
A 128-leaf **uniform** piecewise-linear architectural transplant is **NO GO mathematically**. Simply increasing a 128-leaf lookup to 1024+ is **not approved** by this alone: QROM compute/uncompute cost, coefficient words, reversible interpolation, and 62-qubit limit are still unpriced. Before implementing a 1024-leaf architecture require a counted circuit whose projected score is <95,369 and whose exact output error satisfies the official verifier. Current K120 16-piece cubic may be a better cost basis than 1024 linear lookup, but its multiplier and coefficient lookup remained uncompetitive in prior work. No scored circuit or leaderboard result here.
