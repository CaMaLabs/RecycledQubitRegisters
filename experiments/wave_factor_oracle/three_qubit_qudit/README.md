# Three-qubit simulation of an eight-level qudit

Exactly three qubits have 2**3=8 basis states, matching one eight-level qudit.
This package reproduces that equivalence with actual H, X, CX and CCX gate
operations, and exports standard OpenQASM 2 circuits using three qubits.
All executions here are noiseless classical simulations, not QPU runs.

## What fits

| Model | Qubits required for the same full Hilbert space |
|---|---:|
| One eight-level qudit | 3 |
| Eight eight-level carriers from the previous register model | 24 |
| Eight sixteen-level carriers | 32 |
| Eight thirty-two-level carriers | 40 |

Three qubits cannot represent the whole previous expanded-register machine.
The small prototype keeps N classical and uses the eight states as candidate
divisors [3,5,7,9,11,13,15,17]. The second factor is calculated classically
as N/p after a successful measurement. This is a different, smaller algorithm
from storing P, Q and their product simultaneously.

The prior logical-to-physical map [0,2,4,6,7,5,3,1] is retained. Measurement
strings use q2 q1 q0 order. For example, physical outcome 001 maps to candidate
17; its partner for N=323 is 19.

## Run

Requires Python 3.10+ and NumPy.

```bash
python -m pip install numpy
python three_qubit_qudit.py --selftest
python three_qubit_qudit.py --N 323 --iterations 2 --output result.json --qasm circuit.qasm
python three_qubit_qudit.py --N 35 --iterations 1
```

OpenQASM export includes the final measurements and exactly qreg q[3]. It is
generated directly from the same tested gate list. Qiskit is not required to
run the included simulator. The exported circuits have not been executed on
hardware or cross-validated with a Qiskit installation in this session.

## Results

| Target | Rounds | Ideal success probability | Accepted shots |
|---|---:|---:|---:|
| 35 = 5 x 7 | 1 | 100% | 2000/2000 |
| 323 = 17 x 19 | 2 | 94.53125% | 1884/2000 |

The 323 circuit uses 23 H, 20 X and 4 CCX gates, before hardware-specific
decomposition. Four Toffoli gates are not necessarily four native hardware
operations. The iteration counts are diagnostic fixed choices rather than a
schedule for unknown solution count.

The simulator was checked against an independent direct eight-level qudit
calculation for 55 target/iteration combinations, including no-solution cases.
All 64 selective-phase/basis checks passed. A115 modulo-8 increment was
reproduced as CCX(0,1,2), CX(0,1), X(0), and verified on all basis states and
100 random complex superpositions, including inverses. Worst state error
against the qudit model was 2.78e-15 after allowing the known global phase.

## Scope and limit

The oracle is compiled by classically checking N modulo each of the eight
candidates and inserting selective phase flips for successful entries. This
preprocessing already finds the factors in that domain. This circuit therefore
demonstrates encoding, interference and gate-level equivalence; it is not an
efficient reversible division circuit or a quantum factoring speedup.

There is no coherent target, quotient, product or remainder register. Keeping
all of those would require more qubits or a larger qudit. A selective phase
oracle can act on the candidate alone because it preserves each candidate
label, unlike an irreversible overwrite of p by N modulo p.

The fixed candidate list covers every possible smallest odd factor for N<361;
factor 2 is checked and reported classically. For larger N, some inputs still
have an in-range divisor but failure is inconclusive. At N=361=19**2 and
N=899=29*31 there are no marked candidates. Prime inputs also have none. No
finite collection of unsuccessful shots proves primality.

Reference for OpenQASM interoperability:
https://quantum.cloud.ibm.com/docs/en/qiskit/interoperate-qiskit-qasm2
