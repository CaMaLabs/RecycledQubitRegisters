#!/usr/bin/env python3
"""Zero-QPU distribution forensics for the clean11 TCT hardware pilot.

This analyzes the saved baseline/candidate state-count distributions after the
second Fez pilot. It does not submit QPU work and does not fit a hardware noise
model. The goal is to determine whether the failed amplification is merely
uniformized or whether the candidate distribution shows structured displacement
with respect to the model-derived marked set.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / "results" / "tct_surrogate_search" / "qpu_pilot_clean11_v2"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_clean11_qpu_distribution_forensics.json"


def latest_result(directory: Path) -> Path:
    xs = sorted(
        p for p in directory.glob("tct_model_derived_clean11_qpu_pilot_v2_*.json")
        if "preflight" not in p.name
    )
    if not xs:
        raise RuntimeError(f"no clean11 v2 hardware result found in {directory}")
    return xs[-1]


def norm_counts(row: dict, states: int) -> list[float]:
    shots = int(row["shots"])
    out = [0.0] * states
    for k, v in row.get("state_counts_decimal", {}).items():
        out[int(k)] += int(v) / shots
    return out


def bit_marginals(dist: list[float], nbits: int) -> list[float]:
    return [sum(p for s, p in enumerate(dist) if (s >> b) & 1) for b in range(nbits)]


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def nearest_marked_hist(dist: list[float], marked: set[int], nbits: int) -> list[float]:
    out = [0.0] * (nbits + 1)
    for s, p in enumerate(dist):
        if p == 0.0:
            continue
        d = min(hamming(s, m) for m in marked)
        out[d] += p
    return out


def common_constraints(marked: set[int], nbits: int) -> dict[int, int]:
    out = {}
    for b in range(nbits):
        vals = {(s >> b) & 1 for s in marked}
        if len(vals) == 1:
            out[b] = next(iter(vals))
    return out


def constraint_fraction(dist: list[float], common: dict[int, int]) -> float:
    total = 0.0
    for s, p in enumerate(dist):
        if all(((s >> b) & 1) == v for b, v in common.items()):
            total += p
    return total


def tv(a: list[float], b: list[float]) -> float:
    return 0.5 * sum(abs(x - y) for x, y in zip(a, b))


def js_divergence_bits(a: list[float], b: list[float]) -> float:
    # Jensen-Shannon divergence in bits. Empirical descriptor only.
    m = [(x + y) * 0.5 for x, y in zip(a, b)]
    def kl(x, y):
        v = 0.0
        for p, q in zip(x, y):
            if p > 0.0 and q > 0.0:
                v += p * math.log2(p / q)
        return v
    return 0.5 * kl(a, m) + 0.5 * kl(b, m)


def binomial_tail_leq(n: int, p: float, k: int) -> float:
    logs = []
    for i in range(k + 1):
        logs.append(
            math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log1p(-p)
        )
    m = max(logs)
    return math.exp(m) * sum(math.exp(x - m) for x in logs)


def top_states(dist: list[float], n: int = 12) -> list[dict]:
    order = sorted(range(len(dist)), key=lambda s: (-dist[s], s))[:n]
    return [{"state": s, "probability": dist[s]} for s in order if dist[s] > 0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    path = args.result or latest_result(DEFAULT_DIR)
    hw = json.loads(path.read_text(encoding="utf-8"))
    if hw.get("experiment") != "tct_model_derived_clean11_qpu_pilot_v2":
        raise RuntimeError("unexpected result artifact")
    if not hw.get("qpu_job_submitted"):
        raise RuntimeError("artifact is not a submitted QPU result")

    nbits = int(hw["parameter_bits"])
    nstates = 1 << nbits
    marked = {int(x) for x in hw["derived_marked_states"]}
    hwr = hw["hardware_results"]
    b = hwr["uniform_baseline"]
    c = hwr["one_round_clean11"]
    bd = norm_counts(b, nstates)
    cd = norm_counts(c, nstates)
    ud = [1.0 / nstates] * nstates

    common = common_constraints(marked, nbits)
    bm = bit_marginals(bd, nbits)
    cm = bit_marginals(cd, nbits)
    um = [0.5] * nbits
    bh = nearest_marked_hist(bd, marked, nbits)
    ch = nearest_marked_hist(cd, marked, nbits)
    uh = nearest_marked_hist(ud, marked, nbits)

    ideal_candidate = float(hw["ideal_grover_marked_fraction"])
    obs_hits = int(c["marked_hits"])
    shots = int(c["shots"])
    ideal_lower_tail = binomial_tail_leq(shots, ideal_candidate, obs_hits)

    per_marked = []
    for s in sorted(marked):
        per_marked.append({
            "state": s,
            "baseline_probability": bd[s],
            "candidate_probability": cd[s],
            "candidate_minus_baseline": cd[s] - bd[s],
        })

    result = {
        "experiment": "tct_clean11_qpu_distribution_forensics_v1",
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_result": str(path),
        "hardware_job_id": hw.get("job_id"),
        "parameter_bits": nbits,
        "marked_states": sorted(marked),
        "hardware_summary": {
            "baseline_marked_fraction": float(b["marked_fraction"]),
            "candidate_marked_fraction": float(c["marked_fraction"]),
            "candidate_minus_baseline": float(hwr["marked_fraction_difference"]),
            "candidate_over_baseline": hwr.get("marked_fraction_ratio"),
            "two_proportion_z_approx": hwr.get("two_proportion_z_approx"),
            "ideal_candidate_marked_fraction": ideal_candidate,
            "ideal_binomial_probability_candidate_hits_or_fewer": ideal_lower_tail,
            "ideal_binomial_log10_probability": math.log10(ideal_lower_tail),
        },
        "distribution_comparison": {
            "tv_candidate_vs_baseline": tv(cd, bd),
            "tv_baseline_vs_uniform": tv(bd, ud),
            "tv_candidate_vs_uniform": tv(cd, ud),
            "js_bits_candidate_vs_baseline": js_divergence_bits(cd, bd),
            "baseline_common_constraint_fraction": constraint_fraction(bd, common),
            "candidate_common_constraint_fraction": constraint_fraction(cd, common),
            "uniform_common_constraint_fraction": constraint_fraction(ud, common),
        },
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "bit_marginals": {
            "baseline_p1": bm,
            "candidate_p1": cm,
            "uniform_p1": um,
            "candidate_minus_baseline": [cm[i] - bm[i] for i in range(nbits)],
        },
        "nearest_marked_hamming_distance": {
            "baseline": bh,
            "candidate": ch,
            "uniform": uh,
        },
        "per_marked_state": per_marked,
        "top_baseline_states": top_states(bd),
        "top_candidate_states": top_states(cd),
        "classification": (
            "AMPLIFICATION_REVERSED_ON_HARDWARE"
            if float(c["marked_fraction"]) < float(b["marked_fraction"])
            else "AMPLIFICATION_NOT_ESTABLISHED"
        ),
        "interpretation_boundary": (
            "This is descriptive analysis of finite-shot hardware output. Large empirical TV/JS distances can be "
            "inflated by 1024-shot sampling over 512 states. Hamming and marginal structure can identify where the "
            "candidate distribution moved, but cannot identify a unique hardware error mechanism."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("ZERO-QPU TCT CLEAN11 HARDWARE DISTRIBUTION FORENSICS")
    print(f"job_id={hw.get('job_id')} result={path}")
    print(
        f"baseline_marked={b['marked_hits']}/{b['shots']}={b['marked_fraction']:.6f} "
        f"candidate_marked={c['marked_hits']}/{c['shots']}={c['marked_fraction']:.6f} "
        f"z={hwr.get('two_proportion_z_approx')}"
    )
    print(
        f"ideal_candidate={ideal_candidate:.9f} "
        f"P_ideal(X<={obs_hits})={ideal_lower_tail:.3e} "
        f"log10={math.log10(ideal_lower_tail):.3f}"
    )
    print(
        f"common_constraint_fraction baseline={constraint_fraction(bd, common):.6f} "
        f"candidate={constraint_fraction(cd, common):.6f} uniform={constraint_fraction(ud, common):.6f}"
    )
    print("bit_marginal_candidate_minus_baseline=" + json.dumps([round(x, 6) for x in result['bit_marginals']['candidate_minus_baseline']]))
    print("nearest_marked_hamming_baseline=" + json.dumps([round(x, 6) for x in bh]))
    print("nearest_marked_hamming_candidate=" + json.dumps([round(x, 6) for x in ch]))
    print("classification=" + result["classification"])
    print(f"wrote {args.out.resolve()}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
