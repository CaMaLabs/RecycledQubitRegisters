# PTP/QRR novelty audit

Date: 2026-09-14

This document is intentionally conservative. It separates established prior art, claims made in the PTP papers, QRR experimental contributions, and speculative hypotheses. It is not a claim of novelty by itself.

## Established prior art

### Shor/order finding

Peter Shor's 1994 algorithm establishes polynomial-time quantum factoring through period/order finding and classical gcd recovery. DOI: `10.1109/SFCS.1994.365700`.

### Semiclassical inverse QFT

Griffiths and Niu (1996) showed that the inverse Fourier transform immediately before final measurement can be implemented semiclassically using measured classical outcomes to control later one-qubit operations. DOI: `10.1103/PhysRevLett.76.3228`.

### Iterative/small-width Shor architectures

Parker and Plenio (2000), Beauregard (2003), and related work established low-width/iterative Shor constructions before QRR. QRR must not claim invention of iterative order finding or low-width Shor generally.

### Qubit recycling in experimental Shor

Martín-López et al. (2012) experimentally replaced the multi-qubit control register by one recycled control qubit in a compiled photonic `N=21` Shor experiment. DOI: `10.1038/nphoton.2012.259`.

### Dynamic/reuse compiler work

Rovara, Burgholzer & Wille (2025), `arXiv:2511.22712`, use measurement movement and dynamic-circuit primitives to create additional qubit-reuse opportunities in QPE/QFT and other circuits. This is relevant prior art for any general compiler-level reuse claim.

### 2026 dynamic-circuit Shor

Wu et al. (2026), `arXiv:2608.04780`, report dynamic-circuit Shor on a hybrid superconducting qubit-cavity processor, repeatedly measuring/resetting/reusing a superconducting ancilla and factoring `N=15` over all coprime bases. This materially overlaps the dynamic/recycled-Shor concept and narrows any QRR first-claim accordingly.

### Wheel/modulo-210 residue filtering

The fact that integers coprime to `2*3*5*7=210` occupy `phi(210)=48` residue classes is standard wheel-sieve/elementary modular arithmetic. Any PTP/QRR result must distinguish a genuinely new computational effect from this ordinary wheel baseline.

## Claims made in the PTP papers

These are paper claims to reproduce/test, not assumptions embedded as QRR facts.

### PTP 2024

Li, Fang & Kuo, DOI `10.4236/apm.2024.145023`, describe a modulo-210 Periodic Table of Primes with 48 roots for integers not divisible by `2,3,5,7`.

### Periodic listing 2025

Li, Fang, Kuo & Lin, DOI `10.4236/apm.2025.154012`, develop factor-pair/mapping constructions for periodic prime/composite listing.

### Kernel factor pairs 2025

Li, Fang, Kuo & Lin, DOI `10.4236/apm.2025.159032`, define factor-pair rows and kernel factor pairs and present an LFK linear-search framework. The paper states that a target row contains either 24 or 28 unordered factor-root pairs and bounds the search by up to 56 linear scans over approximately `sqrt(N)/210` coordinates.

QRR independently generates the rows and tests the 24/28 property rather than copying their table.

### Composite symmetry 2026

Li, Fang, Kuo & Lin, DOI `10.4236/apm.2026.161006`, describe vertical, horizontal, diagonal, cyclic, and mirror relationships among composite entries.

QRR reproduces the residue transforms but requires an additional fixed-`N` no-false-rejection test before using any symmetry as a factor-search reduction.

## QRR experimental contributions already established independently of PTP

The existing repository includes:

- dynamic phase-register recycling with one repeatedly measured/reset ancilla;
- matched wide-versus-recycled QPE/Shor hardware controls;
- real IBM backend execution and calibration-aware layout experiments;
- explicit random-output/noise-floor baselines;
- a compiled `N=35, a=2, r=12` order-finding experiment;
- cross-backend Fez/Marrakesh data including negative/null placement behavior;
- generic/full-register synthesis experiments that explicitly document large arithmetic/compiler costs rather than hiding them.

These results remain separate from the optional PTP track.

## Potential PTP/QRR contributions that would be new only if demonstrated

The following may become contributions if tests support them and literature review does not reveal prior art:

1. a PTP-aware Shor factor-recovery/postprocessing path with zero false rejection and measured improvement under noisy QPE;
2. a demonstrated pre-order circuit/resource reduction derived solely from public `N`, `a`, and modulo-210 structure, without hidden-factor leakage;
3. a matched wide/recycled experiment showing that such a reduction survives backend transpilation and physical placement;
4. a quantitative result showing kernel-factor constraints reduce total end-to-end work beyond a conventional wheel-210 baseline;
5. a null result establishing that PTP residue structure does **not** materially predict `ord_N(a)` or reduce useful quantum resources.

A well-controlled null result is scientifically valid and should be retained.

## Early falsification result: symmetry does not automatically halve fixed-N search

The diagonal residue transform maps `(q,h)` to `(-q,-h) mod 210` and preserves the product residue. That is an exact modular symmetry.

But it does not preserve the integer product for a fixed semiprime. Example:

```text
N = 2587 = 13 * 199
(13,199) and (11,197) have the same product residue mod 210
13*199 = 2587
11*197 = 2167
```

Therefore, if a factor-pair row retained only one diagonal representative, it could discard the actual factor-root pair. This falsifies the naive version of H4 that mirror symmetry alone safely halves the kernel-factor search for a fixed `N`.

Symmetry may still reduce table construction/storage or support other exact equivalences, but each proposed use requires its own proof/test.

## Open hypotheses and required controls

### H1 — PTP-aware preprocessing reduces useful quantum resources

Required control: same `N`, same admissible base-selection rule, same modular function, same precision target, wide and recycled implementations. Hidden factors must never be used to choose the circuit.

### H2 — PTP-aware postprocessing improves noisy factor recovery

Required control: identical measured bitstrings passed through standard and PTP-aware postprocessors. Report accepted/rejected order candidates, false rejection, factor success, modular exponentiations, gcds, and runtime.

### H3 — kernel-factor structure adds useful information about order candidates

Required control: compare against ordinary Shor verification (`a^r mod N`, even-order and gcd conditions) and against any filter available from `N` alone. Measure information gain or candidate reduction without using `p,q`.

### H4 — composite symmetry materially reduces factor search

Naive diagonal canonicalization is already falsified for fixed-N factoring. Any stronger symmetry proposal needs exhaustive small-N validation and an algebraic proof of equivalence.

### H5 — benefit survives a wheel-210 baseline

This is mandatory. A result that only beats naive trial division but not an optimized wheel-210 search is not evidence of new leverage from PTP representation.

## Claim boundaries

Do not claim:

- a new factoring complexity class from constant-factor residue pruning;
- that modulo-210 structure changes Shor's asymptotic quantum speedup without proof;
- that factor-root information unavailable before factorization can be used in circuit construction;
- that dynamic/recycled Shor itself is novel;
- that a PTP residue filter replaces the coherent modular work register;
- that symmetry classes are interchangeable for fixed-N factoring merely because their products agree modulo 210.

If the optional track produces a positive result, the strongest defensible wording should identify exactly which measurable resource or postprocessing metric changed and against which standard/wheel baseline.
