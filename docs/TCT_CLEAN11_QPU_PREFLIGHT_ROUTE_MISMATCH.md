# TCT clean11 QPU preflight route mismatch

Date: 2026-09-22

## Observed preflight

The first guarded 11-qubit clean-helper QPU preflight selected the HLS sweep's
minimum-exposure candidate (patch 6, transpiler seed 42) but reproduced it as:

- CZ: 367
- depth: 749
- summed CZ calibration exposure: 1.011
- critical path: 25.9 us
- duration / median T1: 0.176
- duration / median T2: 0.254

The preregistered limits were CZ <= 325 and sum_p(CZ) <= 0.8. Both failed, so
no QPU job was submitted.

All semantic / measurement / clean-ancilla checks passed. The refusal therefore
was not caused by a predicate or bit-order failure.

## Why this differed from the 252-CZ HLS sweep candidate

The source HLS sweep did not compile the candidate directly against the full Fez
backend with a fixed physical initial layout. It first extracted the selected
11-node Fez subgraph, relabeled it to local qubits 0..10, created an exact-width
generic backend for that subgraph, and let the router solve that capacity-locked
local problem with no fixed initial layout.

The first QPU runner instead called the full authenticated Fez backend with
`initial_layout=patch_nodes`. That is a different routing optimization problem.
Although the resulting circuit stayed entirely inside the same physical patch,
it had a different internal permutation / SWAP solution and therefore 367 CZ
rather than the selected 252 CZ.

This is a methodology mismatch, not a reason to loosen the guardrails.

## Correction

`run_tct_model_derived_clean11_qpu_pilot_v2.py` preserves the original
preregistered limits and instead replays the exact source routing problem.

It:

1. reconstructs the same exact-width relabeled patch backend;
2. recompiles with the frozen HLS method and seed;
3. requires exact reproduction of the source CZ/depth/size before proceeding;
4. recovers the final local wires carrying the nine parameter bits;
5. lifts the already-native local operations directly onto the corresponding Fez
   physical qubits, without re-routing;
6. verifies every lifted native operation is supported by the live Fez Target;
7. appends measurements after routing and statevector-verifies the lifted circuit;
8. uses a uniform native-SX baseline on the same physical output/readout qubits;
9. re-applies the unchanged CZ, sum-p, duration, coherence, semantic, and mapping
   guardrails before allowing `--run`.

No QPU job was submitted by the failed preflight.

## Claim boundary

The 252-CZ source result remains a zero-QPU compiler/calibration result until the
exact route-replay preflight reproduces it and passes the live-target checks.
Calibration products are engineering proxies, not measured fidelity. Neither the
HLS result nor any subsequent pilot constitutes fusion validation or an
end-to-end quantum-advantage result.
