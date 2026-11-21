# Limits found in the qudit constraint solver

## Finding

The model correctly implements ideal amplitude-amplified pair search. Qudits
reduce the number of logical carriers, but do not change its search complexity.
The implementation is useful for studying the mechanism, not competitive
integer factoring. No quantum hardware execution or native gate benchmarking
has taken place.

The original model was tested unchanged under its 2-million-amplitude guard.
The only implementation extension for the larger tests was an explicit
`max_amplitudes` parameter (also exposed as `--max-amplitudes`). Its default
remains 2 million. Arithmetic, reflection, state preparation and measurement
are unchanged. All original 60 selftests passed again after this extension.

## Expanded classical simulation

Detailed measured results are in stress_results.json; separate distinct-prime
stress results are in distinct_stress.json. Each run includes failed shots,
checks agreement with the exact Grover formula and checks scratch cleanup.

| Input | Factor pair | Encoding | Iterations | Ideal success | Elapsed | Peak memory |
|---|---|---|---:|---:|---:|---:|
| 3721 | 61 x 61 | 24 qubits | 48 | 99.9961% | 23.37 s | 1.02 GiB |
| 6241 | 79 x 79 | 16 qutrits | 62 | 99.9867% | 66.05 s | 2.58 GiB |
| 5767 | 73 x 79 | 16 qutrits | 43 | 99.9823% | 50.95 s | 2.57 GiB |

The first two large inputs are squares, so they primarily stress-test
representation, arithmetic and amplification. The third is the largest
distinct-prime product within the expanded qutrit candidate domain. All three
are tiny classical factoring problems. Each expanded run accepted 1000/1000
sampled shots; this is consistent with the listed exact ideal probabilities,
not evidence of certainty.

These diagnostic iteration counts were chosen using known solution counts;
they establish circuit behavior, not blind factoring performance. In a
separate unknown-count experiment for 899=29*31, a randomized BBHT-style
schedule found the factors in all three tested seeds without supplying the
solution count to the schedule. It used 11, 16 and 38 total oracle applications,
plus 9, 11 and 16 verification runs respectively. Three seeds do not establish
a general reliability estimate. Each oracle requires multiplication and its
inverse; each verification requires another multiplication. The simulator also
does extra diagnostic work that is not part of the proposed quantum circuit.

## Memory ceiling is an implementation limit

With m base-d digits per factor and 2m product digits, the dense state contains
d**(4m) complex amplitudes. Each complex128 amplitude uses 16 bytes.

| Encoding | State amplitudes | One statevector | Status |
|---|---:|---:|---|
| 3 levels, m=4 | 43,046,721 | 0.641 GiB | Executed |
| 3 levels, m=5 | 3,486,784,401 | 51.96 GiB | Projected; not allocated |
| 2 levels, m=6 | 16,777,216 | 0.25 GiB | Executed |
| 2 levels, m=7 | 268,435,456 | 4.00 GiB | Projected; working arrays exceed budget |

The machine reported about 9 GiB available RAM before the expanded runs. Each
stress child had a 5 GiB address-space limit. The next complete qutrit digit
step is outside this budget even for one vector. This is a tested capacity
boundary for this dense implementation and register layout, not a physical
limit of qudits. An optimized sparse/reduced simulator could go farther without
improving the underlying factoring algorithm. Intermediate arbitrary carrier
dimensions are possible in software; no exhaustive hardware-independent
maximum is claimed.

Under the ORIGINAL 2-million-amplitude guard, the largest candidate-register
capacity is 37 (four 37-level carriers). Candidate values stop at 36. The largest
representable candidate product is 1296=36*36 and the largest semiprime product
in that candidate domain is 961=31*31. A 37-level logical carrier here is only a
software setting, not a demonstrated physical device.

## Coverage fails before the largest supported number

The current algorithm requires BOTH p and q to fit in the selected candidate
range. A number fitting the product register is insufficient.

- At the original maximum bound 36, 74=2*37 has zero success probability.
- At the expanded qutrit bound 80, any needed cofactor above 80 is excluded;
  for example, 166=2*83 is not covered despite being much smaller than 6241.
- At bound 80 the maximum supported product is 6400 and the maximum supported
  semiprime is 6241. These bounds do not imply coverage of every smaller input.

Thus a failed run is not a primality proof. Increasing amplification never
rescues a solution omitted from the initial candidate space.

## Algorithmic ceiling

Let B be the upper candidate bound. There are K=(B-1)**2 ordered candidate
pairs. With S marked pairs the success after k rounds is

    sin((2*k+1) * asin(sqrt(S/K)))**2.

For balanced distinct semiprimes, B is roughly sqrt(N), K roughly N, and S=2.
Reaching the first high-probability peak requires roughly
pi/(4*sqrt(2))*sqrt(N) oracle uses: exponential in the input bit length.

Illustrative asymptotic projections, NOT executions:

| Input length | Approximate oracle uses for a first peak |
|---|---:|
| 64 bits | 2.4 billion |
| 128 bits | 1.0 x 10^19 |
| 2048 bits | On the order of 2^1024 |

Arithmetic and state-preparation costs are additional. These estimates assume
balanced factors and an appropriately chosen range; covering unbalanced
factors can require a much larger symmetric pair space. Unknown solution counts
also require a schedule rather than a single known optimal stopping point.

For these small inputs ordinary trial division took microseconds while dense
simulation took fractions of a second to a minute. That comparison concerns
classical simulation, not future quantum hardware performance. More
fundamentally, this pair-search method does not establish an asymptotic win over
classical trial division's O(sqrt(N)) candidate checks for balanced factoring.

## Does the qudit encoding help?

Matched-candidate experiments for 35 and 899 gave identical ideal probabilities
across radices to numerical precision. The candidate-space dimension, rather
than its digit representation, controls the Grover probability.

No native arithmetic gate decomposition or hardware noise model is included.
Fewer carriers cannot yet be translated into fewer physical operations or
better fidelity. The original optical/entanglement mechanism therefore has not
provided an additional algorithmic speedup in this qudit realization.

## Most useful next algorithm change

Search only one candidate p in 2..floor(sqrt(N)), and reversibly mark N mod p=0.
Then compute q=N/p after finding p. Grover search over that smaller domain has
an ideal O(N**(1/4)) oracle scale for fixed small solution count. It also avoids
requiring the second factor to fit a symmetric candidate register. Division
and modular arithmetic still need reversible gate implementations. This is a
proposed next version, not a feature or result of the current code, and remains
exponential in bit length rather than matching Shor's scaling.

Reference for unknown-solution quantum search and the unstructured search
query bounds: Boyer, Brassard, Hoyer and Tapp, *Tight bounds on quantum
searching*, https://arxiv.org/abs/quant-ph/9605034.
These query bounds apply to unstructured search, not to all possible factoring
algorithms.
