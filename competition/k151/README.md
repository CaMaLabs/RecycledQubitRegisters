# K151 — compact signed Newton correction
2026-11-15. **Exhaustive classical result, not a gate-level reversible Kickmix circuit.**

Starting from K150's numerically passing Q14→Q26 two-step Newton scheme with 64 table entries, K151 computes
`delta = Newton_Q26(m, y14 << 12) - (y14 << 12)`.
On all **3,133,452 Helios inputs**, the signed delta is **[-5460,7384]** and fits in **14 signed bits**, versus the final Q26 estimate taking 27 bits. Worst relative error still uses **0.8018678218** of the K149 2^-24 numerical tolerance, with **zero violations**.

This yields a compact *classical storage representation*:
- x: 22 bits
- first estimate: 14 bits
- signed correction: 14 bits
- total: **50 bits**, leaving a *nominal* 12 of the 62 qubits.

**No quantum qubit-width or Toffoli-count win is established.** This is the range for actual seeded inputs only, not arbitrary quantum basis states. A reversible correction oracle must preserve x and y14, compute the nonlinear delta, apply it, and uncompute all scratch coherently. There is **no proved implementation within the 12 remaining qubits**. The straightforward three-register representation uses 63 bits before scratch, as K150 showed. Neither delta compactness nor the classical numerical test proves an official verifier PASS.

Reproduction:
```bash
cd ~/quantum-a26-check
mkdir -p competition/k151
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/53fd31385efe1e73a5b7417e614a63498236662c/competition/k151/k151_newton_delta.py -o competition/k151/k151_newton_delta.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k151/k151_newton_delta.py
```
Expected summary: `K151_RESULT` with 0 violations, signed delta range [-5460,7384], 14 bits, total 50 stored bits. It writes `competition/k151/results/delta_feasibility.json`.

Next go/no-go: implement actual reversible delta synthesis with exact gate count and proven max scratch <=12, including seed lookup, clean uncompute and phase application, **before** suggesting an official full-domain score win.
