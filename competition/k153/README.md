# K153 — exact Q14→Q26 Newton residual and reversible arithmetic cost

**Status: exact integer residual identity and a verified gate-level modular-adder component; not a full reversible inverse-square-root circuit and not a leaderboard win.**

## New algebra, checked on every one of 3,133,452 input values

Let `S=2^26`, and `y14` be the integer result of K150's Q14 first Newton update. The original K149 final update uses `Y=y14<<12`, `m26=floor(x*2^26/2^(2k))`, `p=round(m26*round(Y²/S)/S)`.

Because `Y=y14*2^12`, its square rounds **exactly** as

```python
squared_q26 = (y14*y14 + 2)//4
product_q26 = (m26*squared_q26 + (1<<25))//(1<<26)
residual_q26 = (1<<26) - product_q26
delta = (y14*residual_q26 + (1<<14))//(1<<15)
y26 = (y14<<12)+delta
```

All these are integer operations and the expression reproduces K149's original Q26-rounded Newton update exactly across the complete 3,133,452-input domain.

Measured ranges:
- Residual: **−16,423..+20,479**, requires **16-bit signed** representation
- Final delta: **−5,460..+7,384**, requires **14-bit signed** representation
- Numerical errors: **zero** against prior relative-error 2^-24 surrogate; worst tolerance fraction **0.8018678218232443**

An exact reversible reference for a **14-bit modular add** of two stored registers was also built and explicitly simulated. It uses q36..49 as one input, q22..35 as the other, q50..61 as 12 scratch bits, keeping the original q0..21 unchanged. The gate sequence contains **819 CCX and 14 CX** operations. It was checked on 256 randomized 14-bit addends/augends with nonzero arbitrary 22-bit x, plus exhaustive 2/3/4-bit verification; all scratch ends at zero and running gates in reverse restores the original. The adder is a working reversible arithmetic primitive, **not an in-place Newton correction synthesis**. Its 819 static CCX already represents a significant portion of Helios's ~1,243 dynamic baseline Toffoli mean; those are not identical measures. This naive adder is not claimed optimal.

## Critical resource obstruction

The K151 storage layout (22 input + 14 Q14 estimate + 14 delta) uses 50 qubits, leaving **12**. The residual itself needs **16 signed bits**, so it cannot be stored alongside those three registers without reusing or spilling data. The complete square and multiplication circuits need additional carry and uncomputation workspaces. K153 does **not** demonstrate a full width-62 arithmetic implementation, nor a cheaper total gate count. Only a deliberately simple adder subroutine is fully synthesized and proven.

## Reproduce

```bash
cd ~/quantum-a26-check
mkdir -p competition/k153
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/5d55318f9eaf7c7fcc0334522cbfc15b85adb246/competition/k153/k153_residual_arithmetic.py -o competition/k153/k153_residual_arithmetic.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k153/k153_residual_arithmetic.py --selftest
"$PY" competition/k153/k153_residual_arithmetic.py
```

Expected full-domain summary: 0 numerical violations, residual range [-16423,20479], delta [-5460,7384], 819 CCX, 14 CX. Report at `competition/k153/results/residual_arithmetic.json`. Pins the Helios input SHA.

**Decision:** A useful algebraic simplification, but the straightforward 16-bit residual register **fails the 12-scratch width gate**, and the naive adder is expensive. Further effort requires streaming/product accumulation or a measurement-assisted replacement with explicitly proven exact phase correction and counted 62-qubit cost. No reason to upscale the K152 Boolean truth table or spend significant compute on this incomplete arithmetic design.
