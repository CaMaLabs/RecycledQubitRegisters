# A20 direct-cycle multiplier source result — 2026-10-30

User ran `python hardware/qrr_a20_direct_cycle_multiplier.py`. Status `SOURCE_EXACT_PASS`. Power8: 128/128 computational-basis/control cases, 107 MCX, 756 X, 107 adjacent transposition edges, seven 4-cycles. Power29: 128/128, 74 MCX, 488 X, 74 edges, fourteen 2-cycles. Both are 7-qubit standalone permutations with no additional auxiliary qubits and only X/MCX gates (exact +1 computational phase), preserving invalid-state identity. Zero QPU jobs.

**No native compilation performed in this run; no evidence yet of improved CZ/depth or hardware feasibility.** No original selected arithmetic or Quaspy implementation was modified. Run the already-committed script with `--native` for the isolated native screening; compare to original isolated multipliers before integration.
