# Inverse-square-root phase fitting

This research screen uses the absolute phase margin to model the competition's
rotation charge. It fits the existing angles jointly, tries dropping the
smallest eligible rotations, and uses the linear program's dual weights to rank
new predicates on live wires. Every rounded fit is screened across all 3,133,452
legal inputs. Two independent measurement transcripts establish the numerical
scope. The official verifier determines correctness and score.

On historical K098, the fixed 41-rotation fit retained a minimum margin of
58,597,850 units of (2^{-64}) turns. The six tested drops violated the
tolerance even after refitting the remaining angles. The best tested addition
improved the margin to 63,755,774 units and increased the modeled raw cost by
about 414 points. The 15-trial screen emitted no candidate.
[Recorded results](../evidence/k098_phase_fit_screen.json)

The Ubuntu K191 run reproduced the same baseline margin, six rejected drops,
and best addition cost. It also emitted no candidate, so the official
verifier stayed idle. K191's previously verified cost remains
95,368.96201542337.

The method adapts the published competition cost model and an existing
cutting-plane fit. The independent profiler is QHDL's public bitset simulator.
[Benchmark paper](https://arxiv.org/abs/2610.23832) · [Earlier angle fit](https://github.com/nasir26/vqcc-kaggle/blob/2d3f1d617fbdfceca11bf119984bc66e502c0a10/tasks/invsqrt/angle_lp.py) · [QHDL profiler](https://github.com/manwithacat/vqcc-tools/blob/cd4b30f6806b13096ab0d30946f38c8c9548dfa7/scripts/qhdl_bitsim.py)

## Run on K191

```bash
PROFILE_VENV="$HOME/.venvs/qrr-phase-fit"
PY="$PROFILE_VENV/bin/python"
BACKEND="$HOME/qrr-phase-profile-backend"
git clone https://github.com/manwithacat/vqcc-tools.git "$BACKEND"
git -C "$BACKEND" checkout --detach cd4b30f6806b13096ab0d30946f38c8c9548dfa7
python3 -m venv "$PROFILE_VENV"
"$PY" -m pip install 'numpy>=2.0' 'scipy>=1.13'
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$PY" \
  -m competition.optimizer.research.invsqrt_phase_fit \
  --source "$HOME/quantum-a26-check/competition/k191/results/helios_k191.kmx" \
  --backend "$BACKEND/scripts/qhdl_bitsim.py" \
  --campaign-db "$HOME/quantum-optimizer-runs/k191-qrom-e2af6e6/experiments.sqlite3" \
  --out "$HOME/quantum-optimizer-runs/k191-phase-fit"
```

Run from the optimizer checkout. A profitable modeled result writes a candidate
and uses the saved verifier contract, interpreter, seeds, and worker count. The prior SQLite
database is opened read-only. The JSON report records the candidate's vetted
comparison with the prior fully verified best and the historical reference.
The exact campaign checkpoint does not change.
