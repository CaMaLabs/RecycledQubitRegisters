# K163 — segmented word-level arithmetic versus shared nonlinear output terms

**Status:** two bounded exact reversible implementations constructed and tested locally. Neither produces a full Helios candidate.

The target remains the exact K159 Q-bounded affine seed:

    y0 = A[segment] - floor((B[segment] * offset + 2^(Q-1))/2^Q)

XOR y0 into an arbitrary target word, leaving selector, offset and all scratch unchanged. We test every segment and offset combination and three initial target values, as well as running the full circuit twice/inverting it. Every gate is X/CX/CCX.

## Architecture 1: word accumulator with no separate seed register

Use a single 2Q+1-bit accumulator P and:
- Coherently add A[segment]*2^Q to P,
- Coherently subtract B[segment]*offset as per-segment controlled shifted-constant powers,
- Add the rounding bias 2^(Q-1)-1 so P>>Q equals the required *rounded subtraction*,
- CX the high output bits into the arbitrary initial target register, then exactly reverse P computation.

This is a genuine segment-selected, word-level reversible multiplier/accumulator but the most straightforward multi-controlled ripple scheme is expensive and requires substantial scratch. At Q4: **7,860 CCX, 20 scratch**. At Q14, this exact construction needs **60 scratch**, so it cannot fit the K151 free-12 budget. It is a negative experimental result, not a viable Helios architecture.

## Architecture 2: share the nonlinear word monomials

Compute each unique Boolean ANF monomial from the selector+offset *once* into a clean workspace bit, CX that computed term into **every** output bit that uses it, then reverse the monomial computation. Compared with K162, which recomputed the same monomials for each output bit, this avoids repeated CCX and materialized seed/product registers.

| Q | Architecture | CCX | CX | Scratch | Total wires | Tested cases |
|---:|---|---:|---:|---:|---:|---:|
| 3 | word | 3428 | 8 | 16 | 26 | 192 |
| 3 | shared | 154 | 111 | 5 | 15 | 192 |
| **4** | **word** | **7860** | **11** | **20** | **32** | **384** |
| **4** | **shared** | **440** | **288** | **6** | **18** | **384** |
| 5 | shared | 1218 | 665 | 7 | 21 | 768 |

K162 Q4 direct ANF: 1,024 CCX and 5 scratch. K163 shared Q4: **440 CCX and 6 scratch**, 57.0% CCX savings for one more scratch bit. K161 Q4 full-interpolation: 7,208 CCX and 24 scratch.

However, direct ANF across Q+3 input bits still grows exponentially in Q. K163's shared monomial strategy uses Q+2 clean scratch at full width, so **Q14 would require 16 scratch**, exceeding 12. This version is not a Q14 candidate either.

## Reproduce

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k163
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/5be510765c6abed244e65564aa86ec6ab845101e/competition/k163/k163_word_shared.py -o competition/k163/k163_word_shared.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k163/k163_word_shared.py --selftest
"$PY" competition/k163/k163_word_shared.py --scaling
~~~

Output: competition/k163/results/word_vs_shared.json.

**Next:** do not confuse fewer lookup gates with full Helios improvement. Combine low-scratch output term sharing with arithmetic word decomposition (short chunks), carry propagation, and K157 measurement-assisted release, explicitly respecting 12 ancillas and counted phase correction. User K162 and K160 reproduced. K157's 14-bit 27-CCX/12-carry measured adder remains an active independent result.

No official verifier result or leaderboard improvement claimed.
