# Mapping-optimization gain result

Date: 2026-10-14

## Purpose

This analysis closes the interpretation gap between the optimized-placement
experiments and the unique-placement sensitivity audit.

Optimized placement is an intentional part of the QRR compiler strategy. The
unique-placement experiment does not replace it; it measures how strongly
performance depends on mapping quality.

The analyzer compares:

- **optimized result:** best successful placement from the independent fresh
  stochastic replication set (`patch_index > 0`);
- **sensitivity result:** median over genuinely unique connected placements,
  keeping the better transpiler seed for each placement.

No QPU job is used.

## Mapping-optimization gain

### 32 phase bits

| topology | architecture | CZ best / unique median | CZ mapping gain | depth best / unique median | depth gain |
|---|---|---:|---:|---:|---:|
| Fez heavy-hex | recycled | 54,973 / 61,002.0 | **9.88%** | 118,122 / 123,135.0 | **4.07%** |
| Fez heavy-hex | wide | 59,928 / 60,820.5 | 1.47% | 120,726 / 120,960.0 | 0.19% |
| square-lattice proxy | recycled | 42,851 / 50,489.5 | **15.13%** | 102,263 / 110,861.5 | **7.76%** |
| square-lattice proxy | wide | 45,926 / 46,335.0 | 0.88% | 103,931 / 104,388.0 | 0.44% |

### 64 phase bits

| topology | architecture | CZ best / unique median | CZ mapping gain | depth best / unique median | depth gain |
|---|---|---:|---:|---:|---:|
| Fez heavy-hex | recycled | 109,443 / 118,735.0 | **7.83%** | 234,565 / 241,274.0 | **2.78%** |
| Fez heavy-hex | wide | 122,414 / 123,447.5 | 0.84% | 240,217 / 240,425.5 | 0.09% |
| square-lattice proxy | recycled | 85,416 / 104,482.5 | **18.25%** | 203,890 / 221,160.5 | **7.81%** |
| square-lattice proxy | wide | 93,135 / 93,559.0 | 0.45% | 207,107 / 207,525.0 | 0.20% |

The optimization benefit is therefore strongly architecture-dependent. Across
these cells, deliberate mapping changes recycled CZ by about 7.8-18.3% relative
to the unique-placement median, while the wide architecture moves by only about
0.45-1.47%.

This is evidence that the narrow recycled circuit has a concentrated routing
problem that rewards topology-aware placement much more strongly than the wide
circuit.

## Architecture comparison: optimized versus unique median

| bits | topology | width | optimized R/W CZ | unique-median R/W CZ | optimized R/W depth | unique-median R/W depth |
|---:|---|---:|---:|---:|---:|---:|
| 32 | Fez | 39 -> 8 | **0.9173** | 1.0030 | **0.9784** | 1.0180 |
| 32 | square proxy | 39 -> 8 | **0.9330** | 1.0897 | **0.9840** | 1.0620 |
| 64 | Fez | 71 -> 8 | **0.8940** | **0.9618** | **0.9765** | 1.0035 |
| 64 | square proxy | 71 -> 8 | **0.9171** | 1.1168 | **0.9845** | 1.0657 |

Expressed as optimized savings:

- 32-bit Fez: recycled uses **8.27% fewer CZ** and **2.16% less depth** than wide.
- 32-bit square proxy: **6.70% fewer CZ** and **1.60% less depth**.
- 64-bit Fez: **10.60% fewer CZ** and **2.35% less depth**.
- 64-bit square proxy: **8.29% fewer CZ** and **1.55% less depth**.

The unique-placement medians answer a different question. At 32 bits the
typical sampled recycled placement is at parity/slightly worse on Fez and worse
on the square lattice. At 64 bits Fez's unique-placement median still gives a
3.82% CZ advantage, while the square-lattice median is 11.68% worse.

## Interpretation

The correct result is not "random placement invalidates optimized placement."

It is:

> **QRR's gate/depth competitiveness is placement-sensitive, and topology-aware
> mapping is materially more valuable for the recycled architecture than for
> the wide architecture.**

That is an engineering/compiler result in its own right. The best-placement
advantage has also been reproduced on fresh stochastic placements, so it is not
just the deterministic dense patch recurring across discovery and replication.

The square-lattice proxy shows the strongest mapping-optimization gain for the
recycled circuit, but this must not be called a Nighthawk/Phoenix hardware
result. The current square lattice is a labeled 10x12 topology proxy.

## Why 48 bits is absent

The unique-placement audit includes 32, 48 and 64 bits. The independent fresh
optimized-placement replication used by this analyzer overlaps it at 32 and 64
bits. The analyzer intentionally reports only the intersection rather than
mixing discovery and replication populations to manufacture a 48-bit row.

## Claim boundary

Supported:

- fixed-width QRR remains a large width reduction;
- recycled compilation is substantially more sensitive to physical placement;
- deliberate placement search recovers replicated CZ/depth advantages over
  wide at 32 and 64 bits on both tested topology models;
- mapping optimization contributes far more to recycled than to wide.

Not established:

- a universal advantage on arbitrary placements;
- a calibrated hardware-fidelity/runtime advantage;
- an exact Phoenix/Nighthawk result;
- scalable RSA arithmetic from the N=35 topology circuits.
