# TCT surrogate search compiler v1 result

Date: 2026-09-18

## Scope

This result compiles one Grover iteration for a frozen FAIR-MAST-seeded TCT reduced-order search surface exported from `Fusion_Blanket_Design_TCT`.

The search dataset contains 320 valid TCT parameter scenarios and 8 marked low-loss scenarios. The 320-state valid domain is represented on 9 index qubits by padding to 512 basis states.

This is a zero-QPU compiler/workload experiment over a classically precomputed table oracle. It does **not** include coherent reversible evaluation of the fusion surrogate and therefore does not establish end-to-end quantum speedup.

## Search dataset

- valid candidates: 320
- marked candidates: 8
- index qubits: 9
- padded search space: 512
- idealized optimal Grover iterations: 6
- idealized success probability at 6 iterations: 0.996586
- classical random without replacement, expected valid-domain queries: 35.6667
- idealized valid-random / Grover query ratio: 5.9444x
- exhaustive-valid-candidates / Grover query ratio: 53.3333x

The current lowest reduced-order objective point exported by the fusion model was:

- standing bias: 0.35
- boost reduction: 0.70
- false-trigger cost multiplier: 0.0
- event-rate multiplier: 0.25
- realizable winner: `baseline_mirnov_fast_boost`
- objective (`mirnov_toroidal_loss`): 66.1296401261

## One-round interaction graph

The compiled one-round Grover workload produced:

- logical width: 9
- weighted logical edges: 24
- total two-qubit interaction weight: 2,268
- all-to-all probe CZ: 2,268
- probe depth: 9,310

This interaction structure differs substantially from the earlier 8-qubit recycled-QPE mapper benchmark and is therefore a useful generalization workload.

## Compiler results

### Fez heavy-hex topology

Best custom fixed layout:

- patch: 22
- predictor rank: 6
- predictor score: 4,122
- patch diameter: 5
- screen reason: minimum physical diameter
- CZ: 4,405
- depth: 12,367

Best Qiskit auto layout on the screened set:

- patch: 22
- CZ: 4,304
- depth: 12,069

Fixed / auto:

- CZ ratio: 1.0234665
- depth ratio: 1.0246914

Thus Qiskit auto used about 2.35% fewer CZ and about 2.47% lower depth than the current custom fixed mapper on this workload.

### 10x12 square-lattice proxy

Best custom fixed layout:

- patch: 12
- predictor rank: 14
- predictor score: 3,402
- patch diameter: 4
- screen reason: minimum physical diameter
- CZ: 3,977
- depth: 11,091

Best Qiskit auto layout on the screened set:

- patch: 12
- CZ: 3,845
- depth: 10,792

Fixed / auto:

- CZ ratio: 1.0343303
- depth ratio: 1.0277057

Thus Qiskit auto used about 3.43% fewer CZ and about 2.77% lower depth than the current custom fixed mapper on this proxy workload.

## Interpretation

The first TCT-search workload does **not** support a claim that the current custom logical mapper improves over Qiskit auto-layout. On both tested topology models, Qiskit auto was better in CZ and depth on the best screened patch.

The useful result is instead that the TCT parameter-search problem maps naturally to a narrow 9-qubit Grover-style workload and gives an idealized oracle-query reduction of about 5.94x versus random search expectation over the valid domain, or 53.3x versus a full 320-point exhaustive scan.

Those query ratios are algorithmic/oracle-model quantities only. The present table oracle was classically precomputed, and the cost of reversible surrogate evaluation is not yet included. Because the classical reduced-order TCT model is itself inexpensive, no wall-clock quantum advantage is implied by these numbers.

## Next test

Compile the full six-round Grover circuit using the same frozen dataset and screened patch protocol:

```bash
python3 integrations/tct_surrogate_search/benchmark_tct_surrogate_search.py \
  "$DATASET" \
  --grover-rounds 6 \
  --candidate-patches 24 \
  --patch-seed 118021 \
  --transpiler-seeds 8776,2026,9401 \
  --out results/tct_surrogate_search/tct_surrogate_search_compiler_6round.json
```

This measures the actual compiled six-query circuit cost instead of extrapolating linearly from one round.

After that, the stronger experiment is to replace the lookup-table phase oracle with a reversible implementation of the reduced-order objective or a compact polynomial surrogate, so oracle construction cost is part of the comparison.

## Boundaries

- Zero QPU jobs.
- Fez result is topology/compiler-only, with no calibration/fidelity/timing claim.
- Nighthawk side remains a 10x12 square-lattice proxy, not authenticated Phoenix performance.
- The fusion model is reduced-order and FAIR-MAST-seeded; this does not validate TCT physics.
- Table-oracle Grover query counts do not establish practical quantum advantage.
