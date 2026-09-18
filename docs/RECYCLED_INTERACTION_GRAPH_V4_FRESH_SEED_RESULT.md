# Recycled interaction-graph v4 fresh-seed result

Date: 2026-09-18

This document records the first fresh-seed falsification run of the frozen v4 screen preregistered in `docs/RECYCLED_INTERACTION_GRAPH_V4_PREREG.md`.

## Run identity

- Patch seed: `118021`
- Exhaustive candidate count: 48 patches per topology
- Logical width: 8
- Weighted logical interaction edges: 28
- Total two-qubit interaction weight: 20,794
- Zero QPU jobs
- Fez result uses authenticated heavy-hex topology only; no calibration/fidelity/timing claim
- Nighthawk result remains the 10x12 square-lattice topology proxy, not authenticated Phoenix hardware

The dominant learned post-HLS interactions in this run were:

| Logical pair | Weight |
|---|---:|
| `phase_recycled` ↔ `scratch[0]` | 2378 |
| `phase_recycled` ↔ `work[0]` | 2218 |
| `work[3]` ↔ `work[5]` | 2088 |
| `work[0]` ↔ `scratch[0]` | 1810 |
| `work[0]` ↔ `work[3]` | 1352 |
| `phase_recycled` ↔ `work[3]` | 1168 |
| `work[0]` ↔ `work[2]` | 1136 |
| `phase_recycled` ↔ `work[1]` | 1118 |
| `work[1]` ↔ `work[3]` | 1108 |
| `work[3]` ↔ `work[4]` | 1108 |

## Frozen predictor validation

### Fez heavy-hex topology

- Exhaustive compiled patches: 48/48
- Spearman `score` vs native CZ: **0.9787081236**
- Spearman `score` vs compiled depth: **0.9653684256**
- Predicted top-1 fixed layout: patch 4, score 36,340, CZ 55,145, depth 117,350
- Global-best fixed layout: patch 27, predictor rank 4, score 36,340, CZ 54,796, depth 118,000
- Global-best Qiskit-auto: patch 47, predictor rank 8, score 36,340, CZ 54,866, depth 117,167
- Best-fixed / best-auto CZ ratio: **0.9987241643**
- Best-fixed / best-auto depth ratio: **1.0071095104**

Interpretation: the frozen interaction-distance score is strongly monotone with both CZ and depth across the exhaustive patch set, but the score has ties. The exact logical mapping beats the best auto-layout result slightly in CZ in this run (~0.128%) while losing on depth (~0.711%). This does not establish fixed mapping as universally superior to Qiskit auto-layout.

### 10x12 square-lattice topology proxy

- Exhaustive compiled patches: 48/48
- Spearman `score` vs native CZ: **0.9681172407**
- Spearman `score` vs compiled depth: **0.9588199901**
- Predicted top-1 fixed layout: patch 7, score 30,118, CZ 43,013, depth 102,507
- Global-best fixed layout: patch 22, predictor rank 5, score 30,118, CZ 42,888, depth 102,278
- Global-best Qiskit-auto: patch 20, predictor rank 4, score 30,118, CZ 42,669, depth 101,798
- Best-fixed / best-auto CZ ratio: **1.0051325318**
- Best-fixed / best-auto depth ratio: **1.0047152203**

Interpretation: predictor correlation again remains strong, but Qiskit auto-layout is modestly better than the best fixed mapping in both CZ (~0.513%) and depth (~0.472%) for this proxy ensemble. The useful result is therefore the predictor's ability to rank/select physical patches, not a claim that the custom logical permutation always outperforms Qiskit routing.

## V4 preregistered screen result

The frozen v4 rule was:

`minimum interaction-distance bucket ∪ minimum induced-subgraph-diameter bucket`.

No compiled CZ/depth outcome was used to form the screen.

### Fez heavy-hex

- Minimum-distance bucket: 8 patches
- Minimum-diameter value: 5
- Minimum-diameter bucket: 9 patches
- Union: **9/48 patches**
- Compile-count reduction: **81.25%**
- Fixed-layout global optimum recall: **true**
- Fixed-layout CZ regret: **0.000%**
- Qiskit-auto global optimum recall: **true**
- Qiskit-auto CZ regret: **0.000%**
- Baseline v3 minimum-distance bucket also recalled both optima with 0.000% CZ regret in this seed

### 10x12 square-lattice proxy

- Minimum-distance bucket: 11 patches
- Minimum-diameter value: 4
- Minimum-diameter bucket: 31 patches
- Union: **31/48 patches**
- Compile-count reduction: **35.42%**
- Fixed-layout global optimum recall: **true**
- Fixed-layout CZ regret: **0.000%**
- Qiskit-auto global optimum recall: **true**
- Qiskit-auto CZ regret: **0.000%**
- Baseline v3 minimum-distance bucket also recalled both optima with 0.000% CZ regret in this seed

## Preregistered falsification outcome

This fresh seed **passes the preregistered v4 success criterion**: for both tested topologies, the union screen retained the global-best fixed and auto patches with zero CZ regret while reducing compilation count.

The result is stronger on Fez for screening efficiency (81.25% fewer patch compilations) than on the square-lattice proxy (35.42% fewer). The result does **not** establish universality. In particular, the baseline v3 bucket also happened to succeed on this fresh seed, so this run alone does not show that the diameter challenger is necessary or superior. Its motivation remains the prior independent square-lattice seed where v3 missed the optimum.

## What this now supports

Within the current exact small-N, compiler/topology model:

1. The learned post-HLS weighted interaction graph is a strong predictor of routing cost across independently sampled physical patches in this fresh ensemble.
2. A preregistered topology-only screen can reduce the number of expensive compilations while retaining the true optimum in this seed.
3. Custom fixed logical mapping and Qiskit auto-layout are close competitors; neither is uniformly superior in these results.
4. Score ties are now a visible remaining weakness: several distinct patches share the same minimum weighted-distance score even when their compiled CZ differs slightly.

## Next falsification

Do not refit on seed `118021`. The next test should keep the v4 rule frozen and run additional fresh patch seeds, then cross N/base/work-width cases. A useful next predictor revision may add an explicitly preregistered tie-breaker only after those replications, rather than fitting one to this successful seed.

## Boundaries

- Zero QPU jobs.
- No hardware fidelity, execution-time, reset-speed, or calibration claim.
- `nighthawk_square_lattice_topology` is a topology proxy only.
- Exact full-register small-N modular permutation synthesis remains non-scalable to RSA-sized arithmetic.
- This is evidence about compiler/topology screening, not evidence of a quantum computational speedup or hardware advantage.
