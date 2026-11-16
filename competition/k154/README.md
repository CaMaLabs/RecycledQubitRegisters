# K154 — exact 4-bit streaming signed product with reversible cleanup

**Status: small gate-level arithmetic prototype VERIFIED; full Helios implementation not built.**

After K151 proved a 14-bit signed final correction and K153 found the full residual needs 16 bits, K154 investigates retaining only partial-product workspaces, integrating rounding, and uncomputing scratch coherently. K152 direct ANF oracle is abandoned (10-bit bounded domain cost 13,104 CCX).

## Actually tested

The arithmetic oracle computes `|r,y,d,0> → |r,y,d XOR floor((signed4(r)*y+16)/32) mod 16,0>` where `r` is signed 4-bit and `y` is unsigned 4-bit. It builds each shifted signed-r partial row, adds it into a product register with an exact Cuccaro ripple adder, clears the row, adds the rounding half-unit, XORs the sign-extended high bits to d, and **reverses the entire computation**, clearing every ancilla.

The user-independent local Python execution exhaustively tested all 16 signed r × 16 unsigned y with three arbitrary output targets each = **768 test states**, confirming both forward output and involution. X/CX/CCX gate-level interpreter, not an abstract arithmetic identity.

**Observed static gate count:** 240 CCX, 262 CX, 2 X. This includes forward arithmetic, output, reversal, and every scratch uncompute.

**Resource use:** 4-bit r + 4-bit y + 4-bit output = 12 logical data bits; 8-bit partial product register + 8-bit row operand + one carry = **17 clean scratch**; 29 total. The bounded prototype is **five scratch bits above the nominal K151 12-scratch limit**, even before scaling to 14-bit y / 16-bit residual. It is NOT a valid 62-qubit Helios construction.

### Significant independent improvement: actual cheap adder

An exact 14-bit Cuccaro ripple-carry adder using **28 CCX + 56 CX**, one clean carry and no other scratch was also synthesized and tested with 500 random 14-bit addend pairs (lower widths 1–4 exhaustively). This is far cheaper than K153's deliberately naive **819-CCX** 14-bit modular-adder reference. Both act as `|a,b,0> → |a,(a+b) mod 2^n,0>`, and return carry clean. The 819 versus 28 comparison is for the **adder only**; it is not a full Newton improvement.

The 4-bit product-and-round construction has cost 240 CCX with **17 scratch**; do not extrapolate that as a 14×16 signed product cost, especially with 12 scratch available.

## Reproduction

```bash
cd ~/quantum-a26-check
mkdir -p competition/k154
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/4f3e4af5db452fe3fdaacfbffbbc206cea73483e/competition/k154/k154_streaming.py -o competition/k154/k154_streaming.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k154/k154_streaming.py --selftest
"$PY" competition/k154/k154_streaming.py
```

Report: `competition/k154/results/streaming.json`.

**Go/no-go:** We have a low-ancilla reversible **adder** and verified small signed streaming product, but the current streamed multiplier does **not** fit the available scratch. Before a full 22-bit-Kickmix attempt, develop a carry-streaming row add that avoids the independent 8-bit operand buffer, with exact gate counts and clean-scratch proof. No official verifier score improvement claimed.
