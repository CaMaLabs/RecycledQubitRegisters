# K157 — recycled first carry in a measured ripple adder

**Status 2026-11-16: standalone 14-bit arithmetic prototype with 12 carry scratch qubits, 27 CCX; not full Helios.**

K156 used 13 clean carry qubits for a 14-bit out-of-place XOR-adder, saving 25 CCX over Bennett cleanup but exceeding the 12 spare qubits in K151's nominal 50-bit storage layout. K157 eliminates one carry register without introducing an incorrect X-measurement phase.

## Construction

1. Compute c1..c12 from unchanged a,b and free carry registers c[0]..c[11].
2. XOR sum bit1 to z before erasing c1.
3. HMR-measure c1 and correct its phase using a conditional CZ(a0,b0).
4. **Reuse the now-clean c1 physical wire to compute c13**, then XOR remaining sum bits.
5. Release c13 down through c3 by X measurements in descending order, applying exact conditional CZ on the local carry polynomial with temporary CX parity conjugations.
6. With c13 released, recompute c1 into the same physical wire using CCX(a0,b0,c1), measure and phase-correct c2 using the restored c1, and then undo the temporary c1 using the second CCX.

The two extra CCX recover information required for the final phase correction. Simply releasing c1 and ignoring it during cleanup would be incorrect.

## Local verified gate-level counts

- 14-bit **K156** measured cleanup: 25 CCX, 13 carry scratch; 55 total wires for 3 14-bit words.
- 14-bit **K157** reused carry: **27 CCX, 12 carry scratch; 54 total wires** for 3 14-bit words.
- 14-bit conventional Bennett reference: 50 CCX, 13 carry scratch.
- Thus 23 CCX saved relative to conventional, with one fewer carry wire than K156.

The local test exhausted every a,b and both extreme initial output values and all measurement outcomes for n=4,5,6, and checked 500 random 14-bit a,b,output triples with 2,000 sampled measurement branches. Each checked branch has the same target arithmetic basis output, no remaining carry values, and zero relative phase. The phase-corrected X-branch argument extends to coherent superpositions of the tested states; it is not a full 14-bit exhaustive simulation. Conditional CX/CZ are **pseudoinstructions** in the simulator, not verified Kickmix grammar.

**Important limitation:** K151's input+estimate+delta compact representation has nominally 12 free wires. The standalone K157 adder needs 3 independent 14-bit words and 12 carry wires. Its 54-wire standalone size does not prove that the full Newton datapath can use the same wires without live-register conflicts, nor that the inverse-square-root arithmetic or phase application fits the global 62-qubit budget.

## Reproduce

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k157
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/61d25a51e05f534ddce5cd8b461f241801b94457/competition/k157/k157_recycled_carry.py -o competition/k157/k157_recycled_carry.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k157/k157_recycled_carry.py --selftest
"$PY" competition/k157/k157_recycled_carry.py
~~~

Output report: competition/k157/results/recycled_carry.json.

**Next planned architectural directions (requested):** (1) inspect the Helios circuit for *actually duplicated* exponent/normalization work and a valid compute/use/uncompute reuse schedule, not repeat prior generic ANF motif scans K135–K138; (2) try a cheap reversible log-derived seed and **benchmark it against K149's 64-entry seed** before any Newton multiplier implementation. Do not assert savings without scored gate and clean-scratch proof.
