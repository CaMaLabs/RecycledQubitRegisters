# K156 — measurement-assisted coherent carry release vs Bennett uncomputation

**Date:** 2026-11-16. **Verified local small-word coherent quantum-channel equivalence and scored-gate reduction; NOT a full Helios implementation or leaderboard win.**

## Reversible target

Two n-bit input words a and b remain unchanged, as does an arbitrary initial z except that the circuit XORs their modular sum into it:

    |a,b,z,0^c> → |a,b,z XOR ((a+b) mod 2^n),0^c>

A ripple carry is c_(i+1) = a_i b_i XOR ((a_i XOR b_i) c_i), with c_0=0. For i>=1 the compute costs two CCX (plus two CX for the temporary parity) and the first carry costs one CCX. It uses n-1 clean carry qubits. The old reversible Bennett scheme performs the same compute, XORs the sum into z, and then reverses the entire carry network.

K156's measurement-release scheme instead, in descending carry order:
- X-measures c_(i+1) via HMR, obtaining classical bit m.
- Applies CZ(a_i,b_i) if m.
- If i>0, computes temporary parity (a_i XOR b_i) with CX, applies CZ(parity,c_i) if m, and restores the parity with CX.
- Resets/releases the measured carry qubit.

The phase from measurement is (-1)^(m*c_(i+1)), and the two conditional CZ terms apply the identical phase because of the exact carry identity. The pair cancels. All correction steps are Clifford and controlled by classical measurement outcomes. This **retains quantum coherence**, unlike measuring live carries in the Z basis.

## Exact proof scope

Python performs **gate-by-gate** basis-state evolution for both arithmetic networks. For EVERY X-measurement outcome branch, it tracks the phase introduced by HMR and the corrections and requires the final state to match the coherent Bennett result with **zero residual relative phase**. Uniform branch probability 2^(-(n-1)) then proves equality on arbitrary coherent superpositions by linearity for the tested inputs (and their entangled references). The z-register starts in arbitrary tested basis values; for widths 3..5, selected nonzero z values are tested, not all z combinations.

| n | Bennett CCX | X-measured CCX | Saved CCX | Measured carry qubits | Outcome branches checked |
|---:|---:|---:|---:|---:|---:|
| 2 | 2 | 1 | 1 | 1 | 128 |
| 3 | 6 | 3 | 3 | 2 | 768 |
| 4 | 10 | 5 | 5 | 3 | 6,144 |
| 5 | 14 | 7 | 7 | 4 | 49,152 |

Formula n=14 (static gate counts of this standalone construction): **50 CCX Bennett** vs **25 CCX measured**, saving 25, using **13 clean carry qubits** and **55 total logical qubits** when a,b,z are all 14 bits. This is NOT an integrated Helios result: the K151 Newton layout has only 12 nominally free qubits, and requires products, precision shifts, seed lookup and phase application.

### Block-size caveat

A naïve attempt to release carry chains between blocks does **not** automatically solve the 13-versus-12 scratch shortage. The correction for measuring c_i depends on c_(i-1), so measuring earlier carries before the boundary carry is released changes which correction information remains available. Block streaming requires a new exact phase-correction strategy or recomputation, both of which must be separately counted and proven.

### Kickmix caveats

The pseudoinstructions CZ_IF/CX_IF in this experiment mean **a CZ or CX performed only when a classical HMR measurement bit equals one**. They are NOT claimed to be valid Kickmix syntax. Full compiler support, phase-correction semantics, execution cost, and the official verifier's legality remain untested.

K139–K143 studied existing HMR feedback; K147 found no strict preexisting clean-target CCX-use-inverse pattern. K156 is different: a **purpose-designed ripple adder** with explicit mid-circuit carry X-measurement and correction, proving a local exact resource win. It is not a drop-in replacement for the pinned Helios baseline.

## Run on Ubuntu

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k156
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/c8c9eee7d892b095a33976ecc08c1714c23d04d2/competition/k156/k156_ripple_measure.py -o competition/k156/k156_ripple_measure.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k156/k156_ripple_measure.py --selftest
"$PY" competition/k156/k156_ripple_measure.py
~~~

Output: competition/k156/results/measurement_carry.json; pinned baseline SHA checked. No full Helios candidate generated.

**Next gate:** apply the measurement-release primitive to an actual arithmetic operation in a proposed 62-qubit Helios architecture, including a legal bit-conditioned Clifford control, width accounting, and exact total executed-gate advantage over the official baseline. Avoid assuming the full residual 16-bit multiplication becomes free.
