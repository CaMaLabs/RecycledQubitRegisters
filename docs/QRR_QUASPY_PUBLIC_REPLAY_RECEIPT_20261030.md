# Quaspy public-input replay receipt — 2026-10-30

User supplied terminal output from the Quaspy PR #14 worktree using:

` .venv/bin/python -m integrations.darkstar_hybrid.quaspy_public_postprocess --upstream /tmp/qrr-indie-quaspy --input results/indie_diamond_20261030/replay_example.json`

Output:

```json
{
  "status": "VERIFIED_FACTORS",
  "candidate_exponent": 70172940,
  "factors": [46381, 60521],
  "public_only": true,
  "ledger": {
    "pow_calls": 21,
    "mul_calls": 0,
    "gcd_calls": 1,
    "inverse_calls": 0,
    "binary_mul_estimate": 297,
    "seconds": 0.03011239506304264
  }
}
```

This is one positive public-input replay, not a fresh independent 512-trial rerun. No QPU job, no RSA-2048 factorization. The user did not provide unit test results in this excerpt; do not imply test suite passed as a result of this execution.
