# A113 — Routing robustness for A110

**Status:** Implemented and committed, awaiting local Ubuntu validation.

## Prior confirmed evidence

A112, IBM Fez read-only target local compilation at N2491 (five isolated controlled multiplier powers): 5/5 wins for A110 over frozen A97; sums 2,197,695 to 1,941,087 native two-qubit gates (−11.6762%) and 5,152,147 to 4,626,550 depth (−10.2015%). A112 used a single fixed seed and fixed 30-physical-qubit layout. Neither represents an executed quantum factoring job, and circuit depth sums are **not** full-QPE depths.

## A113 experiment

Test **5 powers × 2 connected physical layouts × 3 transpiler seeds = 30 matched comparisons** on IBM Fez. Each trial independently rebuilds A97 and runs the phase-exact conservative commuting-gate cancellation A110; both are compiled with the identical backend target, initial physical layout, optimization level and random seed. Keep logs of distinct trial costs, gate types, 28 sampled basis cases per architecture (with 8 probes in the existing audit contract), and the A110 canceled gate pair count.

Choose two distinct connected physical subsets with deterministic BFS roots and save exact layouts in settings. Run one comparison at a time by default and save each architecture individually; a repeated invocation resumes the checkpoint. Do not infer hardware fidelity or fault-tolerant speedup.

When complete, report per-trial and weighted 2Q/depth improvements, min/max 2Q improvement and count of improvements versus reversals. The pass criterion is wins in **both** metrics for all trials; mixed outcomes are reported, not hidden.

## First run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 600 "$PY" hardware/qrr_a113_ibm_routing_robustness.py \
  --backend-name ibm_fez --n 2491 --base 8 \
  --seeds 9401 9402 9403 --layout-count 2 \
  --max-new-trials 1 \
  --output results/a113_n2491_ibm_fez_robustness.json
echo "EXIT STATUS: $?"
```

Continue with the same command; each invocation completes one new trial. An outer `for i in $(seq 1 29)` loop can finish the remaining trials while retaining the checkpoint. No IBM job is submitted and no paid QPU runtime is needed.

## Follow-on

If the results remain robust, A114 should analyze actual Toffoli/Clifford+T decomposition, T-count/T-depth, ancilla and critical-path impacts at comparable logical functionality, then investigate whether the optimizer is novel relative to existing commuting-gate simplification in reversible synthesis.
