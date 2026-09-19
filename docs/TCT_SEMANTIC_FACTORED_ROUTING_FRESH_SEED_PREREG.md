# TCT semantic-factored routing — fresh-seed preregistration

Date: 2026-09-19

## Purpose

Replicate the seed-118021 semantic/factored routing result on a fresh physical-patch ensemble without changing the oracle, predictor, screen rule, compilation settings, or evaluation criteria after seeing the new outcome.

## Frozen workload

- Source: classification-exact FAIR-MAST-seeded TCT reversible-oracle specification.
- Predicate: the already validated 8-state frozen TCT marked set.
- Oracle: shared-common-control, three-term ESOP implementation.
- Parameter bits: 9.
- Clean ancilla: 1.
- Logical width: 10 qubits.
- Grover rounds: 6.
- Statevector validation must remain `all_passed=True` before routing.

## Fresh patch seed

`271828`

This seed is frozen before running the fresh routing experiment.

## Frozen patch/search settings

- candidate patches per topology: 24
- control patches: 4
- mapping restarts: 96
- transpiler seeds: `8776,2026,9401`
- optimization level: existing routing-script default
- profile: existing routing-script default
- topologies:
  - authenticated IBM Fez heavy-hex connectivity
  - explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy

## Frozen deterministic screen

`minimum interaction-distance bucket ∪ minimum physical-diameter bucket`

The operational screened policy is:

`deterministic screen ∪ 4 random controls`

No tie-breaker or heuristic parameter will be changed after seeing the fresh-seed result.

## Evaluation

For each topology and each layout mode (`interaction_fixed`, `qiskit_auto`), report:

1. exhaustive global-best CZ and depth among the 24 sampled patches;
2. deterministic-screen optimum recall;
3. deterministic-screen CZ/depth regret if recall fails;
4. full screened-with-controls optimum recall and regret;
5. compile-count reduction of the screened policy;
6. predictor rank and diameter of each global optimum.

Primary success criterion for the screen is **zero CZ regret**; exact patch identity is secondary when multiple patches tie in CZ/depth.

## Anti-overfitting rule

Do not modify the screen based on the seed-271828 result. If the deterministic screen misses again, report the miss and regret as-is. Any new heuristic must be proposed only after this fresh replication and must be evaluated on a subsequent untouched seed.

## Claim boundaries

- Zero QPU jobs.
- Exhaustive only over the 24 sampled patches for each topology.
- Nighthawk/Phoenix remains a 10x12 square-lattice proxy unless exact hardware topology is authenticated.
- Fixed-instance Boolean/ESOP oracle only.
- No scalable coherent-surrogate claim.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
