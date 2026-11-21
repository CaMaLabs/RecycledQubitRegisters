# Matched comparison: our divider and a published arithmetic primitive

## Result

The published COMP-N-SUB-I primitive is cheaper than our subtract/restore
implementation in the matched wrapper. Our current arithmetic does not establish
an improvement over this published design. Both have identical logical width
in this wrapper; the published substitution lowers Toffoli count, CNOT count,
uniformly decomposed T-count and depth across all eight tested width pairs.

The executable reference is our transcription of Section 2.2.1, steps 1-8,
printed p.11 of Mukhopadhyay, Gheorghiu and Krovi,
*Improved quantum circuits for division*, arXiv:2603.18110v2:
https://arxiv.org/pdf/2603.18110v2.
The primary comparator is their fully coherent Type-I component; variants
requiring intermediate measurements are excluded to retain our coherent oracle.

## What is actually matched

Three executable circuits are counted: our original saved-history divider,
our optimized in-place divider, and the published COMP-N-SUB-I primitive
substituted into our streaming long-division wrapper.

All preserve P and N through a complete phase-oracle call, use the same candidate
preparation, quotient/remainder semantics for positive divisors, nontrivial-factor
flags, cleanup, diffusion, and final postselection. Invalid P=0 is rejected by
all versions; its otherwise undefined quotient is not part of the equivalence
claim. Inputs may have leading zeros and varying effective divisor lengths.
The gate compiler takes widths, never factors or a divisibility table.

This is NOT an implementation of the authors' complete divider. Their full
register-reuse strategy, shortened schedules and optimized T-pair synthesis are
not included. No claim to beat or reproduce every published full-divider metric
is made. This component comparison isolates a directly compatible operation.

## Actual oracle circuit counts

| N / widths n,m | Implementation | Qubits | Toffoli | CNOT | Logical depth | T+Tdg, uniform decomposition |
|---|---|---:|---:|---:|---:|---:|
| 35 / 6,3 | Original history | 74 | 370 | 348 | 480 | 2590 |
| 35 / 6,3 | Our in-place | 26 | 250 | 372 | 464 | 1750 |
| 35 / 6,3 | Published component, common wrapper | 26 | 166 | 252 | 354 | 1162 |
| 323 / 9,5 | Original history | 146 | 926 | 810 | 1042 | 6482 |
| 323 / 9,5 | Our in-place | 38 | 602 | 954 | 1066 | 4214 |
| 323 / 9,5 | Published component, common wrapper | 38 | 368 | 630 | 788 | 2576 |

These are oracle-only counts, excluding state preparation, diffusion and final
division/readout. The published substitution saves 33.6% and 38.9% of Toffolis
relative to our optimized divider in the two examples. The first prototype's
large resource reductions therefore do not establish superiority to prior art.

The resource grid uses (n,m)=(4,2),(6,3),(8,4),(9,5),(12,6),(16,8),(32,16),
(64,32). Larger rows are circuit construction/counting only, not complete
factor-recovery experiments. At (64,32), our in-place oracle uses 257 qubits and
25074 Toffolis; the published substitution uses the same 257 qubits and 13042
Toffolis. These figures do not measure physical carrier controls or noise.

Qiskit 2.6.2 decomposes all variants into the same exact H/S/Sdg/T/Tdg/X/CX
basis at optimization level zero, with no coupling-map routing. This uses the
standard per-Toffoli synthesis; it does NOT reproduce the paper's specialized
Toffoli-pair T savings. No T approximations or measurement-based uncomputation
are used. Depth is the same conservative logical scheduling model as our
existing benchmark, not hardware time or fault-tolerant reaction latency.

## Independent Aer runs

| Architecture | N | Grover rounds | Ideal success | Accepted / total shots |
|---|---:|---:|---:|---:|
| Published component | 35 | 1 | 100% within roundoff | 2000/2000 |
| Our in-place | 323 | 2 | 90.84472656% | 1836/2000 |
| Published component | 323 | 2 | 90.84472656% | 1798/2000 |
| Published component, filter only | 323 | 0 | 6.25% | 124/2000 |

Different finite shot counts at identical probabilities are sampling variation,
not a success-rate advantage. The new Aer runs agree with the independent
sparse engine within 2.1e-10, with cleaned workspace. Seeds are recorded.
There were no QPU submissions or intermediate measurements.

## Why not just force flag 1?

The filter-only arm already implements final good-flag selection. Every
accepted shot is correct, but 1876 of 2000 preparations were rejected. Its
unconditional acceptance probability is 6.25%, not 100%. Renormalizing only
the surviving state does not remove those failed preparations.

Repeated Grover rounds precede measurement; they are not required to select
the final branch. They can lower expected total cost per accepted answer.

For 323 with the published component:

| Rounds | Ideal success | Expected preparations per success | Expected Toffolis per success |
|---|---:|---:|---:|
| 0, filter only | 6.25% | 16.00 | 2944 |
| 1 | 47.265625% | 2.12 | 1178 |
| 2 | 90.84472656% | 1.10 | 1024 |
| 3 | 96.13189697% | 1.04 | 1355 |

Two rounds minimize Toffoli cost over the tested 0..6 sweep, despite three
rounds having the larger success probability. Relative to three rounds, two
save about 24.5% expected Toffoli work per accepted answer in this case.
Relative to filtering alone, two save about 65.2%.

Expected cost counts all fresh preparations, every oracle, diffusion and final
division/flag generation. Initialization is counted in total unitary gates;
Toffoli cost counts only Toffolis. Measurement duration, routing, classical
control, error correction and wall-clock costs are excluded. The minimum is
retrospective analysis using simulated success probability, not a blind rule
that knows the number of solutions. Prime/no-solution cases have no finite
cost per success; JSON records null rather than inventing a successful outcome.

## Validation

- 1360 exhaustive COMP-N-SUB input pairs at widths 2..5, including inverse,
  compare/subtract semantics and the paper's 3k-1 Toffoli / 4k-5 CNOT counts.
- 992 complete divider/oracle cases for N=4..127 and P=0..7, checking quotient,
  remainder, validity, phase sign and shared-scratch cleanup.
- 128 randomly weighted coherent N/P basis terms, with exact phase action and
  inverse restoration.
- Aer checks of the substituted circuit, filter-only behavior and ordinary
  Qiskit regression/QASM tests.

The tests establish the stated small-instance behavior plus the structural
implementation; they are not a formal proof for every arbitrary width.

## Reproduce

From the repository root after installing requirements-qiskit.txt:

```bash
python experiments/wave_factor_oracle/comparison/benchmark.py
python experiments/wave_factor_oracle/qiskit_runner.py \
  --N 323 --candidate-qubits 5 --iterations 2 --architecture published-cns
python experiments/wave_factor_oracle/qiskit_runner.py \
  --N 323 --candidate-qubits 5 --iterations 0 --architecture published-cns
python -m unittest discover -s experiments/wave_factor_oracle -p 'test_*.py' -v
```

Full tables and round sweeps: `../results/published_comparison.json`.
Executable source: `published_2026.py`; no paper PDFs are redistributed.
This is an implementation/resource study, not a new factoring algorithm or a
demonstrated qudit/native-hardware advantage.
