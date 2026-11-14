# K146 — real upstream Polytof extraction and compiler/CPD trial

## What changed
K145's CCZ-only tool found zero regions containing at least two CCZs. K146 **does not repeat that gate filter**. It extracts bounded maximal unconditional unitary islands containing `X,CX,CCX,CCZ,H,Z,S,T`, preserving original gate order, from pinned 62q Helios KMX SHA256 `e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183`. At least two CCX/CCZ operations are required. A supplied synthetic three-CCX chain from Helios lines 25637–25639 passes exporter tests.

**Critical parser detail confirmed from actual upstream `src/circuit/parser_qc.h`:** Polytof .qc uses `tof a b c` for CCX, `cnot a b` for CX, `Z a b c` for CCZ, and `H` etc. The parser **does not support two-qubit CZ**. This adapter treats CZ and any unrecognized instruction as a hard barrier; it will never silently alter the operation.

## Original solver, not homemade imitation
`run_upstream_polytof.sh` clones the official https://github.com/ZIB-IOL/polytof if needed, builds and invokes its C++ `compile` (with tensor --idx), `bco` (actual beam basis change optimization), and `topp[1|2|6]` (actual SGE CP decomposition), on the **highest-ranked** exported multi-Toffoli region only, with 120-second caps. The CPD binary is selected from the **compiled** qubit width, not the source width.

Source: https://arxiv.org/abs/2602.15285 (revised October 26, 2026).

## Run on user's Ubuntu VM

```bash
cd ~/quantum-a26-check
mkdir -p competition/k146
BASE=https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/e3206115c19cc59e10b19b93047e419447ebf761/competition/k146
curl -fL "$BASE/k146_polytof_adapter.py" -o competition/k146/k146_polytof_adapter.py
curl -fL "$BASE/run_upstream_polytof.sh" -o competition/k146/run_upstream_polytof.sh
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k146/k146_polytof_adapter.py --selftest
bash competition/k146/run_upstream_polytof.sh
```

Reports:
- `competition/k146/results/extraction.json` — actual eligible units; original line numbers/width and Toffoli count; top .qc exports.
- `compile.log`, `bco.log`, `cpd.log` — genuine upstream C++ output.
- `competition/k146/results/upstream_trial.json` — original width, compiled gadget width, new ancillas, rank.

**This is a compatibility/extraction trial, not an optimization proof.** Upstream compiler may gadgetize internal Hadamards into ancillas and assumes measurement outcomes. Exact channel equivalence and a qubit-neutral output mapping have **not** been demonstrated, nor has any actual reduced KMX been generated. A favorable CPD rank is merely a lead, not a leaderboard improvement. Do not splice upstream pre/post circuits into Helios or submit anything without explicit end-to-end equivalence and full verifier checks.

## Gates
1. `eligible_islands=0`: stop; this upstream translator doesn't apply without new exact handling of barriers.
2. `eligible_islands>0`: run original compiler and CPD; record **new_ancillas** and rank.
3. If ancilla expansion is substantial, the 62q score makes a replacement unlikely economically. Reject before investing in circuit reconstruction.
4. If a candidate has headroom, *then* implement exact end-to-end reconstruction with output invertible map, phase corrections, measurement histories, and official full-domain check.

## Actual upstream result (user's Ubuntu VM, 2026-11-14)

The complete K146 runner finished successfully using the **real upstream Polytof** code.

- Exported 254 candidate unitary islands. Top: Helios lines **34789–34916**, 128 instructions, 33 occupied qubits, **23 CCX**, 0 source CCZ, 0 source H.
- Upstream `compile 7145 --idx`: 33q input, 49q output (**+16 gadget ancillas**), 161 T before merge, 135 T after merge, 77 sparse tensor nonzero terms.
- Upstream `bco 7145 -b 2 --save --verify`: tensor `nnz 77 → 23` (70.1% reduction), verified. This is NOT equivalent to a reduction in Toffoli count.
- Upstream `topp1 8145 --sge -b 2 --save --verify`: trivial rank 23, optimized CP rank **23** (no Toffoli reduction), verification reported ok.
- C++15 `cnpy.h` compile warnings appeared but build and pipeline succeeded.
- No synthesized candidate was generated, no exact Helios channel equivalence tested, no official verifier score measured. The upstream tensor's transformed 49q representation **cannot be inserted into the 62q Helios circuit** without proving ancilla initialization, liveness and cleanup; automatic addition would grow global 62q→78q. In that naïve mapping, up to 23 CCX saved cannot compensate 16 additional scored qubits (theoretical delta would be unfavorable). Existing 29 qubits not touched in the island do **not** automatically count as clean available ancillas.

**Outcome: K146 TOP ISLAND NO SCORE WIN**. Do not mistake BCO's 70.1% sparse tensor compression for a scored gate reduction. CPD (SGE beam 2) not finding a rank reduction does not prove tensor rank is optimal.

**Next research gate:** before spending further effort on FGS or other regions, establish whether the original solver has a qubit-neutral, exact extraction/reconstruction mechanism. If not, this published pipeline is not a practical drop-in for Helios's 62q objective, and its benefits must be restricted to algebraic insight rather than a circuit replacement.
