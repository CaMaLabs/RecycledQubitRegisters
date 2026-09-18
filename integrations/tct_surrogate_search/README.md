# TCT Surrogate Search Compiler Integration

This integration connects the reduced-order FAIR-MAST TCT sensitivity surface in
`CaMaLabs/Fusion_Blanket_Design_TCT` to the placement/compiler experiments in
this repository.

## Workflow

1. In the fusion repository, run `fair_mast_tct_quantum_search_export.py` on the
   `agent/tct-precursor-pacman-supervisor` branch. It exports the existing
   320-scenario sensitivity grid as a frozen JSON search dataset.
2. Pass that JSON to `benchmark_tct_surrogate_search.py` here.
3. The benchmark constructs a Grover-style phase oracle for the marked low-loss
   parameter settings, probes its post-HLS two-qubit interaction graph, and uses
   the interaction-distance/compact-patch screen to select exact-width Fez and
   square-lattice-proxy patches for compilation.

## What this tests

- Whether the TCT reduced-order search produces the narrow/deep interaction
  pattern where the recycled-register placement machinery is useful.
- Native CZ count, depth, size, and exact-width touched-qubit count.
- Interaction-aware fixed placement versus Qiskit's automatic layout.
- Idealized Grover oracle-query counts for the exported marked set.

## What this does not prove

The oracle is a **classically precomputed table oracle**. It is not a reversible
implementation of the FAIR-MAST surrogate. Therefore the idealized Grover query
count is not an end-to-end runtime advantage. A real quantum advantage would
require an efficient coherent implementation of the surrogate/objective,
including state preparation, arithmetic, comparison/uncomputation, error
correction, and readout costs.

The fusion surface itself is reduced-order screening evidence only. It does not
validate TCT on a real tokamak or establish sustained fusion.

The Nighthawk path remains a 10x12 square-lattice topology proxy unless the IBM
account exposes authenticated `ibm_phoenix` connectivity.

No QPU job is submitted by this benchmark.
