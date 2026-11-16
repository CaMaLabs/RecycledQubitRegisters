# K168 — Q14 exact lookup, coherent segmented factoring

**Status:** locally checked gate-level, exact Q14 K149 lookup only. The complete K159 affine interpolation is **not priced or implemented at Q14**, and this is not a full Helios candidate.

K167 established that bounded Q3/Q4 hybrid routing can save gates, but used low-precision lookup surrogates. K168 uses the **actual 64 Q14 K149 seed constants** divided into eight segments with eight local 3-bit entries each. The 3-bit segment is kept quantum coherent and matched with reversible CCX gates; the local 3-bit address is synthesized through shared-ANF monomials that fan out into all 15 output bits. Classical ROM constants use zero coefficient qubits. No measurement of the selector occurs.

The local gate-level interpreter verified all **64 addresses × 3 initial XOR target values = 192 states**, including all scratch returned to zero, unchanged input registers and inverse behavior.

| Component | CCX | CX | X | Scratch | Total wires |
|---|---:|---:|---:|---:|---:|
| K168 exact segmented K149 Q14 table | **240** | **388** | 48 | **4** | 25 |
| K160 older unfactored ANF Q14 table | 1,365 | 33 | 8 | 4 | 24 |

Every K168 segment has 30 CCX in this construction (including coherent selection and reversal); the coefficient values have differing CX fanout. **This is a more efficient synthesis of the same 64-entry lookup, not a different numerical method.** Counts should not be directly compared as complete Helios circuits.

For K159's eight affine segments, K168 also prints each Q14 integer slope and its canonical signed-digit shifts. The eight slopes require 35 nonzero signed digits total. This is **static scheduling only**. Coherent offset-by-selected-slope multiplication, rounded subtraction, register liveness, normalization and K157 measurement-assisted cleanup have not been integrated or costed. Therefore K168 cannot defensibly select affine or lookup by segment at Q14 yet; lower CCX in lookup makes that comparison especially important.

### Run

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k168
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/5e451516c01b2cc1be20e6eddada46f04d1cc23e/competition/k168/k168_q14_cost.py -o competition/k168/k168_q14_cost.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k168/k168_q14_cost.py --selftest
"$PY" competition/k168/k168_q14_cost.py
~~~

Report: competition/k168/results/q14_cost.json.

**Next gate:** synthesize and validate at least one actual Q14 affine-seed segment with exact arithmetic and clean scratch, then compare its **fully counted** cost to the segment's 30-CCX Q14 lookup block. Do not present a hybrid optimization until this is done. K157 measurement-assisted carry and K158 original-source parity reuse remain live.
