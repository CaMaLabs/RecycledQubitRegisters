# Quaspy unit-test execution receipt — 2026-10-30

User executed from `~/Downloads/QRR-Quaspy-Validation`:

` .venv/bin/python -m unittest discover -s hardware -p test_qrr_indie_diamond.py -v`

Result reported 7 tests, **4 `ok` and 3 skipped** with reason `pinned external checkout required`. These skipped tests are `test_signed_group_powers_and_identity`, `test_small_smooth_order_can_succeed_without_measurement`, and `test_strict_factor_verification_and_work_cap`. Other four sampler contracts passed.

This is **not** a seven-pass test result. Expected cause is omitted `QRR_QUASPY_UPSTREAM` environment variable; earlier replay and full audit explicitly supplied `/tmp/qrr-indie-quaspy` and completed successfully. Rerun with `QRR_QUASPY_UPSTREAM=/tmp/qrr-indie-quaspy .venv/bin/python -m unittest discover -s hardware -p test_qrr_indie_diamond.py -v`. The expected no-skip result is still pending direct user evidence.
