# Dark Star — rigorous public PTP midpoint-bound audit and RSA / ML-KEM research gap

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-30. **Result: certified generic factor-size midpoint upper bound PASS; QR-residue-only proximity hypothesis FALSIFIED as a generally useful bound.** Exact algebra + deterministic illustrative counterexample + completed CPU GitHub Actions. Zero QPU or IBM Runtime usage **in this audit** (separate earlier genuine IBM Fez N15 hardware evidence preserved).

## 1. Mathematical result, proof and what is actually known from N alone

For an odd semiprime `N=pq`, `1<p<=q`, the exact Fermat midpoint is `x=(p+q)/2`, `y=(q-p)/2`, so `N=x²-y²` and the start of a Fermat search is `x0=ceil(sqrt N)`.

**Public, conditional upper bound:** if **independently certified** `p>=L>0`, then

`x <= floor((L²+N)/(2L))`, so `D=x-x0 <= floor((L²+N)/(2L))-ceil(sqrt N)`.

Proof: `f(t)=(t+N/t)/2` has derivative `(1-N/t²)/2<=0` for `0<t<=sqrt N`. Because `L<=p<=sqrt N`, `x=f(p)<=f(L)`. This is a generic factor-size inequality, **not** a new periodic-prime-table (PTP) acceleration. The hypothesis **p>=L** must be established from actual public evidence (e.g. complete smaller-divisor exclusion or a trusted prime-generation interval). Merely declaring that p is large from an unknown N is invalid and leaks a factor size assumption. Excluding divisibility by 2,3,5,7,11,13,17 lets the illustrative odd semiprimes use only `L=19`; the resulting formal upper bound on midpoint x is tens of millions while the actual x is about 30,000–35,000. Thus the rigorously safe bound is grossly loose.

**Why PTP quadratic-residue masks alone cannot give a closer certificate:** put `M=3·5·7·11·13·17=255255`, and for any odd N define `x_t=(N+1)/2`, `y_t=(N-1)/2`. The identity `x_t²−N=y_t²` is exact (the trivial factorization 1×N). Then for every integer k,

`(x_t+kM)²-N ≡ y_t² (mod M)`.

Hence all those midpoint coordinates pass EVERY individual safe quadratic-residue mask for M, even though most do not correspond to a real global square or a nontrivial factor. This is an infinite periodic family of **local necessary-condition** witnesses. The sieves can eliminate specific impossible x coordinates and save expensive integer isqrt tests. They **cannot** by their modular periodicity alone certify that some entire distant portion of the unsearched factor-midpoint interval contains no valid factor midpoint, nor locate the true first global square. The original QR masks are safe, not sufficient.

### Exact reproducible same-signature counterexample

[Proof implementation](../integrations/darkstar_hybrid/darkstar_public_midpoint_bound_math_audit.py) checked both primality and exact factor/midpoint arithmetic for the **constructed** pair of synthetic 30-bit targets (not an independently frozen factoring-performance holdout):

| Constructed synthetic N | Posthoc factor pair | Public N bit length | Public N mod 255255 | True Fermat offset D |
|---|---|---:|---:|---:|
| `922551607` | `29989×30763` | 30 | **60037** | **2** |
| `537116557` | `8719×61603` | 30 | **60037** | **11985** |

Both actual true midpoints pass every small-prime QR mask. A public classifier given **only (bitlength, N mod 255255)** must give both the same label, despite radically different true factor separations. This does **not** prove that no other public N-dependent features or algorithm can ever predict factor distance, only that this narrow residue signature is insufficient and the QR necessary-condition masks alone cannot certify a small search horizon.

- [Successful original Actions **41019940060** — exact algebra, independent JSON assertion and archive](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/41019940060)
- [Prespecified mathematical audit protocol](DARK_STAR_PUBLIC_MIDPOINT_BOUND_MATH_PROTOCOL.md)
- [Full machine-readable proof certificate / both constructed examples](../results/dark_star_unified/darkstar_public_midpoint_bounds_mathematical_audit.json)

The original N26–N34 classical performance papers and scientific negatives remain untouched.

### RSA-2048 implication even with balanced prime-size promise

A **separate trusted RSA key-generation promise** that both primes are in `[2^1023,2^1024)` implies factor ratio `q/p<2`. Algebra gives `D≈(p+q)/2−sqrt(pq) = sqrt N·((sqrt(q/p)+sqrt(p/q))/2−1)`, with coefficient `≤3/(2sqrt2)−1≈0.06066017` for ratio ≤2. Even this considerably stronger *assumed* balance bound leaves a search horizon of order **2^1020 midpoint coordinates** for a large 2048-bit N. It does NOT remotely turn the few hundred or few thousand tested positions into an RSA-2048 attack. A demonstrated 47× reduction in exact isqrt calls on earlier small composites is neither a 47× unconditional complete factoring wall-time gain nor an exponent collapse.

## 2. Combined honest project-wide feasibility assessment

**Answer to “with every improvement, are we close to breaking RSA or ML-KEM?”: NO.** The experiments measure different surfaces; do NOT multiply independent percentage improvements from PTP isqrt savings, cubic phase selection, 23-wire N35 sources, and 4-qubit ideal LWE optimization into a single end-to-end attack performance figure.

### RSA-2048

- [Earlier genuine IBM Fez QPU trial](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md): **N=15**, a=2, actual recycled phase register full Shor arithmetic, 49/64 factor-producing hardware samples versus 38/64 matched wide, and 55 versus 87 native CZ in this ONE device/source/layout compile. **Real small experimental validation** and fewer simultaneously live logical phase qubits, not a scalable RSA-2048 factoring run.
- [Latest N34 full classical head-to-head](DARK_STAR_N34_ANYTIME_INTERLEAVED_RESULT.md): 24/24 exact 34-bit synthetic factors; precommitted anytime strategy wins only 10/24 vs optimized Brent and 5/24 vs Fermat8+Brent. Both end-to-end speed gates failed. Valid original PTP pruning remains a specialized Fermat candidate sieve, but no general-purpose certified factor-distance selection emerged.
- [Source-level N35 scratch-pruning](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_RESULT.md): true source width 32→23 after removing nine *unused* scratch lines; independent preregistered native-device CZ/depth robustness gate **FAILED**. No physical-feasibility win based on that alone. [N27 conditional model accounting](DARK_STAR_N27_FRESH_RESTORED_END_TO_END_RESULT.md): 5.31% reduction in ideal source CCX for unconditional cube over selected synthetic cases, with no improvement in ideal factor successes and no physical 27-bit QPU, not scalable hardware advantage.
- Competitive resource context: Craig Gidney, *How to factor 2048 bit RSA integers with less than a million noisy qubits* (2025): https://research.google/pubs/how-to-factor-2048-bit-rsa-integers-with-less-than-a-million-noisy-qubits/; projection **less than 1 million noisy physical qubits and less than a week** under explicit gate-error, surface-code and timing assumptions. This is a prospective fault-tolerant engineering estimate, **NOT a verified implemented device**. Our current Shor circuit resources must be benchmarked against realistic error-corrected modular-arithmetic schedules with **all logical/physical qubits, magic states, T/Toffoli gates, native routing, feedforward latency and success probability**, not only source phase-register widths.

**RSA status:** Mathematically vulnerable to sufficiently capable fault-tolerant Shor; our experimental small-N circuit and pruning optimizations do not remotely solve the engineering scale gap or classical RSA-2048 integer factorization.

### ML-KEM / Module-LWE (separate repository)

- NIST official FIPS 203, https://csrc.nist.gov/pubs/fips/203/final, says ML-KEM's Module-LWE basis is believed secure against quantum adversaries, with parameter sets **ML-KEM-512, 768, 1024**. Unlike RSA, Shor order finding does **not** yield a known efficient attack on those parameter sets.
- [CaMaLabs/LWE_GeometryLab audit — 2026-10-25 synthetic reused-basis n56](https://github.com/CaMaLabs/LWE_GeometryLab/blob/main/docs/mlkem512_reused_basis_n56_verified_20261025.md): four of four synthetic degree52 exact posthoc secret/error recoveries, **one of four degree56**, other three **420s timed out**. These are synthetic rank-two negacyclic modules with n52/56, **not degree256 ML-KEM-512** or genuine standardized key recovery. Preserve timeouts/censored outcomes.
- [Cross-program QRR × actual full public ML-KEM-512 objective ideal four-qubit QAOA audit](https://github.com/CaMaLabs/LWE_GeometryLab/blob/main/docs/mlkem512_qrr_quantum_optimization_verified.md): constructed 12 small 4-variable binary search tiles from two genuine full 512-variable public-key objectives plus nulls, with exactly enumerated 16-entry classical local objective comparator. **Zero improvement** on all six real-key tiles, no secret/error recovery, ideal p=1 four-qubit simulation only, no on-device QPU or synthesized full-dimensional reversible cost oracle. The baseline already held the exact local tile optimum in all 12 genuine+null samples.
- The original Fourier, NTT, transform-coherence, bounded-search, recursive/pruned candidate and reused-basis methods are valuable *hypothesis generators*, but neither small synthetic recovery nor cheaper local approximate scores demonstrates a polynomial or practical standardized ML-KEM key recovery mechanism. ML-KEM ciphertext validity, noisy polynomial convolution, full 256-coefficient module structure, all secret/error variables, full security parameters and out-of-sample key recovery must be retained in a conclusive attack benchmark.

**ML-KEM status:** There is no validated full standardized secret-key recovery in these repositories, no known Shor-like efficient quantum attack, and no convincing end-to-end parameter-scaled resource advantage. Not close to breaking ML-KEM-512, -768 or -1024.

## 3. Research decision

This theorem/counterexample is an important stopping rule for **unjustified QR-distance heuristic loops**, not for the original PTP mathematics: preserve it and reuse PTP only when a separate public certificate or externally documented structural promise justifies a close-factor search, or where a fixed bounded sieve wins complete cost on a properly preregistered population. For RSA classical work, optimized general factoring baselines and full-cost comparison matter more than repeated tiny semiprime wins. For quantum Shor, direct controlled-modmul arithmetic, fault-tolerant resource accounting and hardware-circuit validation are the engineering frontier, although no user-paid hardware run is warranted by this audit. For ML-KEM, credible public-only full degree256 key recovery—or a rigorous bound excluding misleading synthetic simplifications—is a separate mathematical frontier.

**No RSA-2048 break, standardized ML-KEM break, RSA-2048 quantum feasibility, source-level resource product, or new asymptotic result is claimed.**
