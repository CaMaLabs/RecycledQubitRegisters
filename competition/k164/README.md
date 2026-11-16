# K164 — carry-aware chunk cofactors (exact, bounded)

**Status: verified locally at Q3–Q6; not a streaming arithmetic multiplier or full Helios candidate.**

This experiment splits the Q-bit fractional offset into high and low chunks. The high chunk together with the 3-bit segment selector chooses an exact rounded-seed cofactor; a shared low-chunk ANF computes all its output bits into an arbitrary XOR target, then reverses all work. Every nonlinear monomial is computed into a reusable scratch term, fanned out to all required output bits, and uncomputed.

The complete affine function `A[segment] - floor((B[segment]*offset + 2^(Q-1))/2^Q)` is preserved exactly, including **carry and rounding**. However, those carries are encoded in the cofactor truth tables: **there is no physically streamed arithmetic carry register**. That is an important distinction from the originally proposed K164 word-level chunked multiplier.

## Locally reproduced gate counts

| Q | Low offset chunk | CCX | CX | Scratch | Total wires | Checked cases |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 1 | 450 | 61 | 5 | 15 | 192 |
| 4 | 2 | 502 | 99 | 5 | 17 | 384 |
| 5 | 2 | 1,286 | 249 | 6 | 20 | 768 |
| 6 | 3 | 1,892 | 504 | 6 | 22 | 1,536 |

Each case tests all 8 segment values, every offset, and three initial XOR targets, checks exact reference arithmetic, the output's unchanged input bits, every scratch bit returned to zero, and inverse/involution.

For comparison, K163 Q4 shared-output ANF was 440 CCX with 6 scratch, and K163 Q5 1,218 CCX with 7 scratch. **K164 currently trades slightly more CCX for one less scratch.** K161 Q4 was 7,208 CCX/24 scratch; K162 Q4 1,024 CCX/5 scratch.

The high/low partition has a **syntactic 10-clean-scratch projection at Q14** (10 high controls, seven low controls), below K151's 12 free scratch. However, it requires 1,024 high-cofactor groups and up to 128 low inputs per group. We have NOT generated or costed Q14 and should expect exponential gate growth. **This is not a viable full-width result yet.**

K157's exact measurement-assisted carry recycler (27 CCX/12 clean carry) remains an active independent lead, not part of K164; no phase-correct measurements are used here.

## Copy and run on Ubuntu

```bash
cd ~/quantum-a26-check
mkdir -p competition/k164

curl -fL \
  https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/f6556e83e51752ee3d32fdaa4a8021de3a8c224e/competition/k164/k164_chunk_cofactor.py \
  -o competition/k164/k164_chunk_cofactor.py

PY="$HOME/.venvs/kaggle-k001/bin/python"

"$PY" competition/k164/k164_chunk_cofactor.py --selftest
"$PY" competition/k164/k164_chunk_cofactor.py --scaling
```

The full run checks the SHA256-pinned Helios baseline and writes `competition/k164/results/cofactor.json`.

## Next experiment gate

Instead of expanding every high cofactor, exploit the affine-seed fact that the slope is constant **within each of eight segments**. Factor the offset contributions into bounded reversible shift/add operations with explicit carry state and cleanup, keeping <=12 scratch, before investing in any Q14 full synthesis. If that is not possible or cost-effective, prioritize proven K157 adder savings and any concrete K158 shared-parity improvements on the original baseline.

**No official score win or 62-qubit end-to-end construction claimed.**
