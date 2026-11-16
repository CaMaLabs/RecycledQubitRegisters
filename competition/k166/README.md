# K166 — hybrid by range, classical ROM, coherent arithmetic and measured cleanup

**Status (2026-11-16):** locally tested range-screen and a separate exact bounded coherent selected-row arithmetic primitive. No full Helios KMX submission and no official score change.

## Two distinct experiments

**Full-domain numerical comparison:** Uses K159's Q14 → Q26 mixed-precision Newton implementation and compares two Q14 seeds (K149 64-entry lookup versus K159 eight-segment chord-affine seed) on every integer x=1..3,133,452. All eight normalized mantissa intervals have **zero numerical violations for both seeds**. K159 chord-affine gives smaller *worst-case relative error* in all eight, but individual inputs can favor either; the method with the best numeric worst case is not necessarily cheapest to implement. The evaluated fixed-point arithmetic is a numerical model, not a Q14 quantum circuit.

**Actual bounded reversible arithmetic primitive:** Compiles four 5-bit bitmask constants into gates; selector (2 qubits) and operand (5 qubits) remain coherent. A selected partial row is prepared by controlled CCX gates, used with an out-of-place sum-XOR adder, and uncomputed after addition. Conventional Bennett cleanup uses K156; measured cleanup uses K157's phase-correct carry recycling. All 384 sampled input/selector/output states and **6,144 distinct measurement branches** had exact arithmetic, zero residual phase and fully cleared scratch. The selector and operand are **not measured**.

| Bounded five-bit row-add design | CCX | Carry+flag scratch | Other |
|---|---:|---:|---|
| Conventional coherent reversal | 50 | 5 | 4 carry plus 1 flag |
| X-basis measurement with exact phase repair | **45** | **4** | 3 carry plus 1 flag, 4 HMR and 7 conditional CZ |

Thus the selected-row example saves **5 CCX** and **1 scratch**. The masks are an illustrative four-entry classical table, **not the actual Q14 K159 slope coefficients**. The measured circuit uses pseudoinstructions HMR/CZ_IF/CX_IF interpreted by the K157 phase-aware checker, and requires actual legal Kickmix measurement-feedback support before claiming a competition benefit.

**Classical lookup storage vs quantum operands:** Coefficients, schedules, static masks, and classical measurement results can be stored in ordinary classical data. Compiling a ROM into controlled gates avoids holding the table *contents* in quantum registers; however, a selector in superposition must be processed coherently, and gate cost does not disappear. Unknown, live quantum operands cannot be measured into classical memory without generally destroying the required input/output coherence. X-basis measurement of eligible garbage plus phase feedforward is a narrower safe technique, subject to exact proof.

## Reproduce on user's Ubuntu setup

Requires already downloaded experiments K156, K157 and K159.

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k166

curl -fL \
  https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/500d266e0f59352063376ead004c27dbe553e757/competition/k166/k166_range_hybrid.py \
  -o competition/k166/k166_range_hybrid.py

PY="$HOME/.venvs/kaggle-k001/bin/python"

"$PY" competition/k166/k166_range_hybrid.py --selftest
"$PY" competition/k166/k166_range_hybrid.py
~~~

The full run SHA-checks the pinned baseline and writes competition/k166/results/hybrid.json. The full-domain numerical screen reports eight K166_RANGE lines.

**Next gate:** compare actual executed-score costs for a **coherent range-selectable implementation of the real Q14 seed**. A classical per-input range decision is only available when the competition's input is truly classical, not when it must be a coherent oracle on superpositions. More practical: find portions of the fixed Helios circuit that demonstrably permit phase-correct HMR cleanup; test legal syntax and full verifier rather than repeatedly rebuilding arithmetic exceeding the 62-qubit budget. Maintain K157/K158/K159/K160/K165 as independent active leads.
