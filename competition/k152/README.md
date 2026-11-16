# K152 — actual X/CX/CCX reversible delta oracle on bounded input subdomains

**Gate-level implementation complete for bounded subdomains; no 22-bit Helios circuit or official score win.** The K151 signed Newton correction is reproduced as a deterministic Boolean function `delta(x)`. We construct its output bits' exact algebraic normal form by a Möbius transform, then synthesize every monomial using only `X`, `CX`, and `CCX`, with all AND scratch chains uncomputed.

Full 62-qubit allocation: q0–21 input x (22), q22–35 retained Q14 estimate (14), q36–49 signed correction target (14), q50–61 scratch (12). The oracle is `|x>|y>|d>|0> -> |x>|y>|d XOR delta(x)>|0>`, a reversible involution on the synthesized *bounded* x domain, with full basis-state tests of output, y preservation, x preservation, and scratch clean-up.

**Actual locally measured source CCX counts (not a score proxy)**:
- 6-bit bounded input, 64 values: **499 CCX**, 24 CX, 63 nonzero ANF monomials.
- 8-bit bounded input, 256 values: **2,675 CCX**, 32 CX, 255 monomials.
- 10-bit bounded input, 1024 values: **13,104 CCX**, 40 CX, 1023 monomials.

All three syntheses and bounded state-evolution checks passed locally. These are actual counted reversible gates, but **not** valid full-domain Helios circuits. Even the 10-bit subdomain's direct truth-table oracle alone exceeds the baseline's 1,243 average executed Toffoli gates. A 22-control-degree monomial would need 20 clean ladder scratch bits, exceeding the 12 available. Therefore do not upscale this generic ANF synthesis to a 22-bit Helios submit or claim the correction has an efficient quantum implementation.

## Run on VM

```bash
cd ~/quantum-a26-check
mkdir -p competition/k152
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/f858cb14b39bea8866b84eeecda845babadf5a3c/competition/k152/k152_reversible_delta.py -o competition/k152/k152_reversible_delta.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k152/k152_reversible_delta.py --selftest
"$PY" competition/k152/k152_reversible_delta.py
```

The report is written to `competition/k152/results/gate_audit.json`. Option `--emit-width 6` writes a standalone **bounded example only**, not a full Helios candidate. The script pins the Helios baseline source hash.

## Decision

The compact K151 classical correction representation is real, but a straightforward ANF lookup is quantitatively noncompetitive and does not furnish a valid 22-bit architecture. Next architecture must compute the correction *arithmetically*, exploit low precision and cancellation, or derive a narrow error correction with substantially cheaper nonlinear arithmetic. Do not conflate memory representation (50 bits) with a 62-qubit finished unitary. No actual official score change.

## Independent Ubuntu reproduction (2026-11-15)

The user ran `$PY competition/k152/k152_reversible_delta.py` successfully. `K152_SELFTEST PASS`. Observed gate counts identical to initial run: 6-bit oracle 499 CCX / 24 CX, tested 64/64 basis states; 8-bit oracle 2675 CCX / 32 CX, 81 test cases out of 256; 10-bit oracle 13104 CCX / 40 CX, 94 test cases out of 1024. Output `K152_RESULT {"widths":[6,8,10],"candidate":false,"out":"competition/k152/results/gate_audit.json"}`. This is **negative for naive truth-table architecture**; counts are static, not verifier mean executed cost. No complete 22-bit Helios candidate.
