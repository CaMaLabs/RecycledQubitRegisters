# K162 — direct reversible affine-seed XOR oracle, no product or seed registers

**Status:** locally verified bounded Q3/Q4/Q5 exact reversible circuit, but scaling to full Q14 is not competitive. No full Helios or official score claim.

K161 materialized selected-slope arithmetic, partial products, and a seed register. At Q4 it passed 384 tests with 7,208 CCX, 24 scratch, 36 total wires. K162 bypasses those registers entirely by synthesizing the exact Boolean function of the segment selector and Q-bit fractional offset into the XOR output: \`|segment,offset,z,0> -> |segment,offset,z XOR [A(segment)-round(B(segment)*offset/2^Q)],0>\`. Coefficient integer rounding and affine expression match K161.

A Möbius/ANF transform synthesizes one polynomial per output bit. Each monomial is an X, CX or a multi-controlled X decomposed into clean-ancilla CCX chains. Every scratch bit is uncomputed before the next monomial, and input controls remain unchanged, so the XOR oracle is coherent on arbitrary superpositions. No mid-circuit measurements are needed for this design.

**Actual local gate-interpreter results:**

| Q | CCX | CX | scratch | total qubits | gate-level cases |
|---:|---:|---:|---:|---:|---:|
| 3 | 301 | 18 | 4 | 14 | 192 |
| **4** | **1,024** | **24** | **5** | **17** | **384** |
| 5 | 3,096 | 33 | 6 | 20 | 768 |

At Q4, 85.8% fewer CCX than K161 and 19 fewer scratch, but the full ANF table scales exponentially in Q+3 input bits. This is **not a practical Q14 route**; the small-case result is a compact exact proof of a low-scratch XOR-oracle alternative, not evidence of a Helios score improvement. K157's phase-correct measurement carry recycler remains an independent active avenue, as does K159's 8-segment seed numerical success.

## Run

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k162
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/46fd90c7e080e74d9d1d099abc87b99375691fdc/competition/k162/k162_direct_anf.py -o competition/k162/k162_direct_anf.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k162/k162_direct_anf.py --selftest
"$PY" competition/k162/k162_direct_anf.py --scaling
~~~

The pinned baseline SHA is checked on the full run. Output is \`competition/k162/results/direct_anf.json\`.

**Next objective:** keep K162's register lifetime advantage but replace the exponentially growing full-input ANF oracle with a **word-level arithmetic** circuit (multiplexed per-segment constant multiplication / carry propagation), resource-accounted within 62 qubits, ideally using K157's measurement-assisted cleanup where it demonstrably lowers total scored CCX.
