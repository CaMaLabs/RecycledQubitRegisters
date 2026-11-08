# K027: All-methods fusion experiment

**Hypothesis under test:** combining every previously explored method may reveal a superior circuit architecture, including methods that lost in isolation. Do not prune a method from the experimental search solely because its previous standalone result was negative.

**Important distinction:** this is a research hypothesis, not a correctness claim. Every output must satisfy the original benchmark semantics and pass the official verifier. No substitution is assumed mathematically equivalent merely because it is included in the search.

## Target and scope

- Target benchmark: K001 inverse square root (kickmix), not generic Shor factoring.
- Current K026 frontier as of 2026-11-07: cost proxy 1,851,045 with prefix verifier passes through 65,536; not full-domain certified.
- Preserve K025/K026 artifacts and avoid touching their active processes, databases, or submission paths.
- K027 must store its own candidates and verification evidence.
- This branch houses the integration specification; the running K026 installation on `~/quantum-a26-check` is not automatically updated by GitHub changes.

## Include all methods as experimental contributors

1. **Arithmetic architecture substitution:** reciprocal-square-root alternative formulations (including Newton/Halley/polynomial or table-assisted seeds), precision reallocation, Horner/FMA rewriting.
2. **Register recycling:** reuse proven-dead scratch/ancilla slots, optional measurement/reset only where the semantics and benchmark permit it.
3. **Scratch uncompute and reversible synthesis:** clean compute/use/uncompute regions; test shared carry reuse and clean ancilla scheduling.
4. **Adder and multiplier substitutions:** carry-save, ripple, prefix, partial-product trees, alternative Toffoli and CCX decomposition.
5. **Dark Star pruning:** constraint propagation, bounded recursive enumeration, structure-level recombination, deduplication by *compiled circuit hash*.
6. **Fourier/FFT/NTT and polynomial transforms:** include alternative convolution or constant-multiply blocks where exact fixed-point semantics can be established; otherwise retain as candidates and record explicit correctness failure.
7. **LWE-derived constraint/noise reasoning:** stratified adversarial input families, numeric-error shaping, sensitivity-based precision allocation; not interchangeable with cryptographic LWE hardness assumptions.
8. **Ancilla/XOR logic and relative-phase constructions:** allow only when phase/measurement outputs are preserved at verifier boundary.
9. **Physical placement-aware rewriting:** track hardware depth/two-qubit gates separately, since coupling-map gains need not improve kickmix score.
10. **Crossover combinations:** combine all above in one search graph, including combinations of methods previously rejected individually.

## K027 search contract

Candidate = (algorithm family, typed arithmetic IR, precision policy, transform chain, reversible synthesis, scheduling, compiler settings, seed).

Pipeline:
1. Build baseline and a trusted functional oracle.
2. Instantiate each module and the full combined chain. All methods get an opportunity, but a failed transform is not silently treated as an equivalent circuit.
3. Apply static bounds (bit widths, overflow, qubits, ancilla lifetime, reversible cleanup, phase invariants).
4. Compile to the benchmark-native format and compute canonical circuit SHA-256.
5. Deduplicate by compiled SHA; record aliases and parameter provenance.
6. Run targeted arithmetic counterexamples and seeded error tests.
7. Run the *official* verifier on progressive fresh prefixes and seeds, logging scores, worst errors, and failed witnesses.
8. Promote only verified candidates to the frontier; do not confuse heuristic screening or partial-prefix passes with full-domain proof.
9. Use counterexamples to inform the pruning strategy; preserve negative results and reproducible seeds.
10. Compare against both original reference and the best K025/K026 frontier with identical verifier configurations.

## Acceptance criteria

- Full combinatorial system is instantiated and produces a benchmark-native circuit.
- Official verifier passes required configuration(s).
- Candidate cost improves on the current best *under the same evaluation regime*.
- Logs include full spec, module provenance, circuit hash, verifier version, input levels, seeds, error metrics, and failure witnesses.
- No score is described as leaderboard-comparable until it is a genuine Kaggle-scored submission.

## Execution policy

Keep K026 alive. Implement K027 in an isolated `competition/k027/` workspace on the machine with access to the proprietary/local K001 assets. Run local smoke tests first, then launch separately with an explicit resource limit. This branch does not claim implementation or test completion.
