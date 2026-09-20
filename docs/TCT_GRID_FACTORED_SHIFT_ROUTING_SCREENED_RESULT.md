# TCT grid-factored shift routing — screened six-round result

Date: 2026-09-19

## Scope

This records the zero-QPU sparse-topology routing benchmark of the validated, classification-exact, six-round, 25-qubit grid-factored TCT arithmetic oracle.

The circuit coherently evaluates the structured transformed objective, marks the low-loss region, uncomputes the arithmetic, and applies Grover diffusion. The benchmark uses authenticated IBM Fez heavy-hex connectivity and the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy.

This result is **best among screened patches**, not an exhaustive optimum across the sampled candidate sets.

## Fully connected validated baseline

- logical width: 25 qubits
- parameter bits: 9
- accumulator bits: 16
- Grover rounds: 6
- marked states: 8
- CZ: 42,756
- depth: 132,481
- size: 263,193
- weighted interaction edges: 273

## Fez heavy-hex screened routing

Candidate patches: 12
Selected patches: 5
Patch compile reduction: 58.33%
Minimum interaction-distance predictor score: 153,816
Minimum patch diameter: 11

Best interaction-fixed screened result:
- patch 4
- predictor rank 1
- diameter 13
- CZ: 125,391
- depth: 248,496
- CZ overhead vs fully connected: 2.933x
- depth overhead vs fully connected: 1.876x

Best Qiskit-auto screened result:
- patch 4
- predictor rank 1
- diameter 13
- CZ: 121,320
- depth: 247,438
- CZ overhead vs fully connected: 2.837x
- depth overhead vs fully connected: 1.868x

The best Fez result is therefore the predictor-rank-1 patch in both routing modes within the screened set.

## 10x12 square-lattice proxy screened routing

Candidate patches: 12
Selected patches: 3
Patch compile reduction: 75.00%
Minimum interaction-distance predictor score: 106,740
Minimum patch diameter: 7

Best interaction-fixed screened result:
- patch 8
- predictor rank 1
- diameter 7
- CZ: 97,737
- depth: 228,205
- CZ overhead vs fully connected: 2.286x
- depth overhead vs fully connected: 1.723x

Best Qiskit-auto screened result:
- patch 8
- predictor rank 1
- diameter 7
- CZ: 97,026
- depth: 226,426
- CZ overhead vs fully connected: 2.269x
- depth overhead vs fully connected: 1.709x

The best proxy result is likewise the predictor-rank-1 patch in both routing modes within the screened set.

## Interpretation

The validated structured arithmetic oracle survives sparse connectivity with a moderate routing penalty rather than an order-of-magnitude blow-up. In the screened study:

- Fez Qiskit-auto requires about 2.84x the fully connected CZ count and 1.87x the depth.
- The square-lattice proxy Qiskit-auto requires about 2.27x the CZ count and 1.71x the depth.

Relative to the original six-round arithmetic-oracle projection (1,632,756 CZ / 6,502,224 depth), the screened structured Fez result is lower by about 92.57% in CZ and 96.19% in depth, while the proxy result is lower by about 94.06% in CZ and 96.52% in depth. These are implementation/compiler comparisons, not end-to-end quantum speedup claims.

The routing screen performed encouragingly here: the minimum interaction-distance predictor patch is the best screened patch for both routing modes on both topologies. However, unscreened candidate patches were not compiled, so global sampled-patch optimality and exact screen recall are not established by this run.

## Next rigorous check

Use the existing `--exhaustive` mode over the same 12 candidate patches and patch seed 314159. That will convert the current statement from "best among screened" to "best among all 12 sampled patches" and directly measure screen recall/regret for the 25-qubit coherent arithmetic workload.

## Boundaries

- Zero QPU jobs.
- Fez result uses topology/connectivity, not calibration-aware execution.
- Nighthawk/Phoenix side is a 10x12 square-lattice proxy, not an authenticated exact Phoenix map.
- No device error, fidelity, timing, reset, or fault-tolerant resource model is included.
- Reduced-order TCT objective only; this is not fusion-physics validation.
- Classification-exact transformed arithmetic, not pointwise-identical original floating-point loss values.
- No end-to-end quantum-speedup or practical advantage claim.
