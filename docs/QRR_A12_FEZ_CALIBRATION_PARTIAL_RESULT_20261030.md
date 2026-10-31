# A12 read-only Fez calibration audit — user result (2026-10-30)

24 target-native CPU compilations; 0 QPU jobs. All partial error proxies saturated to 1.0 and every run flagged missing calibration coverage; dynamic control-flow branch ops were not charged (6 for b4, 15 b6, 28 b8). **Do not interpret 1.0 as a measured device error rate or inferred readout BER.** Best seeds are as ranked by the incomplete log-error proxy and are not experimentally proven optimum.

|base|bits|best partial-proxy seed|best seed CZ|best seed depth|worst seed|
|---:|---:|---:|---:|---:|---:|
|2|4|4093|27974|65251|1223|
|2|6|1223|43574|99905|509|
|2|8|4093|58772|137350|1223|
|8|4|1223|14097|32814|8776|
|8|6|1223|14097|32814|8776|
|8|8|1223|14097|32814|8776|

The base-8 CZ counts are invariant across b4/b6/b8 for a given seed; control flow / mid-circuit measurement overhead and semantic precision need separate audit. A12 is **not** an end-to-end mapping-to-Quaspy error bridge. Preserve previous selected arithmetic and Quaspy baselines. Next: inspect full conditional control-flow operations, calibrations and readout assignments, report unsaturated log-risk and meaningful coverage; independently validate b4/6/8 circuit semantics before attempting physical hardware. Raw JSON resides only in user's local worktree.
