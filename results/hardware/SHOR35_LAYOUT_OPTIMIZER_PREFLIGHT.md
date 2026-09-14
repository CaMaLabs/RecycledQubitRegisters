# N=35 affine hardware-aware layout optimizer preflight

After the eight-bit affine `N=35`, `a=2`, order-12 result reproduced on a second IBM Fez hardware job, the next experiment froze the successful benchmark and searched physical placement and transpiler seeds without using QPU time.

The optimizer preserves the fair matched comparison: wide and recycled start with the same four physical work-register sites, and the recycled MCM ancilla is also one of the wide phase-register sites.

## Search configuration

- backend: `ibm_fez`
- phase bits: 8
- optimization level: 3
- candidate matched plans: 12
- ancilla pool: 32
- transpiler seeds: `8776, 20260914, 314159`
- selected seed: `8776`

## Recommended matched plan

- region: `[142,143,136,141,140,144,145,123,124,125,117,105]`
- shared initial work physical: `[136,143,141,140]`
- recycled ancilla: `142`
- wide phase physical: `[142,144,145,123,124,125,117,105]`
- recycled initial layout: `[142,136,143,141,140]`
- wide initial layout: `[142,144,145,123,124,125,117,105,136,143,141,140]`
- `measure_2` error on recycled ancilla: `0.00390625`
- local mean CZ error: `0.0021740729314653736`

The separate frozen-plan runner reproduced the optimizer's exact compiled resource counts in a zero-QPU-cost preflight.

| Metric | Legacy-current-calibration wide | Optimized wide | Legacy-current-calibration recycled | Optimized recycled |
|---|---:|---:|---:|---:|
| logical qubits | 12 | 12 | 5 | 5 |
| depth | 832 | **746** | 607 | **572** |
| size | 1447 | 1453 | 782 | **728** |
| CZ gates | 357 | 362 | 175 | **160** |

For recycled, the optimized placement reduces CZ count by about **8.6%**, depth by about **5.8%**, and circuit size by about **6.9%** relative to the legacy placement compiled in the same calibration snapshot.

For wide, CZ count is nearly unchanged, but depth falls by about **10.3%**. The optimizer also avoids very poor phase-readout sites present in the legacy plan: the worst requested wide phase-site readout error drops from about **8.41%** to **2.10%**, and the mean requested-phase readout-error proxy drops substantially.

The optimizer's calibration-weighted ranking value is a placement/routing proxy only, not a predicted hardware fidelity.

## Next experiment

The selected plan has cleared zero-QPU preflight and is ready for a matched same-job 512-shot hardware comparison using `hardware/ibm_shor35_affine_plan_runner.py --run`.

The purpose of the run is not to replace the replicated baseline. It tests a new hypothesis: whether explicit calibration-aware physical placement can further improve order-finding signal while preserving the same affine algorithm, precision, and matched-work-register design.
