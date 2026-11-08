# K028 native arithmetic prototype

The K028 prototype archive has been generated and locally tested. It implements reversible `X`/`CX`/`CCX` unsigned multiplication with a ripple baseline, a carry-save alternative, and Bennett compute/copy/uncompute with clean scratch. The 8-bit deterministic test gave ripple 848 gates / 261 qubits / depth 172 versus carry-save 428 gates / 149 qubits / depth 194. These are prototype gates, **not** official kickmix/Kaggle scores.

The prototype is not yet integrated into the K001 compiler. The source ZIP is currently available as a ChatGPT-generated artifact. Do not represent this document as the source implementation itself. To publish source, commit `k028/native_arithmetic.py`, `k028/install_local.sh`, `k028/README.md`, and `k028/local_test_results.json` from the generated archive into this branch.
