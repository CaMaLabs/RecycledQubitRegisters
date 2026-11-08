#!/usr/bin/env python3
"""A25 resource-scaling ledger: transparent sensitivity scenarios, NOT measurements.

Anchors: Gidney (2025) RSA-2048 <1M physical qubits and <7 days
(arXiv:2505.15917); Pappalardo et al (2026) cat-qubit RSA-2048
~22593 cat qubits / 3.14 days under stated biased-noise assumptions
(arXiv:2610.37839). No published anchors here establish CaMaLabs speedup.
"""
import json
import argparse

BITS = (128, 256, 512, 1024, 2048)
ANCHORS = {
    "gidney_2025_surface_code": {
        "anchor_physical_qubits": 1000000,
        "anchor_days": 7.0,
        "qubit_bound": "strict_upper_bound_not_point_estimate",
        "assumptions": "0.1% physical gate error; 1us code cycle; 10us reaction",
        "source": "https://arxiv.org/abs/2505.15917",
    },
    "pappalardo_2026_cat_qubits": {
        "anchor_physical_qubits": 22593,
        "anchor_days": 3.14,
        "qubit_bound": "architecture_specific_approximation",
        "assumptions": "1us cycle; 10us reaction; pZ=5e-4; zero bit flips in primary model",
        "source": "https://arxiv.org/abs/2610.37839",
    },
}


def project(bits, anchor, qubit_exp, time_exp):
    r = bits / 2048
    return {
        "bits": bits,
        "qubits_sensitivity": round(anchor["anchor_physical_qubits"] * r ** qubit_exp),
        "days_sensitivity": round(anchor["anchor_days"] * r ** time_exp, 6),
        "hours_sensitivity": round(24 * anchor["anchor_days"] * r ** time_exp, 4),
        "measurement": False,
    }


def build(qubit_exp=1.0, time_exp=3.0):
    return {
        "status": "SCENARIO_ONLY_NO_CAMLABS_RSA_RUNTIME_CLAIM",
        "qubit_exponent": qubit_exp,
        "time_exponent": time_exp,
        "warning": "Rescaled numbers below 2048 bits are illustrative power-law sensitivities, not predictions. "
                   "Surface and cat qubits are not interchangeable; fixed overhead, error distance, "
                   "logical success probability and magic-state schedules are not modeled. "
                   "Gidney's anchor is an upper bound, not a measured point.",
        "camlabs_integrated_measured": {
            "n35_exact_ideal_bridge": "A23 pass; no circuit-shot demonstration",
            "rsa_128_2048": "NOT_MEASURED",
            "physical_qubits": None,
            "runtime_seconds": None,
            "speedup_over_baseline": None,
        },
        "scenarios": {
            key: {"source": value["source"], "assumptions": value["assumptions"],
                  "qubit_bound": value["qubit_bound"],
                  "rows": [project(n, value, qubit_exp, time_exp) for n in BITS]}
            for key, value in ANCHORS.items()
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--qubit-exp", type=float, default=1.0)
    p.add_argument("--time-exp", type=float, default=3.0)
    a = p.parse_args()
    if not 0 <= a.qubit_exp <= 5 or not 0 <= a.time_exp <= 8:
        p.error("Exponents outside sensitivity bounds")
    result = build(a.qubit_exp, a.time_exp)
    assert set(row["bits"] for row in result["scenarios"]["gidney_2025_surface_code"]["rows"]) == set(BITS)
    assert result["camlabs_integrated_measured"]["runtime_seconds"] is None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
