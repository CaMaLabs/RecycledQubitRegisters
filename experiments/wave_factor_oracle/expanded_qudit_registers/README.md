# Expanded qudit arithmetic registers

This implements the clarified request: keep separate factor registers P and Q
and product register R, while using additional physical levels within each
qudit to expand the register capacities. It does not merge the whole machine
into a single giant carrier.

## Encoding

Each factor register has m carriers with d levels each: a=d**m distinct values.
The product register has 2m carriers, giving a**2 values. Total carrier count is
4m, and the full Hilbert-space dimension is a**4. The exact binary information
capacity is 4m*log2(d) qubits when d is a power of two.

| Levels per carrier | P carriers | Q carriers | R carriers | Factor capacity | Product capacity | Binary capacity |
|---|---:|---:|---:|---:|---:|---:|
| 8 | 2 | 2 | 4 | 64 | 4096 | 24 qubits |
| 16 | 2 | 2 | 4 | 256 | 65536 | 32 qubits |
| 32 | 2 | 2 | 4 | 1024 | 1048576 | 40 qubits |

Capacity includes zero; valid searched factor values are 2 through capacity-1,
or a smaller explicitly requested max-factor. Both factors must fit. One
eight-level qudit encodes three binary logical bits; one 16-level qudit encodes
four, and one 32-level qudit encodes five. Phase is not an extra independently
readable register.

The prior A115/A117 implementation was inspected in
CaMaLabs/RecycledQubitRegisters, branch experiment/a115-spin-qudit-arithmetic:

- hardware/a115_spin7_2_qudit_arithmetic.py, blob ba117119a4c11af9572b7bd1b3d508fc7592de04
- hardware/a117_multitone_gray_cycle.py, blob eb0c5b6894833d490a903cce74db2f34e5593ad5

The eight-level physical labeling [0,2,4,6,7,5,3,1] is preserved and tested.
For even d it extends as [0,2,...,d-2,d-1,d-3,...,1]. This is a basis relabeling,
not a claim that all new arithmetic has a two-layer pulse implementation. The
A117 increment construction cannot automatically be reused as a multiplier or
Grover reflection. Phase correction and hardware control costs are not modeled.

A spin-7/2 carrier has eight levels total. Expanding to 16 or 32 accessible
levels requires a suitable different physical system or additional modes; it
cannot be obtained by relabeling the eight existing levels. The larger settings
in this package are hypothetical logical hardware models.

## Run

Python 3.10+ and NumPy are required.

```bash
python -m pip install numpy
python expanded_registers.py --selftest
python benchmark_expansion.py
python expanded_registers.py --N 1040399 --levels 32 --digits 2 --iterations 567 --output result.json
```

`--digits` is the number of carriers PER factor register. With --digits 2,
there are always eight modeled carriers total. `--max-factor` restricts the
candidate domain. `--iterations` is explicit; too many iterations can decrease
success. `--shots` and `--seed` control sampling; all unsuccessful shots are
included. `--output` writes JSON.

## Executed results

These are ideal classical simulations, not quantum hardware runs.

| Levels per carrier | Target | Factors | Iterations | Ideal success | Simulation time |
|---|---:|---|---:|---:|---:|
| 8 | 3599 | 59 x 61 | 34 | 99.998961% | 0.012 s |
| 16 | 59989 | 239 x 251 | 140 | 99.996100% | 0.044 s |
| 32 | 1040399 | 1019 x 1021 | 567 | 99.999995% | 2.794 s |

Each used eight modeled carriers and accepted 2000/2000 sampled shots. Exact
success probabilities are slightly less than one; the sample outcome is not a
certainty guarantee. Iteration counts were chosen for the known diagnostic
multiplicity of two ordered pairs. This benchmark is not unknown-count blind
factoring. See expansion_results.json for raw results and full success curves.

Twenty Grover cases passed validation. Five independent dense cross-checks
compared compute, equality marking and uncompute on arbitrary complex PQ states
with clean R. State reflection, basis encode/decode, norm and scratch cleanup
were checked. Matched-capacity results were identical across 24 qubits, twelve
four-level carriers, eight eight-level carriers and four 64-level carriers.

## Why this simulator can reach larger inputs

Two separate changes must not be confused:

1. Higher carrier dimensions expand the modeled physical registers. This
   changes information capacity at fixed carrier count.
2. Exact structured simulation avoids allocating amplitudes for unreachable
   product-register values. This improves only classical simulation efficiency.

The state has the restricted form

    sum(p,q) amplitude[p,q] |p,q,0>

between iterations and

    sum(p,q) amplitude[p,q] |p,q,p*q>

after multiplication. It can therefore be represented by a matrix of a**2
amplitudes plus a computed/uncomputed tag and product table. The factor and
product registers still exist logically and physically in the model.

The structured backend supports only these reachable subspaces. It is not a
general quantum simulator for arbitrary product-register states, noise, leakage,
or arbitrary entangling gates. Dense small-state materialization independently
checks the equivalence where supported. Sampling PQ and calculating the
deterministic product has the same joint output distribution as measuring PQR.

At a=1024, a full dense vector would need 16 TiB, while the stored amplitude
matrix needs 16 MiB. Product tables, masks and sampling arrays use additional
memory; the benchmark process peaked around 81 MiB. This dramatic difference
is due to the structured simulator, not a reduction of physical Hilbert-space
dimension or a demonstrated hardware advantage.

## Oracle and hardware costs remain

The software compiles the product/equality oracle by evaluating a**2 classical
products, exposing the marked entries to the simulator. It reports that
preprocessing work separately. This already performs a classical search over
the product table. It is not a quantum speedup or an efficient hardware oracle
implementation. The simulator counts abstract arithmetic block uses but does
not assign native gate counts or pulse times.

The quantum computation remains compute -> mark -> uncompute -> reflect.
For K candidate pairs and S marked pairs its query scale remains
O(sqrt(K/S)); extra levels do not change this formula. Larger domains at the
same carrier count can require more amplification steps. Enlarging dimensions
alone does not solve the factoring scaling problem.

Reference for physical single-qudit search at small dimensions:
https://arxiv.org/abs/2506.09371 (five- and eight-level trapped-ion experiments).
This does not establish control of the much larger registers modeled here.
