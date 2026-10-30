# N35 validity-only comparator transplant — preregistration

Research lead: Chase Lunsford / CaMaLabs. 2026-10-30.

Scope: replace only six-bit `predicate(x,35,geq=False)` valid-state marking; retain every other modular wrap predicate, constant adder, controlled multiplier, classical feedforward and all original baselines unchanged. New factorized comparator requires four clean carry bits (taken from existing carry register), returns them clean, and uses existing exact controlled multi-X chain for flag toggling.

Validation gates: (1) 128 exact flag/data truth cases without Qiskit; (2) 256 actual emitted candidate/reference controlled cases (2 control × 2 flag × 64 y), scratch 0, exact +1 phase, including y≥35 identity; (3) all distinct controlled power base2/base8 N35 full-register phase-exact 128 state proof; (4) only then paired 4-seed CPU-only Fez read-only transpilation using seeds 509,1223,4093,8776 and opt1; require 3/4 both CZ/depth improvement for each b4/6/8 and base2/base8. Failures preserved. Never submit to QPU. Do not describe classical Boolean proof as a native resource win.

Status at registration: only (1) run locally; Qiskit unavailable; (2)–(4) pending. No hardware runtime.
