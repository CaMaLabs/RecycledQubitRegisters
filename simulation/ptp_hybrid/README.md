# `simulation/ptp_hybrid`

Optional, falsification-first research track for testing whether modulo-210 PTP/kernel-factor structure adds measurable leverage to QRR.

This directory does **not** modify the established QRR hardware experiments.

## Current scope

Implemented now:

- programmatic 48-root modulo-210 core;
- exhaustive prime/root checks;
- generated 24/28 factor-pair table;
- kernel coordinates and LFK-style classical reference search;
- plain and wheel-210 factoring baselines;
- composite mirror/symmetry reproduction;
- fixed-N symmetry falsification gate;
- conservative standard-vs-PTP Shor order postprocessing control;
- deterministic benchmark matrix and raw JSON/CSV output.

Not yet promoted to hardware:

- any PTP-aware circuit optimization;
- any base-selection/order-prediction rule;
- any N=21/N=35 PTP hardware runner.

## Run

From the repository root:

```bash
python -m unittest simulation.ptp_hybrid.test_ptp_hybrid -v
python simulation/ptp_hybrid/core.py
python simulation/ptp_hybrid/symmetry.py
python simulation/ptp_hybrid/benchmark.py --seed 8776 --generated 24
```

Expected output files from the benchmark:

```text
results/ptp_hybrid/ptp_hybrid_benchmark.json
results/ptp_hybrid/ptp_hybrid_benchmark.csv
```

The benchmark contacts no quantum backend.

See `docs/PTP_QRR_RESEARCH.md` and `docs/PTP_QRR_NOVELTY_AUDIT.md` for the research/claim boundaries.
