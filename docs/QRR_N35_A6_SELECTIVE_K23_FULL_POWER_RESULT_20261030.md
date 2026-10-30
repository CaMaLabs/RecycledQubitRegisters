# A6 selective k=23 full controlled-power result — October 30, 2026

Research lead: Chase Lunsford / CaMaLabs. User-executed `python hardware/qrr_n35_a6_selective_k23_power_ab.py --native` using existing Qiskit IBM Open instance for read-only Fez target metadata. Raw detailed JSON lives on user's workstation at `results/qrr_n35_a6_k23_full_power_ab/results.json` (not uploaded to GitHub). No actual QPU submissions.

Six powers [2,4,8,11,16,29] passed exact phase +1, invalid-state identity and full auxiliary cleanup over 128/128 cases each per arm. Candidate substitutions: power2=0, 4=1, 8=1, 11=0, 16=1, 29=1, total four. 48 native CPU compilations, four paired seeds per power; robust criterion simultaneous CZ and depth reduction in >=3/4 seeds.

|Power|Substitutions|Paired wins|Median delta CZ (candidate-baseline)|Median delta depth|Criterion|
|---|---:|---:|---:|---:|---|
|2|0|0/4|0|0|Unchanged control|
|4|1|1/4|+72|+347|FAIL|
|8|1|2/4|-84.5|-2|FAIL|
|11|0|0/4|0|0|Unchanged control|
|16|1|2/4|+19.5|-100.5|FAIL|
|29|1|3/4|-195|-371|PASS|

**Decision:** Accept power29 as a limited controlled-power native compiler win; do not promote global k23 substitution. Next experiment should condition the k23 selection on *public power=29* and compare complete recycled-phase base2/base8 b4/b6/b8 dynamic circuits with original baseline. Existing phase exact proofs do not certify physical wire lineage/feedback latency. No genuine quantum hardware or RSA advantage demonstrated.
