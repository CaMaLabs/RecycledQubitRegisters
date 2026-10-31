# Quaspy seven contract tests — verified user rerun, 2026-10-30

The user reran the contract suite in `~/Downloads/QRR-Quaspy-Validation` with `QRR_QUASPY_UPSTREAM=/tmp/qrr-indie-quaspy` set.

Command:

```bash
QRR_QUASPY_UPSTREAM=/tmp/qrr-indie-quaspy .venv/bin/python -m unittest discover -s hardware -p test_qrr_indie_diamond.py -v
```

Terminal excerpt shows **all seven named tests `ok`**, with no skipped tests:

- `test_signed_group_powers_and_identity` — ok
- `test_small_smooth_order_can_succeed_without_measurement` — ok
- `test_strict_factor_verification_and_work_cap` — ok
- `test_big_frequency_kernel_against_high_precision` — ok
- `test_distribution_matches_direct_shor_work_register_state` — ok
- `test_public_replay_rejects_oracle_fields` — ok
- `test_tail_is_censored_without_renormalizing` — ok

Terminal footer shown: `Ran 7 tests in 0.046s`. The separately supplied excerpt **does not include the final unittest `OK` line**, so this receipt records seven `ok` lines/no skips without inventing a footer. This supersedes the earlier run with three skips (missing upstream env). Prior user-run synthetic audit `passed=true`; still no QPU execution, no RSA-2048 factorization, and no physical speedup claim.
