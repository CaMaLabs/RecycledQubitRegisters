# A9 peak-offset sweep — user-executed 2026-10-30

Executed `hardware/qrr_quaspy_a9_peak_offset_ab.py --upstream /tmp/qrr-indie-quaspy --max-pairs 0` on PR #14-derived worktree. 512 paired held-out synthetic frequency readouts per condition, zero QPU jobs. Run reported status PASS.

|Offset|CF successes|Quaspy successes|CF pow calls|Quaspy pow calls|
|---|---:|---:|---:|---:|
|unchanged|152/512|398/512|5780|45933|
|plus_2|152/512|398/512|5792|47857|
|minus_2|152/512|398/512|5787|47413|
|plus_8|137/512|320/512|5767|65285|
|minus_8|136/512|322/512|5757|65528|
|plus_32|97/512|186/512|5737|77359|
|minus_32|96/512|186/512|5734|77210|
|plus_128|77/512|89/512|5762|82557|
|minus_128|76/512|89/512|5776|81703|
|uniform|0/512|0/512|5960|86745|

Quaspy retains substantial advantage under ±8 and ±32 offsets, narrows at ±128. This tests integer frequency displacements, not a physically calibrated noise distribution or real-device measurements. No RSA attack established. Full per-shot output remains in user's local worktree.
