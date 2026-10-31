# A20 direct-cycle multiplier native negative result — 2026-10-30

User ran `python hardware/qrr_a20_direct_cycle_multiplier.py --native`. Both isolated 7-qubit controlled multipliers passed 128/128 exact computational-basis tests including invalid residues, 0 QPU jobs.

|Power|Seed|CZ|Depth|
|---:|---:|---:|---:|
|8|509|31376|91178|
|8|1223|31739|91458|
|29|509|21875|62653|
|29|1223|21659|63250|

A20 uses 107 MCX for power8 and 74 MCX for power29. These ISA costs are substantially larger than the full baseline N35 base8 b4 circuit (seed509 14857 CZ/34038 depth, seed1223 14097 CZ/32814 depth). Note isolated multiplier versus full-circuit comparisons are not controlled comparisons; **A20 is not integrated and its effect on full circuit is untested**. Its isolated native cost makes integration unpromising. Preserve original selected-adder arithmetic and Quaspy postprocessing, don't spend real hardware budget. Next: pursue lower-control-fan-in or optimized modular-addition synthesis with standalone exact proof and apples-to-apples native cost comparisons.
