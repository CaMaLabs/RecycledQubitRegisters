# K165 — signed-digit (CSD/NAF) fixed-slope shift/add

**Status: bounded reversible gate-level arithmetic PASS, but no Q14 circuit or full Helios result.**

K165 replaces binary slope multiplication with canonical signed-digit (NAF) shifts. For each of the 8 coherent segment values, adds/subtracts shifted offset bits into a 2Q+1 product accumulator, adds exact rounding bias, XORs high bits into an arbitrary output, and reverses all workspace computation.

## Verified local results

| Q | Method | CCX | CX | X | Scratch | Total | Checked states |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | Binary | 3,428 | 8 | 1,468 | 16 | 26 | 192 |
| 3 | CSD | 3,350 | 8 | 1,236 | 16 | 26 | 192 |
| 4 | Binary | 7,860 | 11 | 3,862 | 20 | 32 | 384 |
| 4 | **CSD** | **7,064** | 11 | 2,606 | 20 | 32 | 384 |

CSD saves **796 CCX (~10.1%)** at Q4 compared with the exactly matched K163 word accumulator. Its cost is still vastly worse than K163 shared-ANF **440 CCX/6 scratch** at Q4, and still does not fit K151's nominal 12-scratch allowance.

The Q14 eight slope constants have binary popcounts **7,9,6,3,6,6,8,6** (total **51**) versus CSD nonzero digits **5,5,3,3,5,4,5,5** (total **35**). This is **only a static signed-digit term count**, not a Q14 quantum gate saving. It suggests reducing arithmetic rows but does not solve workspace.

## Reproduce

```bash
cd ~/quantum-a26-check
mkdir -p competition/k165
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/d2e74e2cdae5163d13f27425b888c7f6eadc0015/competition/k165/k165_csd.py -o competition/k165/k165_csd.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k165/k165_csd.py --selftest
"$PY" competition/k165/k165_csd.py --scaling
```

Output: `competition/k165/results/csd_screen.json`.

## Research priority

K157's X-basis measurement-assisted carry recycle is still unintegrated and needs legal Kickmix conditioned-Clifford semantics. K159 8-segment Q14→Q26 numerical seed full-domain PASS and K160 coefficient lookup 97 CCX versus 1365 CCX remain active. We should prefer improving source-dominant executed Helios score and avoiding more uncompetitive wide reversible multipliers until a 12-scratch arithmetic plan exists.

**No complete 62-qubit KMX or official leaderboard improvement.**
