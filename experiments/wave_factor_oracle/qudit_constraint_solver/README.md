# Qudit constraint factoring experiment

An executable NumPy statevector model of candidate preparation, reversible
multiplication, equality phase marking, uncomputation, amplitude amplification,
and postselected factor readout. Dimension 2 models qubits; dimension 3 models
qutrits; higher integer dimensions are also supported.

## Run

Requires Python 3.10+ and NumPy. No cloud account or QPU access is needed.

```bash
python -m pip install numpy
python qudit_factor.py --selftest
python qudit_factor.py --N 35 --dimension 3 --digits 2 --max-factor 7 --iterations 0
python qudit_factor.py --N 35 --dimension 3 --digits 2 --max-factor 7 --iterations 2
```

Use `--output result.json` to save results, `--shots 10000` to change sampling,
and `--seed 12345` for repeatability. The bundled example uses seed 12345 and
2000 shots. With no max-factor, candidates are 2 through min(d**digits-1,N-1).
Both factors must fit in this range. No output is NOT a proof of primality.
Candidate ranges in examples are deliberately small; no factors are used in
state preparation or the oracle. The optional selftest independently enumerates
small answers only to validate the simulated operations.

## What is implemented

Each candidate register has m base-d digits, capacity a=d**m. The product
register has 2m digits, capacity a**2. The state has shape (a,a,a**2).

1. Prepare a uniform superposition of valid ordered candidate pairs with R=0.
2. Apply U_mul: |p,q,r> -> |p,q,(r+p*q) mod a**2>.
3. Flip the phase when R=N.
4. Apply U_mul inverse, returning the product register to zero.
5. Reflect about the prepared initial state; repeat steps 2-5 as requested.
6. Compute the product again and sample all outputs. Keep outcomes with R=N.

The product fits without overflow for candidate values <a. The modular
definition makes multiplication reversible even for arbitrary initial R.
The reported success flag is evaluated from the measured product. A coherent
flag qubit could be added with a controlled equality XOR, but is not allocated
in this simulation. Failed shots are included, never silently renormalized away.
Conditional pair probabilities describe the successful branch separately.

The simulator applies arithmetic permutations and the initial-state reflection
directly. It does not compile them into one-/two-qudit gates. NumPy performs
classical p*q operations when simulating the permutation; these operations must
be replaced by a gate decomposition for QPU execution. This is an ideal logical
quantum model, not a hardware-ready circuit or a fast classical factoring tool.
Dense simulation is limited to 2,000,000 amplitudes; several working arrays are
needed, so peak memory is larger than one statevector.

The default guard is unchanged. `--max-amplitudes` can explicitly raise it for
bounded stress runs. For example, the following uses about 2.6 GiB peak memory
on the test machine and takes roughly a minute:

```bash
OPENBLAS_NUM_THREADS=1 python qudit_factor.py --N 6241 --dimension 3 --digits 4 --iterations 62 --max-amplitudes 45000000
```

See LIMITS.md and the benchmark JSON files for expanded tests. Run
`python benchmark_limits.py` for default-limit, coverage, matched-radix and
unknown-solution-count tests. Run `python stress_limits.py` for the expanded
dense runs. Stress children have a 5 GiB address-space ceiling and the parent
has a 300-second timeout per case. These are classical simulator measurements,
not timings or resource estimates for a quantum processor.

## Results and interpretation

For N=35, candidate pairs from 2..7, there are K=36 ordered pairs and S=2
solutions. The unamplified success probability is 1/18. After k=2 Grover
iterations it is 0.8616657352368371. The accepted branch is the equal coherent
superposition of (5,7) and (7,5), before measurement.

The bundled run accepted 1750/2000 shots: 909 for (5,7), 841 for (7,5).
Sampling fluctuations explain why the empirical fraction differs from the
exact probability. Scratch cleanup probability is 1 to numerical precision.

For a fair comparison using identical candidates and iteration count:

```bash
python qudit_factor.py --N 35 --dimension 2 --digits 3 --max-factor 7 --iterations 2
python qudit_factor.py --N 35 --dimension 3 --digits 2 --max-factor 7 --iterations 2
```

The binary version uses 12 logical qubits; the ternary version uses 8 logical
qutrits, excluding an optional flag. Their unused register capacities differ,
but the populated search space and ideal success probabilities are identical.
The JSON also reports binary qubits needed to match each register's full
capacity, which is a different comparison from matching only the candidates.

Qudits compress representation: a d-level carrier holds log2(d) qubits' worth
of Hilbert-space dimension. They do not intrinsically improve Grover's search
scaling. Whether fewer carriers lead to a practical win depends on native
arithmetic gate counts, gate fidelity, leakage, connectivity and readout. No
hardware superiority is established by this model.

The iteration count is explicit because the number of solutions is generally
unknown. Too many Grover iterations can reduce success. A production solver
would need a schedule for unknown solution count and repeat trials, and must
count all preparation, arithmetic, reflection and verification work. This
search is not Shor's algorithm and does not establish efficient general
factoring or a cryptographic breakthrough.

## Validation

`--selftest` checks 60 combinations across dimensions 2, 3 and 4; targets 15,
21, 35, 49 and prime 17; and iteration counts 0..3. It checks multiplication
and its inverse on arbitrary scratch states, oracle signs against an
independent truth table, the analytic Grover probability, scratch cleanup,
shot accounting, restricted-range behavior and matched-candidate radix results.
See selftest.json for the completed validation result.

For a future circuit backend, Cirq documents native qudit state shapes:
https://quantumai.google/cirq/build/qudits
Choosing a backend and hardware gate set is necessary before assigning gate
counts or claiming a qudit advantage.
