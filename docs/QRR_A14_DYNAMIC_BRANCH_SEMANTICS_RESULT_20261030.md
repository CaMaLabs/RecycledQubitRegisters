# A14 dynamic branch/precision audit — user run 2026-10-30

Status printed `SOURCE_AND_COMPILED_PASS`, QPU jobs 0; direct source/native control-flow checks completed. The pasted excerpt did not include the terminal's final closing brace, but all six progress lines and reported status are visible.

|Base|b|Nonidentity modular-power stages|Conditional feedback blocks|Source instructions|Compiled nested operations|
|---|---|---:|---:|---:|---:|
|2|4|4|6|9783|6|
|2|6|6|15|14710|15|
|2|8|8|28|19641|28|
|8|4|2|6|5052|6|
|8|6|2|15|5069|15|
|8|8|2|28|5090|28|

Conditional branch bodies remained present after native compiler pass. Base8's constant CZ totals across b4,b6,b8 in A12 are consistent with its two active multiplication stages; added precision still increases feedback and measurements. This is a structural/source and compilation test, not a hardware fidelity measurement or full proof of phase-estimation distributions from physical execution. Retain optimized arithmetic and Quaspy baseline. No QPU runtime used.
