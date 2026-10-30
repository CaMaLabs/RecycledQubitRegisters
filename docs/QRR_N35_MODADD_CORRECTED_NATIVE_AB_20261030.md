# Corrected N35 modular-addition native A/B — 2026-10-30

Research lead Chase Lunsford / CaMaLabs. Results from user-executed `hardware/qrr_n35_modadd_ripple_screen.py --native` after fix `4e816687b916ca1f285bcb96bff87077b282950f`. Raw JSON lives on user workstation at `results/qrr_n35_modadd_ripple_screen/screen.json` and is not included here. Previous pre-fix comparison was a self-comparison and is not valid A/B evidence.

34/34 constants k=1..34. Each arm passes 99 exhaustive relevant add-input cases and +1 phase, clean ancillas. 272 CPU-only Fez native compilations (34 constants × four matched seeds × two arms), no QPU. Delta defined selected minus original ripple. Robust means strict CZ and depth reductions in >=3/4 matched seeds.

**Native outcome:** 16/34 robust wins: 16/17 odd k, 0/17 even k; k=33 only 2/4. Even k all tied in reported median metrics; not a claim that entire compiled circuits are structurally identical. All 17 odd k have negative median CZ and depth deltas.

| k | both-win seeds | median delta CZ | median delta depth |
|---|---:|---:|---:|
|1|3/4|-37.5|-59.5|
|3|4/4|-201.5|-655.5|
|5|4/4|-88|-287.5|
|7|4/4|-80.5|-301.5|
|9|4/4|-116.5|-288.5|
|11|4/4|-133|-535|
|13|4/4|-110.5|-383.5|
|15|4/4|-90|-311.5|
|17|4/4|-97.5|-340|
|19|4/4|-216.5|-571.5|
|21|4/4|-127|-355|
|23|4/4|-104.5|-323.5|
|25|3/4|-94|-321.5|
|27|4/4|-158|-458.5|
|29|4/4|-118|-360|
|31|4/4|-108.5|-382.5|
|33|2/4|-5|-41|

For even k=2,4,...,34: 0/4 simultaneous strict wins, median deltas CZ=0 and depth=0. The frozen selected implementation was already in use: this is a *validated historical comparison*, not a newly discovered improvement from XOR/ancilla research.

Decision: retain selected adder as control, target high-impact weighted constants for new synthesis, require exact controlled phase semantics and complete multiplier/native robustness before promotion. No cryptographic factoring speedup or IBM QPU job established.
