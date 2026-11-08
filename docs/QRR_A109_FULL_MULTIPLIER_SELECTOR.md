# A109 — Optimize *whole-multiplier* selection, not isolated adders

**Status:** Source committed; Ubuntu execution pending.

A108 confirmed an exact source match of the frozen A97 multiplier (N35, A8: 12,287 CX; depth 20,957; 18 qubits) and identified large source-operation regions in forward multiplication and inverse cleanup. Section-isolated compiled counts are diagnostic proxies, not additive to the whole circuit.

A108 also exposed a crucial statistical limitation in A107: its permissive postprocessor recovers factors from **244/256 = 95.3125%** of uniform random frequencies at N15, and **3754/4096 = 91.6504%** at N35. Therefore all-success factor counts are weak evidence by themselves. Uniform lattice hits occur for only 12/256 (4.6875%) and 12/4096 (0.29297%) respectively; A107's ideal Aer phase-lattice concentration is a more informative check, but neither establishes quantum advantage or hardware feasibility.

## A109 design

A97 selected each modular addition by the stand-alone adder's CX/depth. A109 starts from its unchanged choices, individually flips the implementation of each distinct modular constant between A87b direct-prefix and A96 dyadic-interval, then **compiles the entire multiplier** with identical `u/cx` target, optimization level, and seed. A move is accepted only if the *complete native multiplier* improves its lexicographic CX/depth objective. It repeats up to three passes, checkpointing each tested candidate and accepted change. No qubits are added. The final circuit and frozen A97 baseline both undergo exhaustive computational-basis verification with clean workspace.

This greedy search is not a proof of global optimality. A winner must later be validated in recycled-QPE ideal Aer phase measurements and IBM Fez target routing. The declared 10% improvement goal is a target, not a known result.

## Run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 300 "$PY" hardware/qrr_a109_full_multiplier_choice_search.py \
 --n 35 --a 8 --level 1 --max-passes 3 \
 --output results/a109_n35_full_multiplier_choice_search.json
```

**Do not promote** any A109 result unless final native counts beat the frozen baseline and exact reversible-basis checks pass. If no change wins, return to structural cancellation/constant-specific arithmetic rather than hiding a negative test.
