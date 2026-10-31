# A8 deterministic readout perturbation result — 2026-10-30

User executed `hardware/qrr_quaspy_a8_readout_perturbation.py --upstream /tmp/qrr-indie-quaspy --max-pairs 128` on Quaspy PR #14 branch after integer timeout fix `0946c6aa42e6d5e60b50bf289e42d5c596ed284e`.

Program reported `status=PASS`, 128 pairs. Exact output table:

| Frequency regime | CF factor recoveries | Quaspy factor recoveries | Uplift | CF modular powers | Quaspy modular powers |
|---|---:|---:|---:|---:|---:|
| unchanged | 38/128 | 95/128 | +0.4453125 | 719 | 11825 |
| plus_one | 38/128 | 95/128 | +0.4453125 | 729 | 11919 |
| minus_one | 38/128 | 95/128 | +0.4453125 | 721 | 11960 |
| low_bit_flip | 38/128 | 95/128 | +0.4453125 | 724 | 12011 |
| uniform | 0/128 | 0/128 | 0 | 794 | 21737 |

Identical success counts do not establish identical per-shot factor outcomes. Tiny native-frequency changes are not realistic hardware calibration and are not evidence of tolerance to large phase errors. Uniform random acts as a null. No QPU jobs or RSA-2048 factorization. Raw full A8 JSON remains on user's worktree and is not committed here. Next experiment: phase offsets in QPE peak units and mixed corruption rates with common random seeds, controlled work budgets and paired per-shot transition analysis.
