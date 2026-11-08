# A108 — Frozen A97 multiplier bottleneck audit

**Status:** committed, awaiting Ubuntu execution. No A108 gate savings asserted.

## Goal

Keep A97 as the frozen reference after A106's negative complete-multiplier result (N15 A106 31,378 CX vs A97 3,086 CX, 59 vs 14 qubits, 46,347 vs 5,165 circuit depth). Before proposing A109 architectural changes, locate which portions of the **actual complete A97 multiplier** dominate.

## Method

`hardware/qrr_a108_a97_multiplier_hotspot_audit.py` independently rebuilds the exact A97 source circuit using the same adders and per-constant native-CX selection heuristic. It verifies every source gate against A97 (name, indices, control state, and parameters). At N35 it also runs exhaustive controlled-multiplier basis inputs with clean work registers unless `--skip-basis` is explicitly used.

The audit records source operation intervals for:
- Enable/validity predicate computation and cleanup;
- Forward controlled modular additions, one per partial-product bit;
- Controlled register swaps;
- Inverse-multiply uncomputation additions.

For each interval, it compiles a standalone diagnostic subcircuit and records native CX and depth. **These isolated section costs are not additive to the full circuit's transpiled CX count and do not establish critical-path depth attribution**, because cross-interval optimizations and cancellations are lost. The complete A97 multiplier is separately compiled to record the authoritative full-circuit count.

## A107 phase postprocessing sanity audit

Existing `results/a107_n15_qpe.json` and `results/a107_n35_qpe.json` are read locally. The script recomputes the exact, exhaustive uniform-frequency factor recovery rate and phase-lattice hit rate for every possible measured frequency, and compares these to the A107 recorded exact null. It also compares the actual ideal-Aer factor recovery ratio to the **uniform frequency null**. This is a useful sanity test but **not a matched physical noise or classical-work comparison and does not establish quantum advantage**.

## Run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 300 "$PY" hardware/qrr_a108_a97_multiplier_hotspot_audit.py \
 --n 35 --a 8 --level 1 \
 --qpe-results results/a107_n15_qpe.json results/a107_n35_qpe.json \
 --output results/a108_n35_a97_hotspots.json
```

## Promotion decision for A109

A108 must pass exact frozen-circuit reconstruction and independent baseline compilation before any change is attributed to a proposed optimization. A109 candidates must be exact reversibly, preserve A97's qubit count initially and beat **complete multiplier** costs—not only isolated arithmetic kernels. Literature comparisons will need matched logical functions and fault-tolerant resource metrics.
