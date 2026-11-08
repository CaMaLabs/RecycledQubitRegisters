# A110 — Commutation-aware cancellation of A97 source arithmetic

**Status:** Committed; local execution pending. No performance benefit is yet established.

## Motivation

A108 found most isolated source-region cost in forward modular addition and inverse cleanup. A109 tested 12 per-constant replacements at N35; none improved the complete A97 multiplier. A110 tests a distinct search space: remove redundant reversible operations that are separated by gates with which they **provably commute**.

## Safe algebraic transformation

For an involution `G`, `G * H1 * H2 * ... * Hk * G = H1 * H2 * ... * Hk` whenever each `Hj` commutes with `G`.

The A97 source consists of X, CX, CCX, open-control MCX and controlled-SWAP gates. All are reversible permutations with no relative phase. For XOR-target gates, two gates commute provided the write target of neither is among the other gate's control bits. Sharing controls or a common XOR target is allowed when that condition holds. To stay conservative, controlled swaps are moved only past disjoint operations.

The pass removes identical gate pairs separated solely by commuting gates, repeating to a fixed point. This is a provably phase-preserving rewrite on the supported source gates, not merely a classical truth-table heuristic.

## Evidence and promotion gate

The script constructs the original frozen A97 multiplier, performs the rewrite, and independently verifies each whole multiplier exhaustively for N35. Both circuits are transpiled with the same `u/cx` basis, seed and optimization level; only the **complete compiled circuit** cost counts. Required: identical reversible behavior, clean scratch, no new qubits, and both lower native CX **and** depth to earn promotion. A no-win result is retained as a negative result.

A110 is deliberately limited: it will not discover conditional arithmetic identities that require resynthesis or nontrivial ancilla management. Qiskit's optimizer may already remove much of the same redundant work. Do not overstate novelty.

## Run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 300 "$PY" hardware/qrr_a110_commuting_gate_cancellation.py \
  --n 35 --a 8 --level 1 \
  --output results/a110_n35_commuting_cancellation.json
echo "EXIT STATUS: $?"
```

Next if no win: explore constant-specific specialized arithmetic or controlled-adder cancellation across a larger algebraic rewrite window, while retaining reversible exactness as a hard gate.
