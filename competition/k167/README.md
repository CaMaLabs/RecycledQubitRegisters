# K167 — cost-aware, coherent segmented seed routing

**Locally checked bounded Q3–Q5 X/CX/CCX circuits. No full Q14 circuit or official Helios verifier.**

Constructs exact small-word XOR seed oracles, preserving selector and input and clearing all scratch. For each of eight normalized-mantissa segments, the circuit compares two **different bounded numerical seed functions**:

- An eight-segment affine Q-bit seed with exact rounded coefficient multiplication (K159 family).
- A Q-bit **surrogate** of the 64-entry K149 seed, using eight center-sample constants per segment.

Each alternative is separately synthesized using the same local-offset ANF and an explicit three-bit coherent segment match. A single clean segment-match wire and one monomial wire are reused. For every segment, the lower static CCX-cost alternative is chosen (CX breaks ties). **Each tested quantum input remains coherent; no computational-basis measurement decides its segment.** Classical ROM constants are compiled into gates, with no coefficient/product storage qubits.

## Local exact-gate results

| Q | Architecture | CCX | CX | Scratch | Cases |
|---:|---|---:|---:|---:|---:|
| 3 | all affine | 106 | 47 | 4 | 192 |
| 3 | all lookup surrogate | 78 | 28 | 4 | 192 |
| 3 | **hybrid** | **54** | **22** | **4** | **192** |
| 4 | all affine | 296 | 105 | 5 | 384 |
| 4 | all lookup surrogate | 176 | 60 | 5 | 384 |
| 4 | **hybrid** | **120** | **53** | **5** | **384** |
| 5 | all affine | 882 | 278 | 6 | 768 |
| 5 | all lookup surrogate | 198 | 103 | 6 | 768 |
| 5 | hybrid (all lookup selected) | 198 | 103 | 6 | 768 |

At Q4 the five-bit-output circuit selects lookup for segments 0,1,2,3,6 and affine for 4,5,7. All 8 segment values × 2^Q offsets × 3 arbitrary XOR targets were checked, including scratch cleanup and reversal/involution.

K163 global affine ANF at Q4 costs 440 CCX and 6 scratch; K167's **segmented affine-only** costs 296 CCX/5 scratch due to a different factoring strategy, and the **Q4 hybrid** costs 120 CCX/5 scratch. The small-word hybrid advantage is exact for this construction.

## Critical limitations

**This is not a full-domain or leaderboard win.** K149 uses a **Q14** table and the successful K159 computation uses Q14→Q26 Newton stages. Here the reference lookup seeds are rounded to Q3–Q5 and have very different bit patterns and zero/low-order behavior. The best bounded routing pattern **cannot be extrapolated** to Q14, and the separate full-domain numerical K166 pass does not establish which Q14 implementation has lower executed gate cost. At Q14, the ANF circuits would be exponential unless an efficient arithmetic/lookup structure is found. Method branching also incurs coherent selection overhead in a full implementation, with at most 12 spare scratch in K151's compact layout.

This circuit contains no K157 X-measurement-based carry uncomputation; that remains a separate active integration track.

## Run

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k167
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/98e0debb407f8a2cde71df669463ac4a9395e551/competition/k167/k167_hybrid.py -o competition/k167/k167_hybrid.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k167/k167_hybrid.py --selftest
"$PY" competition/k167/k167_hybrid.py --scaling
~~~

Output: competition/k167/results/cost_hybrid.json (full run requires SHA256-pinned immutable baseline).

**Next:** use K166's verified segment-error profile to test coarse/fine **Q14** seed routers with actual KMX gate library and optimize expected executed CCX+T-equivalent cost (not merely Q4 static gate sites). Keep baseline hotspot/source-parity reuse and K157 measurement carry independent active leads. No full 62-qubit KMX generated or verifier score claimed.
