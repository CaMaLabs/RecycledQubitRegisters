# K159 — logarithmic-style affine seeds vs K149 table

**Status:** numerical comparison script; full Helios quantum circuit/score not established.

Earlier K117/K118 investigated Chebyshev and fixed-point Horner, K120 piecewise cubic, K149 64-entry seed + two Newton steps, K150 mixed precision Q14→Q26. K159 isolates a less expensive-looking **piecewise affine seed** motivated by the Quake-logarithm idea. This is **not** an IEEE-754 reinterpretation: for x=2^(2k)m, m in [1,4), fit an affine 1/sqrt(m) approximation separately on subranges of [1,2) and [2,4). Fixed intercept and slope per segment are quantized to Q14; y0=intercept - round_Q(slope*(m-origin)), followed by exactly the Q14 and Q26 integer Newton stages from K150.

Test a 2-,4-,8-,16-segment grid (each split evenly across the octaves), with chord and midpoint-biased intercepts. Compare **all 3,133,452 inputs** to the original 64-entry K149 seed under the same relative 2^-24 numerical tolerance. Report actual zero-violation configurations if any.

Important economic caveat: the seed has **two coefficients per segment** and needs variable-by-constant multiplication and lookup, unlike direct seed-value table load. Thus 16 segments / 32 coefficients does **not** prove an advantage over a 64-entry lookup. Even a numeric PASS cannot be called an actual CCX/width win without a reversible implementation and score check.

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k159
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/96a26178f0768ed8c68fc49586b6c4d625e1acee/competition/k159/k159_log_linear_seed.py -o competition/k159/k159_log_linear_seed.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k159/k159_log_linear_seed.py --selftest
"$PY" competition/k159/k159_log_linear_seed.py
~~~

Output competition/k159/results/log_seed.json. Share K159_RESULT and K159_CASE rows. No Helios circuit is modified and no official verifier is run.

**Planned next gate:** identify whether an affine seed actually saves lookup gates *including* reversible constant multiplication, while retaining K157 measurement-carry reuse as an active integration lead. Do not discard K157 simply because K159 has a smaller table.
