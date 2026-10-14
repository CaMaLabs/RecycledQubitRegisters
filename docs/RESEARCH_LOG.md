# Research Log

This file is the narrative record for the RecycledQubitRegisters project. It is
intended to preserve not just results, but **why each experiment was run, what
assumptions were intentional, and what later tests do or do not invalidate**.

## 2026-10-14 — Preserve optimized-mapping intent

### Context

The project intentionally treats physical-qubit placement as part of the
compiler/architecture strategy. The strict Fez-vs-Nighthawk topology study
searched for compact, favorable connected subgraphs under a hard source-width
cap. That optimized placement was deliberate.

A later unique-placement benchmark was added to sample many distinct connected
placements and measure sensitivity to placement quality.

### Interpretation guardrail

**Do not describe the optimized-placement result as a placement artifact.**

The two experiments answer different questions:

- **Optimized mapping:** What resource cost can the recycled architecture
  achieve when the compiler deliberately searches for a good physical-qubit
  placement? This is the intended engineering strategy.
- **Placement sensitivity:** How much do CZ count and depth change when the same
  architecture is mapped onto other valid connected subgraphs? This measures
  robustness to mapping quality.

If random/unique placements perform worse than the optimized placement, that
does not invalidate the optimized result. It quantifies the value of topology-
aware placement optimization.

The correct reporting format is therefore to keep both:
1. optimized-placement resource results; and
2. unique-placement distribution results.

A useful derived metric is the **mapping-optimization gain**:
optimized result versus median unique-placement result, separately for Fez and
the Nighthawk-style square-lattice proxy.

### Related results already preserved

- `docs/NIGHTHAWK_STRICT_TOPOLOGY_PROXY_RESULT.md` — optimized strict-width
  topology result.
- `docs/NIGHTHAWK_PLACEMENT_ROBUSTNESS_RESULT.md` — placement-distribution
  result and sensitivity interpretation.
- `hardware/ibm_nighthawk_unique_placement_benchmark.py` — current stricter
  unique-placement follow-up.

### Runtime-cost safety

IBM paid runtime is not authorized by default. A credit card being present on
the IBM account is **not** permission to use paid runtime.

Before any real QPU submission:
- positively verify that the resolved IBM instance/plan is free/open;
- if plan or billing status is ambiguous, do not submit;
- prefer zero-QPU compiler/topology work and local/fake backends whenever they
  answer the research question.

The current unique-placement topology benchmark is zero-QPU and can fall back
to local FakeFez plus the public square-lattice proxy.

### Current story

The durable result is the width reduction from recycled phase estimation:
the recycled architecture remains fixed-width while the conventional phase
register grows with precision. Topology-aware placement can materially affect
whether that width advantage also produces CZ/depth savings.

The research question is therefore no longer simply "does recycling beat wide?"
It is:

> Under a realistic topology-aware compiler policy, how much width does
> recycling save, what CZ/depth cost or benefit remains, and how dependent is
> that result on placement quality and hardware connectivity?

Future summaries should preserve that distinction.
