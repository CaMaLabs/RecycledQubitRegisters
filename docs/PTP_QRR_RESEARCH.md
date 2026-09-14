# Optional PTP/QRR research track

Status: **experimental, simulation/classical-preflight only; no QPU use authorized by this track yet.**

This track is deliberately isolated from the established QRR experiments. It must not rewrite, reinterpret, or delete existing hardware results, raw JSON, negative/null results, matched controls, or reproducibility records.

## Research question

Can modulo-210 residue structure of unknown semiprime factors reduce classical search/postprocessing, quantum circuit resources, compiled modular arithmetic, or total end-to-end factoring cost when combined with QRR's recycled/iterative phase-estimation architecture?

The default answer is **unknown**. The implementation is designed so every proposed benefit can fail cleanly.

## References incorporated

1. Li, Fang & Kuo (2024), *The Periodic Table of Primes*, DOI `10.4236/apm.2024.145023`.
2. Li, Fang, Kuo & Lin (2025), *Listing Prime Numbers Periodically*, DOI `10.4236/apm.2025.154012`.
3. Li, Fang, Kuo & Lin (2025), *Kernel Factor Pairs for Semiprime Factorization*, DOI `10.4236/apm.2025.159032`.
4. Li, Fang, Kuo & Lin (2026), *Symmetry of the Composite Numbers*, DOI `10.4236/apm.2026.161006`.
5. Shor (1994), *Algorithms for Quantum Computation: Discrete Logarithms and Factoring*, DOI `10.1109/SFCS.1994.365700`.
6. Griffiths & Niu (1996), *Semiclassical Fourier Transform for Quantum Computation*, DOI `10.1103/PhysRevLett.76.3228`.
7. Parker & Plenio (2000), *Efficient Factorization with a Single Pure Qubit and log N Mixed Qubits*, `quant-ph/0001066`.
8. Beauregard (2003), *Circuit for Shor's Algorithm Using 2n+3 Qubits*, `quant-ph/0205095`.
9. Martín-López et al. (2012), *Experimental Realization of Shor's Quantum Factoring Algorithm Using Qubit Recycling*, DOI `10.1038/nphoton.2012.259`.
10. Rovara, Burgholzer & Wille (2025), *Qubit Reuse Beyond Reorder and Reset*, `arXiv:2511.22712`.
11. Wu et al. (2026), *Demonstrating advantages of dynamic quantum circuits on a hybrid superconducting qubit-cavity processor*, `arXiv:2608.04780`.

### Material 2026 overlap

Wu et al. is directly relevant: it reports dynamic-circuit Shor on a hybrid superconducting qubit-cavity processor, with a repeatedly measured/reset/reused transmon ancilla, and factors `N=15` over all coprime bases. That strengthens the prior-art boundary around dynamic/recycled Shor itself. QRR novelty claims therefore must focus on the specific matched architecture/resource experiments, harder compiled instances, placement controls, full-register/generic arithmetic work, and any independently demonstrated PTP hybrid effect—not on inventing dynamic Shor.

Rovara et al. is broader compiler prior art for qubit reuse through measurement movement and classically controlled gates; it is not specific to the modulo-210 hypothesis but is relevant to any future claim about reuse optimization.

## Implemented Phase 1: modulo-210 core

Location: `simulation/ptp_hybrid/core.py`.

The code derives, rather than copies, the PTP root set using

```text
M = 2*3*5*7 = 210
gcd(r,210) = 1
11 <= r <= 220
```

This yields 48 canonical roots, with residue `1 mod 210` represented by root `211`, matching the PTP/kernel-factor period convention.

Implemented APIs:

```python
root_for_integer(N)
root_index(N)
ptp_coordinate(N)  # -> (r,k), N=r+210*k
is_ptp_candidate(N)
```

`exhaustive_core_report()` checks every prime `>7` through a requested bound and verifies that it belongs to one of the generated classes.

## Implemented Phase 2: factor-pair table

`factor_pair_table()` generates all unordered root pairs `(q_j,q_k)` satisfying

```text
q_j*q_k == r_i (mod 210)
```

for each target root. No publication table is embedded in the code.

The independently generated structure has the publication's reported `24/28` row sizes:

- 42 target roots have 24 unordered candidate root pairs;
- 6 target roots have 28 unordered candidate root pairs;
- each 28-pair row has 8 self-pairs.

The test suite also verifies that an actual semiprime factor-root pair is present in the generated row.

The important baseline is all `48*49/2 = 1176` unordered root pairs. Restricting by `N mod 210` therefore prunes to 24 or 28 root-pair classes. This is a **constant-factor residue pruning statement only**; it is not a polynomial/exponential complexity improvement.

## Implemented Phase 3: kernel-factor coordinates and LFK reference

Location: `simulation/ptp_hybrid/kernel.py`.

For candidate roots `(q_j,q_k)`, factors are represented as

```text
p = q_j + 210*theta
q = q_k + 210*theta_hat
```

and the code independently evaluates

```text
sigma = (N - q_j*q_k)/210
sigma = q_j*theta_hat + q_k*theta + 210*theta*theta_hat
```

The LFK-style reference search implements both orderings of `theta` and `theta_hat`, records pair checks/search steps/divisibility tests/wall time, and explicitly handles factors `2,3,5,7` as edge prechecks.

Two required baselines are implemented beside it:

- plain trial division;
- conventional wheel-210 trial division.

The wheel baseline is mandatory for H5 because modulo-210 PTP filtering overlaps classical wheel-factorization structure.

## Implemented Phase 4: symmetry reproduction and falsification gate

Location: `simulation/ptp_hybrid/symmetry.py`.

The code reproduces residue mirrors via

```text
q -> -q (mod 210)
h -> -h (mod 210)
```

and the corresponding vertical, horizontal, and diagonal pair transforms. The diagonal transform preserves the target product residue and does reduce the *residue table* into mirror classes.

However, residue-table equivalence is not automatically a valid reduction for factoring one fixed integer `N`. The implementation therefore refuses to use symmetry pruning unless exhaustive fixed-`N` tests show zero false rejection.

There is already a direct counterexample to naive diagonal canonicalization:

```text
N = 2587 = 13*199
actual root pair = (13,199)
diagonal mirror  = (11,197)
13*199 == 11*197 (mod 210)
but 13*199 != 11*197 as integers
```

Keeping only the lexicographically smaller diagonal representative would discard the actual factor pair. Thus mirror symmetry is useful for table generation/description but **cannot be assumed to halve fixed-N factor search**. This is an early negative result relevant to H4.

## Benchmark matrix

`simulation/ptp_hybrid/benchmark.py` starts with

```text
15 21 33 35 39 51 55 65 77 85 91 143 187 221 323 437 899
```

and adds deterministic balanced/unbalanced semiprimes using seed `8776`. It writes raw JSON/CSV under `results/ptp_hybrid/`, compares trial division, wheel-210, LFK-style search, and SymPy when available, and records actual residue-pair containment plus symmetry-audit status.

Run:

```bash
python -m unittest simulation.ptp_hybrid.test_ptp_hybrid -v
python simulation/ptp_hybrid/benchmark.py --seed 8776 --generated 24
```

No QPU backend is contacted.

## Phases not yet allowed to make positive claims

The following remain experimental work items and should not be inferred from the modulo-210 core alone:

1. **Shor postprocessing.** Compare standard continued-fraction/order recovery against a PTP-aware path. Any PTP validation must have zero false rejection on valid Shor factorization.
2. **Pre-order information.** Test whether `N mod 210` or candidate factor-root pairs provide information about useful bases or `ord_N(a)` beyond ordinary information already available from `N` and `a`.
3. **Quantum arithmetic.** Test whether residue information changes full modular multiplication, ancilla count, work-state count, or compiled CZ/depth without factor leakage.
4. **Wide vs recycled integration.** Any valid circuit optimization must be applied to both architectures with equivalent work registers in matched comparisons.
5. **N=21/N=35 bridge.** Existing QRR hardware results stay frozen as baselines. New PTP files must be separate.
6. **Hardware.** No QPU time until simulation identifies a concrete measurable change in width, two-qubit count, depth, filtering, recovery probability, placement, or required executions.

## Resource-accounting target

Future four-way comparisons must report, when applicable:

| Metric | Standard wide | Standard recycled | PTP-aware wide | PTP-aware recycled |
|---|---:|---:|---:|---:|
| simultaneous logical qubits | | | | |
| phase/control qubits | | | | |
| work qubits | | | | |
| ancillas | | | | |
| resets / MCM | | | | |
| classically controlled ops | | | | |
| 1Q / 2Q(CZ) gates | | | | |
| depth / transpiled depth | | | | |
| modular multiplications | | | | |
| classical candidate count | | | | |
| strict direct-order recovery | | | | |
| permissive factor recovery | | | | |
| Hellinger fidelity / TV | | | | |
| postprocessing time | | | | |

## Falsification hypotheses

- **H1:** PTP-aware preprocessing reduces useful quantum resources.
- **H2:** PTP-aware postprocessing increases factor recovery from noisy/recycled QPE output.
- **H3:** kernel-factor constraints add useful order-candidate information beyond ordinary Shor postprocessing.
- **H4:** composite symmetries materially reduce remaining factor search.
- **H5:** any benefit survives comparison with an optimized conventional wheel-210 baseline.

H4 already has a falsified *naive* form: diagonal mirror classes cannot simply be canonicalized for a fixed semiprime. H1-H3 and the stronger versions of H4/H5 remain open until benchmark results are generated.

## Claim discipline

Do not say PTP changes Shor complexity merely because it removes residue classes. Do not choose `a` using actual hidden factors. Do not use post-factor information to construct a supposedly pre-factor circuit. Do not imply classical storage replaces coherent work-register state. Preserve null results with the same visibility as positive results.
