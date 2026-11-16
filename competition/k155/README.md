# K155 — controlled partial-product rows without operand buffer

**Result (2026-11-15): NEGATIVE COST TRADE-OFF.** Locally executed and gate-level verified. The separate shifted-row operand buffer in K154 is eliminated, but the 4-bit signed multiply-and-round implementation becomes **888 CCX**, compared with K154 **240 CCX**, while scratch falls only from **17 to 15**. No full-domain Helios candidate.

## Gate-level circuit

For r a signed 4-bit two's-complement number and y a 4-bit unsigned number, calculate floor((r*y + 16)/32) mod 16, XOR it into an arbitrary 4-bit output register, and return all scratch to zero.

Implementation adds individual controlled powers 2^(i+j) directly to an 8-bit product register rather than computing an independent shifted row. For the signed most-significant bit of r, it uses modular subtraction (conditional borrow tests). High-to-low bit updates preserve original carry/borrow controls. Computation is reversed after output extraction. All gates are X, CX, CCX.

The local Python interpreter verified all 4-bit 16×16 input pairs with three arbitrary output words each (768 cases), plus 2- and 3-bit widths. Involution and scratch cleanup were checked.

| Width | CCX | CX | X | Checked cases | Clean scratch |
|---:|---:|---:|---:|---:|---:|
| 2 | 76 | 4 | 18 | 48 | 7 |
| 3 | 314 | 5 | 42 | 192 | 11 |
| 4 | **888** | **6** | **82** | **768** | **15** |

K154 4-bit baseline was 240 CCX, 262 CX, 2 X, 17 scratch. Thus K155 **saves two scratch but adds 648 CCX**, and still exceeds the K151 12-scratch constraint. This is not the actual Q14×16-bit residual arithmetic.

## Mid-circuit measurement assessment

Useful only for particular styles of uncomputation. Measuring a live carry or residual in computational Z basis generally leaks information about the coherent input and changes the quantum channel.

For work holding a deterministic Boolean function f(x) of a coherent input, X-basis measurement with outcome m removes the work bit while imprinting phase (-1)^(m*f(x)) on the input. A conditional phase computation can cancel this, and the work bit can reset. The correction may itself be expensive for nonlinear carry/residual functions, and the exact state provenance must be proven. Helios already uses HMR and conditional phase repair, so there is no automatic new gain from introducing another HMR.

A sensible future test needs a **specific coherent arithmetic compute/use/uncompute chain** and an exact synthesized phase-repair network with fewer **scored** CCX than its reverse arithmetic. See K139–K143 and K147 for previously tested narrower patterns.

## Reproduction

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k155
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/0aec86eae30a18d6bce20877f930ee837b2b7eaa/competition/k155/k155_direct_rows.py -o competition/k155/k155_direct_rows.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k155/k155_direct_rows.py --selftest
"$PY" competition/k155/k155_direct_rows.py
~~~

The second command checks the pinned Helios source SHA and writes competition/k155/results/direct_rows.json.

**Next direction:** a word-level controlled ripple adder, or measurement-release applied to a specific proven arithmetic cleanup. Do not repeat direct bitwise multicon­trolled increments without an explicit new cost advantage.
