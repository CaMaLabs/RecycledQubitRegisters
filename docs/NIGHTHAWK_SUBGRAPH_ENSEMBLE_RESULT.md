# Nighthawk subgraph-ensemble result

## Scope

This result is a **zero-QPU compiler/topology proxy** for the existing exact small-`N=35` full-register benchmark in this repository. It is **not** a calibrated IBM Phoenix performance result and it is **not** scalable RSA modular arithmetic.

The Nighthawk side used the labeled 10x12, 120-qubit square-lattice proxy because the current IBM account could not access `ibm_phoenix` metadata. Every compile was capacity-locked to exactly the source-circuit width, so no extra physical-qubit borrowing was possible.

The ensemble audited 8 distinct connected exact-width patches per topology at phase precisions 8, 16, 32, and 64 bits, using one transpiler seed per patch.

## Main result

The single-patch result had suggested that a Nighthawk-style square lattice might strongly amplify the **relative** advantage of the recycled architecture versus wide QPE. The ensemble does **not** support that stronger claim.

Median recycled/wide CZ ratios were:

| Phase bits | Fez heavy-hex | Nighthawk square proxy | Relative Nighthawk / Fez |
|---:|---:|---:|---:|
| 8  | 1.0745 | 1.0535 | 0.9805 |
| 16 | 1.0383 | 1.0299 | 0.9919 |
| 32 | 1.0059 | 1.0118 | 1.0058 |
| 64 | 0.9816 | 0.9962 | 1.0149 |

Median recycled/wide depth ratios were:

| Phase bits | Fez heavy-hex | Nighthawk square proxy | Relative Nighthawk / Fez |
|---:|---:|---:|---:|
| 8  | 1.0606 | 1.0260 | 0.9674 |
| 16 | 1.0446 | 1.0222 | 0.9785 |
| 32 | 1.0265 | 1.0218 | 0.9954 |
| 64 | 1.0154 | 1.0234 | 1.0079 |

The earlier approximately `0.84` relative-CZ effect was therefore placement-sensitive and should **not** be treated as a robust topology-specific amplification of recycling.

## What did survive

Three conclusions remain robust within this proxy:

1. **The square lattice lowers absolute routing cost substantially for both architectures.**
2. **The recycled architecture preserves its width advantage independent of topology.** At 64 phase bits the comparison remains 8 qubits versus 71 qubits.
3. **Recycled and wide approach native-CZ parity as phase precision increases.** At 64 bits the ensemble medians were slightly favorable to recycled on Fez (`0.9816`) and nearly equal on the square-lattice proxy (`0.9962`).

The recycled construction remains slightly deeper in the ensemble median at 64 bits (`1.0154` on Fez and `1.0234` on the Nighthawk proxy), so there is no basis for claiming an across-the-board depth advantage.

## Placement sensitivity

The ensemble exposes an important implementation property: the 8-qubit recycled circuit is much more placement-sensitive than the wide circuit.

At 64 bits, recycled CZ ranges were:

- Fez: `109,853` to `143,935`
- Nighthawk proxy: `81,320` to `104,173`

while wide CZ ranges were much tighter:

- Fez: `122,831` to `124,776`
- Nighthawk proxy: `92,999` to `94,109`

This means qubit placement / subgraph selection is now a more promising optimization lever than additional MCX-profile tuning.

## Safe interpretation

A defensible statement is:

> In a zero-QPU exact-width topology/compiler proxy, qubit-recycled QPE retained an 8-qubit physical-width requirement through 64 phase bits while conventional wide QPE grew to 71 qubits. A Nighthawk-style square lattice reduced routing cost for both architectures, but an apparent topology-specific amplification of the recycled-vs-wide advantage did not survive an 8-patch subgraph ensemble. The recycled circuit showed substantially larger placement sensitivity, identifying placement optimization as the next practical lever.

Do not describe this as measured Phoenix hardware performance, a hardware speedup, or a scalable RSA result.
