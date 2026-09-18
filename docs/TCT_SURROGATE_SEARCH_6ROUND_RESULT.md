# TCT surrogate search — six-round compiler result

Date: 2026-09-18

## Scope

This records the zero-QPU six-round Grover-style compiler benchmark over the frozen 320-scenario FAIR-MAST-seeded TCT reduced-order search dataset.

The oracle in this benchmark is still a classically precomputed table oracle. It is therefore a compiler/workload measurement plus an idealized query-complexity comparison, not an end-to-end quantum speedup result.

## Search model

- Valid TCT scenarios: 320
- Marked low-loss scenarios: 8
- Index width: 9 qubits
- Padded search space: 512
- Idealized Grover iterations: 6
- Idealized success probability: 0.996586
- Expected classical random-without-replacement queries on the valid 320-state domain: 35.6667
- Idealized valid-domain random/Grover query ratio: 5.9444x
- Exhaustive-valid-candidates/Grover query ratio: 53.3333x

These are oracle-query ratios only. The current classical reduced-order surrogate is inexpensive, while the quantum oracle is a deep fault-prone circuit; no wall-clock advantage is claimed.

## Six-round interaction graph

- Logical width: 9
- Weighted logical edges: 24
- Total native 2Q interaction weight: 13,608
- Probe CZ: 13,608
- Probe depth: 55,825

The one-round probe had 2,268 CZ and depth 9,310. Thus:

- probe CZ scales exactly 6x;
- probe depth is almost exactly linear: 55,825 versus 55,860 from naive 6x scaling.

This indicates that repeating the Grover round does not create a new compiler blow-up in the probe construction.

## Preregistered physical-patch screen

The fusion workload was screened with the already-frozen rule:

`minimum interaction-distance bucket ∪ minimum physical-diameter bucket`

plus four deliberately sampled control patches.

### Fez heavy-hex

- candidate patches: 24
- compiled patches including controls: 10
- compile-count reduction: **58.33%**
- minimum predictor score: 24,516
- minimum physical diameter: 5
- best patch: 22
- best patch screen source: `minimum_physical_diameter`

### 10x12 square-lattice topology proxy

- candidate patches: 24
- compiled patches including controls: 15
- compile-count reduction: **37.50%**
- minimum predictor score: 19,764
- minimum physical diameter: 4
- best patch: 12
- best patch screen source: `minimum_physical_diameter`

This is useful cross-workload evidence that the topology-only screen can reduce compilation effort on the 9-qubit fusion-search circuit. It is not an exhaustive-recall result for this workload because the unscreened patches were not all compiled.

## Fez heavy-hex topology

Best fixed interaction layout:

- patch 22
- predictor rank 6
- predictor score 24,732
- diameter 5
- CZ 27,042
- depth 73,661
- size 121,422

Best Qiskit-auto on the same screened patch set:

- patch 22
- CZ 26,391
- depth 72,300
- size 119,543

Ratios:

- fixed / auto CZ = 1.0246675
- fixed / auto depth = 1.0188243

Qiskit auto is about 2.47% lower in CZ and 1.88% lower in depth. The custom logical mapper is not advantageous on this Fez workload.

## 10x12 square-lattice topology proxy

Best fixed interaction layout:

- patch 12
- predictor rank 14
- predictor score 20,412
- diameter 4
- CZ 24,226
- depth 66,458
- size 108,831

Best Qiskit-auto:

- patch 12
- CZ 24,213
- depth 66,734
- size 108,730

Ratios:

- fixed / auto CZ = 1.0005369
- fixed / auto depth = 0.9958642

The two mappings are effectively tied in CZ (fixed is only 13 CZ, ~0.054%, higher), while the fixed map is 276 layers (~0.414%) shallower. This is a tradeoff, not domination by either mapper.

## Comparison with one round

The logical probe scales essentially linearly, but routed hardware cost has topology-dependent overhead.

Fez auto:

- one-round CZ: 4,304; naive 6x = 25,824; measured = 26,391 (**+2.20%** over naive linear scaling)
- one-round depth: 12,069; naive 6x = 72,414; measured = 72,300 (**-0.16%** versus naive linear scaling)

Square-lattice proxy auto:

- one-round CZ: 3,845; naive 6x = 23,070; measured = 24,213 (**+4.95%**)
- one-round depth: 10,792; naive 6x = 64,752; measured = 66,734 (**+3.06%**)

For the fixed square-lattice mapping, scaling is closer to linear: 24,226 CZ versus 23,862 from naive 6x (**+1.53%**) and 66,458 depth versus 66,546 (**-0.13%**). This suggests the repeated oracle structure may narrow the fixed-vs-auto routing gap on this proxy, but that observation needs independent replication.

## What this supports

1. The idealized oracle-query opportunity for this 320-state/8-marked search is about 5.94x relative to random-without-replacement search on the valid domain.
2. Six Grover rounds compile without a qualitative resource explosion in this table-oracle construction.
3. The preregistered topology-only screen substantially reduces patch compilation work on this new 9-qubit workload, although exhaustive recall was not tested here.
4. The current custom logical mapper does not beat Qiskit auto on Fez for this workload.
5. On the square-lattice proxy, fixed and auto are essentially tied in CZ with a small depth advantage for fixed.
6. The present table oracle is the main remaining methodological limitation for any end-to-end quantum-search claim.

## Next experiment

Replace the precomputed marked-state oracle with a reversible implementation of the actual deterministic reduced-order TCT loss expression. The Mirnov/toroidal objective used in the sensitivity surface is low-order and factorized:

`loss = event_count * mean_severity * (1 - bias) * (1 - reachable * boost) + steady_cost + false_trigger_cost`

with the swept event-rate, bias, boost, and false-cost multipliers encoded directly in registers.

The next step is to export a fixed-point reversible-oracle specification and verify that its integer threshold reproduces exactly the 8 marked states before constructing the arithmetic circuit.

## Boundaries

- Zero QPU jobs.
- Fez results are topology/compiler results, not calibration/fidelity/timing measurements.
- Nighthawk remains a 10x12 square-lattice topology proxy.
- The TCT objective is a reduced-order FAIR-MAST-seeded control-policy proxy, not sustained-fusion validation.
- Query ratios do not include reversible surrogate evaluation cost, error correction, state-preparation cost, or QPU execution time.
