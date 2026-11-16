# K160 — priced reversible Boolean lookup comparison; interpolation still unpriced

**Status:** exact small-coherent-lookup X/CX/CCX networks reproduced locally for every selector with three different output targets and scratch reset. NOT a complete logarithmic seed / Newton circuit. No official KMX verifier.

The K159 full-domain Q14→Q26 8-segment chord seed numerically passes all 3,133,452 inputs and has better worst tolerance fraction (0.619301 vs K149 table's 0.801868). This does **not** prove a quantum resource win. K160 compares a specific identical ANF synthesis strategy applied to the 64-entry K149 table versus the 8-entry **intercept, slope, and origin** tables for K159.

| lookup | selector bits | data bits | exact CCX | CX | X | clean ancilla |
|---|---:|---:|---:|---:|---:|---:|
| K149 64 values | 6 | 14 | **1365** | 33 | 8 | 4 |
| K159 intercept | 3 | 15 | **56** | 23 | 1 | 1 |
| K159 slope | 3 | 13 | **37** | 16 | 7 | 1 |
| K159 origin | 3 | 16 | **4** | 4 | 1 | 1 |

**Coefficient lookup total: 93 CCX**; optional explicit origin table adds 4 (origin is dyadic and may be constructed more cheaply). The source uses an exactly specified Möbius ANF transform, decomposes each multi-controlled X using clean reversible CCX chains, and checks every selector with initial XOR target 0/all ones/alternating, including inverse and zero scratch. This is an exact gate-count result for the **particular circuit**, not a global optimal implementation of either lookup.

**Unpriced operations in K159:** extraction of normalized mantissa / selector, loading and clearing coefficient registers, selected-slope multiplication by the variable fraction \`(m - m0)\`, fixed-point rounding/truncation, subtraction, and complete reversible uncomputation. Although each individual slope is a classical constant, choosing the slope coherently means either multiplication with a quantum-valued selected coefficient or a multiplexed fixed-constant arithmetic network. Both can cost significant CCX and scratch. In a 62-qubit full datapath, holding both 15-bit intercept and 13-bit slope registers alongside 22-bit input and 14-bit output already costs 64 bits *before* any scratch, unless lifetime reuse/synthesis eliminates one register. Thus the lower lookup-only count **is not yet an architecture win**.

Comparison with K157: its 27 CCX / 12 carry scratch 14-bit standalone adder remains an active separate development and does not disappear from the registry.

## Run on Ubuntu

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k160
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/e3fd3492466fee39dda1832df9e5b6d033288895/competition/k160/k160_lookup_cost.py -o competition/k160/k160_lookup_cost.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k160/k160_lookup_cost.py --selftest
"$PY" competition/k160/k160_lookup_cost.py
~~~

Report: competition/k160/results/lookup_anf.json.

**Next decision gate:** implement a reversible *word-level* 8-segment seed with coefficient selection, interpolation, rounding, scratch cleanup and 62-qubit budget; compare its **total** scored CCX versus the 64-entry seed. For K158 inspect full windows including actual reset (R) and condition provenance before inventing duplicated exponent normalization.

## User Ubuntu reproduction (2026-11-16)

User independently reran `k160_lookup_cost.py` on Ubuntu and reproduced `K160_SELFTEST PASS`. Exact reports: K149 64-entry 14-bit seed 1,365 CCX / 33 CX / 8 X / 4 clean ancillas; K159 8-entry intercept 56 CCX / 23 CX / 1 X / 1 ancilla; slope 37 CCX / 16 CX / 7 X / 1 ancilla; origin 4 CCX / 4 CX / 1 X / 1 ancilla. All exact XOR table checks passed. Lookup-only CCX difference **1365 - (56+37+4) = 1268**, i.e. approximately **92.9%** of this reference lookup cost. Interpolation remains unpriced; there is no complete 62-qubit candidate or official score gain. Note that independently reported single-lookup ancillas do not prove safe concurrent allocation.
