# Independent placement replication result

## Scope

This result is a zero-QPU compiler/topology study for the repository's exact small-N full-register modular-permutation construction. It is **not** a calibrated QPU result, not a fidelity/runtime claim for IBM Nighthawk r2, and not a scalable RSA resource estimate.

The replication used a fresh stochastic subgraph seed and multiple transpiler seeds. The primary analysis excluded deterministic patch 0 so the reported best-placement results come only from fresh stochastic placements.

## Primary replication criterion

The preregistered question was whether a placement-aware search could independently reproduce the discovery advantage of the recycled construction over the wide construction. The relevant quantities are therefore the **best-of-fresh-placement** recycled/wide ratios. Median ratios answer a different question: how a typical random placement behaves without placement optimization.

The primary replication passed at every tested phase precision and on both topology models:

| Phase bits | Topology | Width wide -> recycled | Best R/W CZ | CZ reduction | Best R/W depth | Depth reduction |
|---:|---|---:|---:|---:|---:|---:|
| 16 | Fez heavy-hex | 23 -> 8 | 0.9482 | 5.18% | 0.9799 | 2.01% |
| 16 | Nighthawk-style square-lattice proxy | 23 -> 8 | 0.9518 | 4.82% | 0.9772 | 2.28% |
| 32 | Fez heavy-hex | 39 -> 8 | 0.9173 | 8.27% | 0.9784 | 2.16% |
| 32 | Nighthawk-style square-lattice proxy | 39 -> 8 | 0.9330 | 6.70% | 0.9840 | 1.60% |
| 64 | Fez heavy-hex | 71 -> 8 | 0.8940 | 10.60% | 0.9765 | 2.35% |
| 64 | Nighthawk-style square-lattice proxy | 71 -> 8 | 0.9171 | 8.29% | 0.9845 | 1.55% |

Thus the fresh-placement search reproduced a circuit with fewer CZ gates **and** lower compiled depth than the independently optimized wide circuit in all six tested cases, while using substantially fewer qubits.

At 64 phase bits the recycled construction used 8 qubits instead of 71, an 88.73% width reduction. On fresh placements the best Fez compile used 109,443 CZ versus 122,414 CZ for wide, while the Nighthawk-style proxy used 85,416 CZ versus 93,135 CZ.

## Median-placement behavior

The median fresh stochastic placement does not support the stronger claim that arbitrary recycled placement is always superior.

- At 16 bits, median recycled/wide CZ is 1.0187 on Fez and 1.0319 on the Nighthawk-style proxy.
- At 32 bits, median CZ is near parity: 0.9798 on Fez and 0.9988 on the proxy.
- At 64 bits, median CZ favors recycled: 0.9601 on Fez and 0.9880 on the proxy.
- Median depth remains slightly above wide at all three tested precisions.

Therefore the supported statement is specifically **placement-aware**: search can reproducibly find favorable exact-width recycled placements. This is distinct from claiming that random or default placement is automatically better.

## Interpretation

The result supports three conclusions inside the present small-N compiler model:

1. The recycled phase-register architecture keeps quantum width fixed while the wide phase register grows with requested precision.
2. The placement-sensitive routing overhead of the recycled circuit can be reduced enough that a fresh placement search reproduces lower CZ and lower depth than the wide construction.
3. The best-placement advantage grows with phase precision over the tested 16/32/64-bit points.

The square-lattice proxy lowers absolute routing cost, but the independent replication does not establish a unique Nighthawk-specific amplification of the recycling advantage. Both Fez and the square-lattice proxy reproduce the placement-aware advantage.

## Claim boundary

This remains:

- N=35 exact full-register permutation synthesis;
- order/orbit independent in circuit construction;
- a compiler/topology proxy with zero QPU jobs;
- not a measured Phoenix/Nighthawk r2 result;
- not a scalable modular-arithmetic implementation for RSA-size N;
- not evidence of an asymptotic Shor speedup.

The next high-value falsification/generalization step is to repeat the architecture on additional small composite moduli with different work-register widths. That tests whether the fixed-width and placement-aware advantages are specific to N=35's interaction structure or generalize across small-N instances.
