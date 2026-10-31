# Independent repository search: a useful post-processing improvement

Research lead: Chase Lunsford / CaMaLabs. User-local date: October 30, 2026.

**Quaspy is the strongest actionable find from this search.** Its author-provided
order-recovery algorithms substantially improve our basic continued-fraction
factor verifier on held-out synthetic measurements. The public-input adapter
is implemented and can replay readouts without factors or order information.
This is established mathematics newly applied to this pipeline, not an original
CaMaLabs theorem or an RSA-2048 break. Spend and QPU jobs: zero.

## Repositories screened

Six external repositories were cloned and pinned. Their inspected source hashes
and commits are in `results/indie_diamond_20261030/repository_screen.json`.

| Repository | What it contributes | Evidence and disposition |
|---|---|---|
| [ekera/quaspy](https://github.com/ekera/quaspy) | Author implementation of improved order recovery and factoring post-processing | Selected; public-input adapter, null controls, and fresh held-out comparison pass |
| [doublegate/cado-nfs-modern](https://github.com/doublegate/cado-nfs-modern) | Independent GPU ECM, P-1/P+1, and NFS performance fork | Shared arithmetic host-tested, including 2048-bit inputs; GPU performance not reproduced |
| [GregDMeyer/parallel-spooky-pebbling](https://github.com/GregDMeyer/parallel-spooky-pebbling) | Author implementation of parallel measurement-based register scheduling | Source inspected; relevant to Regev arithmetic; Julia search not executed |
| [sachncs/tensift](https://github.com/sachncs/tensift) | Independent Rust implementation of tensor-network Schnorr sieving | Source and pipeline inspected; factoring performance and scaling not reproduced |
| [iGentAI/factorlab](https://github.com/iGentAI/factorlab) | Factoring experiments and model-specific lattice-profile certificates | Useful reference for both projects; whole suite not run; no general factoring lower bound inferred |
| [iliazintchenko/agent-factoring](https://github.com/iliazintchenko/agent-factoring) | Catalogue of attempted factoring approaches and reference implementations | Survey source; broad barrier assertions are not accepted as proved theorems |

The TNSS URL used during discovery redirects to `sachncs/tensift`; this is an
independent implementation, not automatically the paper authors' original code.
Third-party repositories were not modified. Their claims are not treated as
validated merely because a README reports a benchmark or links a paper.

## The selected component

Martin Ekerå's [Quaspy](https://github.com/ekera/quaspy) implements the methods in
[On the success probability of quantum order finding](https://arxiv.org/abs/2201.07791),
published in ACM Transactions on Quantum Computing in 2024. Limited frequency
offset search, lattice recovery, and recovery of a missing smooth component of
the order can salvage information discarded by a strict single-convergent
verifier. The inspected implementation is pinned at
`8040affdf08814ef7d451d9797d28f7645856151`.

Our adapter receives exactly the public modulus, public base, precision and
measured frequency. It passes a counted modular-group element to the author's
solver, verifies a returned exponent by modular exponentiation, and validates
every factor by exact division. It accepts no factor or true-order argument.
The old baseline remains available. No QPU/backend interface is imported.

The frozen comparison uses the current Dark Star verifier's policy: test even
continued-fraction denominators, verify the modular exponent, then try the two
square-root GCDs. Both arms use those same final factor checks. This study does
not use the additional randomized complete-factorization algorithm in Quaspy.

## Held-out result

Before scoring, the plan fixed two seed cohorts. Each has 16 modulus/base cases
at each of 32, 48, 64 and 96 bits, with eight ideal QPE draws per case. In total
there are 128 public cases and 1,024 paired simulated quantum draws. The baseline
uses 2n phase bits. The shorter arm uses 2n-4, with m=n as a public order upper
bound, lattice enumeration, c=1 and frequency offset B=4. The implementation
does not use a hidden smaller order bound to choose m.

| Held-out arm | Verified factor pairs | Trials | Success |
|---|---:|---:|---:|
| Current CF verifier, 2n bits | 152 | 512 | 29.69% |
| Current CF verifier, 2n-4 bits | 147 | 512 | 28.71% |
| Quaspy adapter, 2n bits | 395 | 512 | 77.15% |
| Quaspy adapter, 2n-4 bits | 398 | 512 | 77.73% |
| Quaspy adapter, zero frequency | 0 | 64 | 0% |
| Quaspy adapter, uniform random frequency | 0 | 512 | 0% |

For the primary shorter-Quaspy versus full-precision-CF comparison, 50 independent
modulus/base clusters improve, none worsen, and 14 tie. The exact one-sided sign
test is p=8.88e-16. The factor-success uplift is 48.05 percentage points. Verified
exponents are recovered in 508/512 shorter-Quaspy trials versus 167/512 baseline
trials. These exponents are publicly verified multiples of the true order;
minimality is not claimed from the modular check alone.

The phase-round proxy per verified factor drops from 404.21 to 149.23, a ratio
of 0.3692, or a 63.1% reduction. **This proxy is not elapsed factoring time,
native circuit depth, physical qubits, T count, or an RSA-scale resource estimate.**
It divides the total ideal QPE phase rounds in this mixed-size benchmark by
the number of verified factor successes. No native arithmetic compilation or
hardware timing was measured in this study.

The gain occurs at every tested width. For the shorter arm versus full CF,
factor counts are 95 versus 38 at 32 bits, 119 versus 45 at 48 bits, 112 versus
41 at 64 bits, and 72 versus 28 at 96 bits, out of 128 draws per width.

Extra classical work is charged, not free: the shorter adapter averages about
90 modular-power calls per draw versus about 11 for CF. Signed powers, group
multiplications, GCDs, and inverse calls are recorded. Binary modular multiply
estimates are operation proxies, not internal GMP instruction counts. Each
post-processing call has a 100,000-unit work cap and a two-second timeout.
Measured medians are reported in the result files; the arithmetic operations
do not use a factorization oracle.

## Controls and limits

The true order is computed only inside synthetic oracle setup, using the known
small prime factors, then passed only to the ideal measurement generator and
the subsequent validation assertion. It is never passed to the public adapter.
Keys are reproducible seeded synthetic semiprimes, not production RSA keys.
No target RSA-2048 factors or order were available to the solver.

The sampler evaluates the exact conditional QPE kernel in a 129-bin head using
exact integer phase residues before floating-point evaluation. Omitted tail
events are failures in both arms; their probability is never renormalized away.
The measurement distribution is checked against a separate direct small Shor
work-register state calculation and against high-precision arithmetic above
53 phase bits. The simulation has ideal quantum gates and no device noise.

The zero-frequency and uniform-frequency controls matter: tiny smooth-order
examples can be solved by Quaspy's classical work even without measurement.
The tests explicitly demonstrate this on N=35. Neither null control yields a
factor in the held-out primary population above, so that toy effect does not
explain the reported gain. Zero observed null successes is not a universal
guarantee for every modulus or parameter setting.

All 512 held-out shorter-Quaspy readouts were also replayed in a fresh process
that received only the four public input fields. Every candidate exponent and
factor result matched. The standalone JSON replay CLI passed separately.

This is a component worth keeping for public readout replay and subsequent
end-to-end resource tests. It still needs informative quantum measurements
when applied to hard large moduli. It does not turn a simulator that knows
synthetic factors into a public-key-only RSA-2048 attack.

## Secondary find: a concrete GPU arithmetic extension point

The CADO modernization fork is pinned at
`22e7470a0b9b3b5d0e696032e0208ae8bb2b010f`. Its pre-factoring launcher currently
rejects inputs above 1022 bits. Its shared Montgomery arithmetic is templated
and requires two spare bits per modulus, so a 2048-bit input needs at least
33 64-bit limbs; simply selecting 32 limbs violates that precondition.

A new external-header bridge compiles the author's shared core for the CPU and
checks it against Python integer arithmetic. All 10,240 primitive comparisons
pass over 2,560 odd moduli, including 512 actual 2048-bit moduli at K=33. Checks
cover Montgomery multiplication, aliased multiplication, addition and
subtraction, with boundary operands and random operands.

This validates an extension point in the core, not a complete GPU port or an
RSA factorization. The GPU launcher is unchanged, and CUDA/device execution
was unavailable here. Reported upstream RTX 3090 speedups are not transplanted
to the user's RTX 2080 Ti cards. A GPU implementation still needs dispatch,
device compilation, resource/occupancy checks, and end-to-end validation.

## Reproduce and replay

Use a Python 3.12 virtual environment with `requirements-indie-diamond.txt`.
Clone the author sources and select the inspected commits:

```bash
git clone https://github.com/ekera/quaspy /tmp/qrr-indie-quaspy
git -C /tmp/qrr-indie-quaspy checkout 8040affdf08814ef7d451d9797d28f7645856151
git clone https://github.com/doublegate/cado-nfs-modern /tmp/qrr-indie-cado
git -C /tmp/qrr-indie-cado checkout 22e7470a0b9b3b5d0e696032e0208ae8bb2b010f
QRR_QUASPY_UPSTREAM=/tmp/qrr-indie-quaspy python -m unittest discover -s hardware -p test_qrr_indie_diamond.py -v
python hardware/qrr_indie_diamond_audit.py --upstream /tmp/qrr-indie-quaspy --output /tmp/qrr-indie-rerun
python hardware/qrr_cado_core_audit.py --upstream /tmp/qrr-indie-cado --output /tmp/qrr-cado-core.json
python -m integrations.darkstar_hybrid.quaspy_public_postprocess --upstream /tmp/qrr-indie-quaspy --input results/indie_diamond_20261030/replay_example.json
```

The last command replays a public readout from the held-out benchmark. It loads
only N, base, phase_bits and frequency, and does not invoke the synthetic oracle.
Result files preserve the frozen plan, full losslessly compressed audit,
summary, repository screen, CADO host checks, and verification checksums.
Seven contract tests pass. No hosted CI, QPU jobs or paid resources are requested.
