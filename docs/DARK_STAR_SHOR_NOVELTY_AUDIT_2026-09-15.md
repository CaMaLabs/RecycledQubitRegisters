# Preliminary novelty audit: residue-conditioned Shor preconditioning

Date: 2026-09-15

Status: preliminary literature audit, not a legal/patent novelty opinion.

## Question under review

The repository currently studies the following specific construction:

1. start from an odd composite `N` and public Shor base `a` with `gcd(a,N)=1`;
2. when the public selector `N mod 3 == 2` holds, replace the order-finding base with `b = a^3 mod N`;
3. use an adaptive / recycled phase-estimation workflow that can stop after a publicly verified denominator is recovered;
4. exploit the identity

```text
ord_N(a^3) = ord_N(a) / gcd(ord_N(a), 3)
```

so that rows with `3 | ord_N(a)` have an exactly threefold smaller order;
5. rely on the public residue condition only as a selector that enriches those rows, not as hidden knowledge of the order or factors.

The potential contribution is therefore **not** the power/order identity, the use of QPE in Shor, qubit recycling, or smooth-exponent preprocessing individually. The question is whether prior work already combines a public residue-class selector with an odd-power base transform specifically to lower the expected adaptive/recycled order-finding precision or stopping cost.

## Preliminary conclusion

No direct prior proposal matching that complete combination was found in the first targeted search pass.

That is encouraging but is not enough to claim novelty. The current manuscript language should remain conservative:

> The elementary order identity and odd-power transform are known mathematics. The candidate contribution is the public residue-conditioned selector, its use in an order-blind adaptive/recycled Shor workflow, and the controlled resource validation.

A stronger novelty statement should wait for a broader scholarly and patent search.

## Clearly established prior art / background

### 1. Shor / Miller reduction from factoring to order finding

Shor's factoring algorithm uses the multiplicative order of a public base modulo `N`, followed by classical GCD extraction. The reduction itself builds on earlier classical number-theoretic work by Miller.

Relevant baseline:

- Peter W. Shor, *Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer*, SIAM Journal on Computing 26(5), 1997.

Implication for this project: selecting and transforming the public base remains inside the standard order-finding framework; the existence of the order identity itself cannot be presented as a new factoring reduction.

### 2. Semiclassical Fourier transform / iterative phase extraction

Robert B. Griffiths and Chi-Sheng Niu showed that the Fourier transform before final measurement in Shor can be implemented semiclassically with measurement and classical feed-forward.

- R. B. Griffiths and C.-S. Niu, *Semiclassical Fourier Transform for Quantum Computation*, Physical Review Letters 76, 3228 (1996).
- DOI: `10.1103/PhysRevLett.76.3228`

Implication: single-control-qubit / iterative phase extraction is established prior art.

### 3. Qubit recycling in Shor

Martín-López et al. experimentally demonstrated Shor with a recycled control qubit.

- E. Martín-López, A. Laing, T. Lawson, R. Alvarez, X.-Q. Zhou, J. L. O'Brien, *Experimental realization of Shor's quantum factoring algorithm using qubit recycling*, Nature Photonics 6, 773-776 (2012).
- DOI: `10.1038/nphoton.2012.259`
- arXiv: `1111.4147`

Implication: the recycled-register architecture is not the novelty claim. It is the architecture in which a reduced actual order may become an actionable resource reduction when the stopping policy is adaptive.

### 4. Improved classical post-processing from one order-finding run

Ekerå showed that, given the order of a single uniformly selected group element, complete factorization can usually be recovered efficiently with classical post-processing.

- Martin Ekerå, *On completely factoring any integer efficiently in a single run of an order-finding algorithm*, Quantum Information Processing 20, 205 (2021).
- DOI: `10.1007/s11128-021-03069-1`
- arXiv: `2007.10044`

Implication: the literature already contains substantial optimization of what is extracted from an order-finding result. Our claim should be about changing the public input base to alter the order distribution and expected adaptive quantum work, not about being the first to optimize Shor around order structure.

### 5. Pollard `p-1` and smooth-exponent preprocessing

Pollard `p-1` deliberately raises a public base to a smooth exponent and tests a GCD in order to exploit smooth structure in `p-1`.

Implication: generic policies such as `a -> a^105`, `a^1155`, `a^15015`, etc. overlap conceptually with classical smooth-exponent factoring. They should not be described as uniquely PTP-derived or as intrinsically quantum contributions.

The repository's classical-shortcut guardrail is therefore important: if `gcd(a^L +/- 1,N)` or inexpensive repeated-squaring checks already reveal a factor, the row should not be counted as evidence of reduced quantum order-finding cost.

## What appears distinct in the present repository

The first pass did not identify prior work that explicitly uses all of the following together:

```text
public N residue condition
    -> inference about divisibility structure of lambda(N)
    -> deterministic odd-power transform of the public Shor base
    -> enrichment of orders divisible by the selected odd prime
    -> exact order reduction when that factor is present
    -> adaptive/recycled QPE that stops earlier after public verification
    -> measured expected phase-work / native-cost reduction
```

For the current `L=3` rule, the mechanism is especially clean for squarefree semiprimes not divisible by 3:

```text
N mod 3 == 2
    -> factor residues are {1,2} mod 3
    -> at least one of p-1, q-1 is divisible by 3
    -> 3 | lambda(N)
    -> orders are strongly enriched for a factor 3
    -> ord_N(a^3) = ord_N(a)/3 whenever 3 | ord_N(a)
```

The repository's holdouts then test the empirical step between `3 | lambda(N)` and `3 | ord_N(a)` rather than assuming it.

## Important distinction: fixed-width textbook Shor vs adaptive stopping

A reduced actual order does not automatically reduce the width of a conventional fixed-width Shor phase register, which is normally chosen from the size of `N`.

The resource argument in this project depends on an adaptive or staged implementation that can:

- start at lower precision;
- measure / recycle phase information;
- classically reconstruct a candidate denominator;
- verify it using public modular arithmetic;
- stop when a valid factor-producing candidate has been recovered;
- otherwise increase precision.

This distinction should remain explicit in every external description.

## Searches performed in this first pass

Targeted web/scholarly queries included variants of:

```text
Shor a^L base preprocessing multiplicative order
Shor odd power preprocessing order finding
Shor base selection multiplicative order optimization
Shor order reduction factoring
Shor a^3 order finding
N mod 3 Shor algorithm
lambda(N) Shor order
public residue Shor factoring
adaptive Shor order finding stopping precision
semiclassical Shor iterative phase estimation recycled qubit
Pollard p-1 Shor preprocessing smooth exponent
```

These searches recovered the established order-finding, iterative-QPE, recycled-qubit, post-processing, and smooth-exponent literature above, but no direct match for the residue-conditioned selector + transformed base + adaptive stopping construction.

## Remaining novelty-risk searches

Before external submission, the next search pass should explicitly cover:

1. Google Scholar / Crossref / Semantic Scholar citation neighborhoods around Shor, Griffiths-Niu, Martín-López, and Ekerå.
2. Papers on generator/base selection for quantum order finding and hidden subgroup algorithms.
3. Literature on reducing the order of a chosen group element before quantum order finding.
4. Hybrid classical/quantum preprocessing for Shor, including residue-symbol, Jacobi-symbol, Carmichael-function, and subgroup heuristics.
5. Patent databases for Shor preprocessing, adaptive order finding, transformed generators, and residue-conditioned quantum factoring.
6. The Periodic Table of Primes source papers to separate what is genuinely inherited from PTP from what is elementary modular arithmetic.
7. Recent post-2024 papers on resource-reduced Shor, dynamic circuits, adaptive phase estimation, and base selection.

## Current wording recommendation

Safe wording:

> We study a public residue-conditioned preprocessing rule for adaptive Shor order finding. For the tested semiprime populations, `N mod 3 == 2` strongly enriches bases whose order contains a factor 3; replacing `a` with `a^3 mod N` then removes that factor exactly when present. In an order-blind staged/recycled phase-estimation model, this reduces expected stopping precision and cumulative phase-estimation work. A targeted preliminary literature search did not identify a prior proposal combining this public selector with odd-power base transformation specifically for adaptive Shor resource reduction, but a broader novelty review is still required.

Avoid for now:

- "new Shor algorithm";
- "first proof";
- "first quantum speedup";
- "new order identity";
- "asymptotic improvement";
- "breaks RSA faster";
- "PTP proves the factors";
- any claim of measured QPU speedup.

## Next experimental gate

The cleanest next technical gate is a **multi-prime selector panel** using the same preregistered design rather than immediately escalating to large smooth exponents.

For small odd primes `ell` (for example 3, 5, 7), derive public residue conditions on `N mod ell` that imply `ell | lambda(N)` for selected semiprime strata, then test the matched transform

```text
b = a^ell mod N
```

against controls with:

- one independent row per `N`;
- deterministic public base selection;
- identical classical shortcut guardrails;
- exact order-blind staged-QPE expectation;
- held-out numeric ranges;
- correction for multiple selector hypotheses.

If the effect reproduces beyond `ell=3`, it would materially strengthen the claim that the result is a general public residue-to-order-distribution mechanism rather than a special-case artifact.