# K150 — mixed-precision Newton, reversible injectivity and width gate

2026-11-14. **Numerically promising, no certified 62-qubit circuit, no official score improvement.**

## Difference from K149 and earlier K117–K123
K149 ran *both* Newton iterations at the final precision Q26–Q30. K150 uses **one lower-precision iteration and one final-precision iteration**, retaining the exact K149 integer rounding convention. It checks **all 3,133,452 input integers**, not just random samples. It also tests a reversible injectivity obstruction to naive in-place overwrites.

The initial full-domain local Python experiment found, with **64 seed entries (32 per octave) and final Q26**:

| First Q | Final Q | Input violations | Worst error / 2^-24 tolerance | Toy schoolbook product proxy |
|---:|---:|---:|---:|---:|
| 12 | 26 | 515,655 | 6.4854 | 1,287 |
| 13 | 26 | 8,396 | 1.7181 | 1,326 |
| **14** | **26** | **0** | **0.80187** | **1,368** |
| 15 | 26 | 0 | 0.65939 | 1,413 |
| 16 | 26 | 0 | 0.56447 | 1,461 |
| 26 | 26 | 0 | 0.54708 | 2,106 |

Proxy = 3·Q1(Q1+1)/2 + 3·Q2(Q2+1)/2, **not a Toffoli count or lower bound**, because fixed-point middle products need carry propagation and omitted low-bit effects. The difference between 1,368 and 2,106 is ~35% for this proxy, not an official score gain.

A **real liveness problem remains**: Q14 first-step output has peak integer value 16,383 (14 bits), while Q26 final output can reach 67,108,864 = 2^26 (27 bits). Retaining both estimates plus the 22-bit x input at once requires **22+14+27=63 qubits**, already greater than 62, **without even one scratch qubit**. This is the straightforward out-of-place storage case, not a universal lower bound on specialized circuits.

The crucial additional reversible finding: the rounded Newton update y→F(m,y) is **not injective on general basis states for fixed m**. A small Q8 exact enumeration finds distinct y values with identical next y. Thus a naive `y = newton(y)` overwrite is not a valid reversible mapping on the full register. It does not forbid a clever permutation on *reachable* seed states with extra bookkeeping; such a circuit has **not** been supplied.

The existing K123 reference modular multiplier costs 4,200 CCX for width14 and 44,226 for width26; 3 instances of each would cost 145,278 CCX, **but those are from a deliberately inefficient different modular construction**. They are not the actual cost of fixed-point Newton and not a proof of computational hardness. This explicitly rejects reusing K123 naive multiplier as a competitive solution.

## Exact implementation/reproduction

```bash
cd ~/quantum-a26-check
mkdir -p competition/k150
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/77a7e22182234d38ba0c10a27d20b58efd312727/competition/k150/k150_mixed_precision.py -o competition/k150/k150_mixed_precision.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k150/k150_mixed_precision.py --selftest
"$PY" competition/k150/k150_mixed_precision.py
```

Report: `competition/k150/results/mixed_precision.json`. The script refuses unpinned KMX. Its small self-test validates rounded Newton, the K123 original counting formula, and a collision demonstrating why general overwriting is irreversible.

## Decision

**Numerics improvement proven for the tested full integer domain. No measured quantum-gate reduction or useful legal width gain established.** Do **not** declare a score win or push a generic 26-bit reversible multiplier until one of these is supplied:

1. A qubit-neutral reversible encoding/compute/uncompute schedule that handles every basis state coherently and restores all scratch.
2. An exact gate-counted middle-product implementation with dynamic Toffoli cost and max live width 62, including seed lookup and two iterations.
3. An official full-domain Kickmix verifier pass with strict score below **95,369.00696815242**.

The next theoretical improvement would be to derive a *specialized reversible correction* based on `x` that avoids simultaneously storing the low- and high-precision estimates. Until then this branch is at an **architectural resource gate**.
