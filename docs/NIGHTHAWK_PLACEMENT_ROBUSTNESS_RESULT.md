# Placement-robust Fez vs Nighthawk topology-proxy result

Date: 2026-10-07

## Scope

This records the zero-QPU placement-robustness benchmark from
`hardware/ibm_nighthawk_placement_robustness_benchmark.py`.

The experiment compares the same exact small-N N=35 recycled-QPE construction
on:

- authenticated IBM Fez heavy-hex connectivity; and
- a clearly labeled 10x12, 120-qubit square-lattice proxy for IBM Nighthawk.

For each topology / architecture / phase precision, multiple deterministic
connected placements were generated. Each placement was compiled under two
transpiler seeds and the best strict compile for that placement was retained.
Compiler borrowing was impossible because every placement backend was hard-capped
to the source logical width.

This remains a topology/compiler proxy only. It contains no Phoenix calibration,
timing, reset-speed, fidelity, or QPU execution data. The square-lattice proxy is
not asserted to be the exact Phoenix coupling map. The N=35 full-register
permutation synthesis is not a scalable RSA modular-arithmetic estimate.

## Placement-robust summary

R/W means recycled divided by wide. Values below 1 favor recycling.

| phase bits | width wide->recycled | Fez CZ R/W median | square CZ R/W median | Fez depth R/W median | square depth R/W median | CZ amp square/Fez |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 23->8 | 1.2230 | 1.0220 | 1.1408 | 1.0088 | 0.8356 |
| 24 | 31->8 | 1.0383 | 1.0063 | 1.0466 | 1.0034 | 0.9692 |
| 32 | 39->8 | 1.0216 | 0.9234 | 1.0303 | 0.9820 | 0.9038 |
| 48 | 55->8 | 1.0910 | 0.9222 | 1.0836 | 0.9820 | 0.8453 |
| 64 | 71->8 | 1.0031 | 0.9826 | 1.0301 | 1.0034 | 0.9795 |

## Main interpretation

The strongest placement-robust result is not that recycling always beats wide.
It does not on Fez under these sampled placements.

Instead, the stronger topology claim is:

> Across every tested precision from 16 through 64 phase bits, the square-lattice
> topology improves the recycled-versus-wide CZ ratio relative to Fez.

The amplification ratio is below 1 at every tested precision. In other words,
the denser square lattice consistently shifts the relative resource tradeoff in
favor of recycling.

At 32 and 48 phase bits, this is strong enough to reverse the sign of the result:

- 32 bits:
  - Fez recycled has 2.16% more CZ than wide.
  - Square-lattice recycled has 7.66% fewer CZ than wide.
- 48 bits:
  - Fez recycled has 9.10% more CZ than wide.
  - Square-lattice recycled has 7.78% fewer CZ than wide.

At 64 bits:

- Fez is effectively at CZ parity: recycled is only 0.31% higher than wide.
- Square-lattice recycled is 1.74% lower than wide.

The depth effect is weaker but directionally similar. At 32 and 48 bits the
square lattice again flips the recycled result from a depth penalty on Fez to a
small depth advantage.

## Width result remains unchanged

The topology study does not change the width conclusion:

- 16 bits: 23 -> 8 qubits
- 24 bits: 31 -> 8 qubits
- 32 bits: 39 -> 8 qubits
- 48 bits: 55 -> 8 qubits
- 64 bits: 71 -> 8 qubits

At 64 bits, recycling still removes 63 of 71 qubits, an 88.73% width reduction.

## Important methodological caveat

The placement generator can map multiple different placement seeds to the same
connected subgraph. Therefore the eight nominal placement samples are not always
eight unique graph placements. Repeated subgraphs can overweight one local
topology shape in the distribution.

This does not invalidate the measured compiles, but it means the current
placement distribution is not an independent sample of eight unique subgraphs.

## Next validation

Repeat the same strict-width test with an explicit uniqueness constraint:

1. Canonicalize each selected connected subgraph by source-node set.
2. Reject duplicate placements.
3. Continue sampling until the requested number of unique placements is reached
   or a documented attempt limit is exhausted.
4. Report the number of unique placements actually obtained.
5. Preserve the same two transpiler seeds and median/IQR summary.
6. Focus on 32, 48, and 64 phase bits, where the topology effect is most relevant.

If the square-lattice recycled-over-wide CZ advantage survives unique-placement
sampling at 32 and 48 bits, the topology effect will be substantially more robust.

No QPU job was submitted.
