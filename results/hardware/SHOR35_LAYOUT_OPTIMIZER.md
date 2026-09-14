# N=35 post-replication placement/routing optimizer

The 8-bit affine `N=35`, `a=2`, `r=12` hardware result was reproduced before starting this experiment.  The baseline affine runner remains unchanged for provenance.  Physical-layout optimization is therefore treated as a new experiment rather than folded retroactively into the successful baseline.

## Goal

Search for a better physical arrangement of the same exact affine circuits on the current IBM backend calibration while preserving the fair matched comparison:

- wide and recycled use the same four initial physical work-register sites;
- the recycled MCM ancilla is also one of the wide phase-register sites;
- no mathematical circuit change is made;
- no QPU time is spent during the search.

`hardware/ibm_shor35_layout_optimizer.py` enumerates calibration-aware candidate connected patches, chooses ordered work-register placements using the actual affine interaction pattern, transpiles the real 8-bit wide/recycled circuits at multiple deterministic seeds, and ranks the results using a calibration-weighted proxy built from CZ errors, MCM/readout errors, compiled CZ count, depth, and size.

The ranking score is explicitly a **placement-selection proxy, not a predicted circuit fidelity**.

## Zero-QPU search

Recommended first run:

```bash
python hardware/ibm_shor35_layout_optimizer.py \
  --backend ibm_fez \
  --phase-bits 8 \
  --optimization-level 3 \
  --candidate-plans 12 \
  --ancilla-pool 32 \
  --seeds 8776,20260914,314159 \
  --top 8
```

The program prints and saves:

- the historical heuristic layout recompiled under the current calibration snapshot;
- `recommended_matched`, optimized for the balanced matched comparison;
- `recommended_recycled_primary`;
- `recommended_wide_primary`;
- the top ranked matched alternatives.

The output JSON path is printed as `PLAN_FILE:`.

## Freeze the selected plan before QPU use

Use the separate runner so the replicated baseline script stays untouched:

```bash
python hardware/ibm_shor35_affine_plan_runner.py \
  --plan-file results/ibm_shor35_optimizer/<PLAN_FILE>.json \
  --selection recommended_matched \
  --backend ibm_fez \
  --shots 512 \
  --transpile-only
```

Review the exact compiled width/depth/size/CZ counts.  Only after that preflight should the optimized hardware experiment be submitted:

```bash
python hardware/ibm_shor35_affine_plan_runner.py \
  --plan-file results/ibm_shor35_optimizer/<PLAN_FILE>.json \
  --selection recommended_matched \
  --backend ibm_fez \
  --shots 512 \
  --max-execution-time 120 \
  --run
```

## Experimental interpretation

This is not part of the replication claim.  The original 8-bit affine result and its independent rerun establish the pre-optimization baseline.  The placement optimizer asks a new question: how much additional signal can be recovered by co-designing **algorithm + affine encoding + recycling schedule + physical placement/routing** for the backend calibration available at execution time?
