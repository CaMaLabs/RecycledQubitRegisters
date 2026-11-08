# K028-B: Staged Wallace compressor

Implemented in `parallel_compressor.py`, benchmarked by `benchmark_wallace.py`.

## Reproduce
```bash
python3 k028/benchmark_wallace.py --widths 4,5,8,12,16,27 --random-pairs 40
```

## Local measurements

At 27-bit unsigned multiplication modulo 2^27, after Bennett compute/copy/uncompute:

| Metric | Schoolbook ripple | Serial carry-save | Staged Wallace |
|---|---:|---:|---:|
| Gates | 9531 | 5007 | 5007 |
| CCX | 3672 | 2164 | 2164 |
| CX | 5859 | 2843 | 2843 |
| Allocated logical wires | 2674 | 1517 | 1517 |
| Dependency depth | 1578 | 2664 | 264 |

Exhaustive arithmetic verification at widths 4 and 5; 46 deterministic input pairs per width at 8, 12, 16, and 27. Source registers unchanged; every scratch wire zero after execution. The stage compressor consumes only previous-stage bits; this removes the serial carry dependency across compressor columns.

**Caveats:** the depth calculation is for gate dependencies, not routed hardware depth. Allocated logical wires are not necessarily physical qubits. This modular multiplier has *not* been integrated into the official Kickmix K001 circuit or scored by its verifier. To beat K026's 1,851,045 cost frontier, next translate the reversible arithmetic gate IR to K001's accepted format, incorporate multiplier at the correct signed/unsigned and precision semantics, verify the entire inverse-square-root program and score against its true control.
