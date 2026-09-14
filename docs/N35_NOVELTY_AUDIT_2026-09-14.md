# N=35 Shor/order-finding novelty audit — 2026-09-14

This note records the literature boundary for external claims around the `N=35`, `a=2`, `r=12` recycled-register hardware result. It is intentionally conservative and should be re-run immediately before any preprint or journal submission.

## Bottom line

The project should **not** claim “first quantum factorization of 35,” “first Shor experiment for 35,” “first qubit-recycling Shor implementation,” or “first dynamic Shor implementation on superconducting hardware.” Prior work exists in each broader category.

The narrow statement that currently survives the literature check is:

> **To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware, and the first reported dynamic-circuit `N=35` Shor/order-finding result on a superconducting qubit processor.**

This is a priority claim based on a literature search, not proof that no unpublished or obscure earlier result exists. Keep “to our knowledge.”

## Relevant prior work

### 2012 — qubit recycling already established

Martín-López *et al.* demonstrated a compiled iterative Shor experiment for `N=21` using a single recycled control qubit in a photonic system.

Reference: E. Martín-López *et al.*, *Nature Photonics* 6, 773–776 (2012), DOI `10.1038/nphoton.2012.259`.

Implication: do **not** claim invention of qubit recycling for Shor or iterative phase estimation.

### 2019 — superconducting N=35 attempt, but unsuccessful

Amico, Saleem, and Kumph studied compiled Shor circuits for `N=15`, `21`, and `35` on IBM's superconducting `ibmqx5`, using a semiclassical QFT. Their `N=35` circuit used `a=4` (`r=6`). The paper concludes that the `N=35` experiment failed to factor 35 reliably.

Reference: M. Amico, Z. H. Saleem, M. Kumph, *Physical Review A* 100, 012305 (2019), DOI `10.1103/PhysRevA.100.012305`.

Implication: our work is not the first superconducting **attempt** at Shor for 35.

### 2021 — successful compiled N=21 on IBM hardware

Skosana and Tame demonstrated complete factoring of `N=21` with a compiled QPE routine on IBM quantum processors.

Reference: U. Skosana and M. Tame, *Scientific Reports* 11, 16599 (2021), DOI `10.1038/s41598-021-95973-w`.

### 2024 — dynamic QFT on IBM superconducting hardware

Bäumer *et al.* demonstrated QFT+measurement using dynamic circuits and real-time feed-forward on IBM superconducting processors, showing the resource advantage of replacing unitary-QFT entangling structure with mid-circuit measurements.

Reference: E. Bäumer *et al.*, *Physical Review Letters* 133, 150602 (2024), DOI `10.1103/PhysRevLett.133.150602`.

Implication: do **not** claim the first dynamic/semiclassical QFT on superconducting hardware.

### 2025/2026 — successful N=35 signal exists for a friendlier base

Bagourd *et al.* experimentally investigated Shor implementations on current cloud hardware. For `N=35`, their `a=4`, `r=6` experiment produced only marginal evidence under their statistical test, while their `a=8`, `r=4` experiment produced a statistically significant signal.

Reference: P. Bagourd *et al.*, arXiv:2512.15330v3, DOI `10.48550/arXiv.2512.15330`.

Implication: do **not** claim first successful quantum-hardware evidence associated with Shor factorization of 35 in general. Our distinction is the harder `a=2`, `r=12` case and the dynamic recycled architecture.

### 2026 — classical acoustic N=35 Shor implementation

Kuk *et al.* implemented the period-finding core of Shor for `N=35`, `a=4`, `r=6` on a nonlinear topological acoustic phase-bit platform. This is a classical physical-wave system, not quantum hardware. Their paper states that they were not aware of a successful quantum-hardware Shor implementation for `N=35` at the time of their study.

Reference: I. Kuk *et al.*, *Communications Engineering* 5, 60 (2026), DOI `10.1038/s44172-026-00623-6`.

### August 2026 — dynamic-circuit Shor on superconducting hardware, N=15

Wu *et al.* reported a dynamic-circuit implementation of Shor's algorithm on a hybrid superconducting qubit-cavity processor, factoring `N=15` over all coprime bases. Their architecture uses a high-dimensional cavity qudit as the computational register and a repeatedly measured/reset transmon ancilla.

Reference: H. Wu *et al.*, arXiv:2608.04780, DOI `10.48550/arXiv.2608.04780`.

Implication: do **not** claim the first dynamic-circuit Shor experiment on a superconducting platform. A narrower `N=35`/gate-based qubit-processor claim remains plausible.

## What appears distinctive here

The present result combines all of the following:

- `N=35`, `a=2`, non-power-of-two `r=12`;
- gate-based superconducting quantum hardware (`ibm_fez`);
- one recycled phase ancilla using mid-circuit measurement, reset, and feed-forward;
- a coherent four-qubit work register carrying an exact compiled twelve-state modular orbit;
- direct continued-fraction order/factor recovery rather than only histogram-overlap assignment;
- explicit uniform-random-output baselines for both permissive and strict post-processing;
- same-job wide/recycled comparison with matched initial work-register placement;
- clean hardware replication before placement optimization;
- a subsequent calibration-aware layout search that improves the distribution while preserving the strict signal.

The combination, rather than qubit recycling alone, is the research contribution.

## Recommended claim hierarchy

**Safest:**

> We report replicated recovery of `r=12` order information for a compiled `N=35`, `a=2` Shor instance on IBM superconducting hardware using a dynamically recycled phase register.

**Priority wording acceptable with literature qualifier:**

> To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware.

**Additional architecture wording, also qualified:**

> To our knowledge, this is the first reported dynamic-circuit `N=35` Shor/order-finding result on a superconducting qubit processor.

**Avoid:**

> We are the first to factor 35 on a quantum computer.

That broader statement is not supportable given the prior literature and alternative quantum factoring approaches.

## What cross-backend validation changes

Cross-backend replication is not required for the narrow priority statement, but it would substantially improve the scientific credibility of the architecture claim. If the `a=2`, `r=12` strict signal survives on an independent dynamic-capable superconducting backend, the paper can argue that the result is not a one-device or one-calibration anomaly.

If cross-backend execution fails, report that failure. The Fez result remains a replicated device-specific result, but the generality claim must remain narrow.