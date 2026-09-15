#!/usr/bin/env python3
"""End-to-end textbook-RSA recovery demo using the residue-conditioned Shor path.

This is a deliberately small synthetic RSA demonstration, not a claim about
practical RSA-2048 capability.

Default instance
----------------
Public RSA key:
    N = 713 = 23 * 31   (factors hidden from the attack path)
    e = 17

Public Shor/preconditioning policy:
    seed base a = 19
    ell = 5
    N mod 5 = 3 -> trigger
    b = a^5 mod N = 563

Validation-only orders for the built-in ideal QPE simulator are
    ord_N(19)  = 330
    ord_N(563) = 66
so the public odd-power transform removes a factor 5 from the order.

Separation of responsibilities
------------------------------
The *simulator boundary* receives p, q and the true multiplicative order only so
it can generate idealized QPE measurements.  This stands in for a future QPU.

The *attack path* receives only:
    - public N and e,
    - the public Shor base,
    - measured phase integers y and phase precision m.

It recovers and verifies an order candidate with public modular exponentiation,
extracts non-trivial factors with the standard Shor gcd step, reconstructs the
RSA private exponent d, and decrypts the ciphertext.  The hidden p, q and true
order are never passed into the public recovery routine.

The QPE simulator uses the same conservative nearest-bin-only convention as the
repository's staged stopping audits: non-nearest outcomes are discarded even
though some could also recover the order.  No QPU service is contacted.

Encryption is byte-wise textbook RSA solely to keep the demonstration readable;
real RSA deployments use padding/encoding schemes and much larger moduli.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_residue_prime_panel_audit as panel

SCRIPT_REVISION = "2026-09-15-dark-star-rsa-end-to-end-v1"

DEFAULT_N = 713
DEFAULT_E = 17
DEFAULT_BASE = 19
DEFAULT_ELL = 5
DEFAULT_SIM_P = 23
DEFAULT_SIM_Q = 31
DEFAULT_MESSAGE = "DARK STAR RSA"
DEFAULT_SEED = 8776
DEFAULT_OUT = Path("results/dark_star_ptp/dark_star_rsa_end_to_end_demo.json")


def encode_message_bytes(message: str, n: int) -> list[int]:
    raw = message.encode("utf-8")
    vals = list(raw)
    if any(v >= n for v in vals):
        raise ValueError("N must exceed every plaintext byte; use N > 255 for arbitrary UTF-8 bytes")
    return vals


def encrypt_blocks(blocks: list[int], e: int, n: int) -> list[int]:
    return [pow(int(m), int(e), int(n)) for m in blocks]


def decrypt_blocks(ciphertext: list[int], d: int, n: int) -> bytes:
    vals = [pow(int(c), int(d), int(n)) for c in ciphertext]
    if any(v < 0 or v > 255 for v in vals):
        raise ValueError("recovered plaintext block is not a byte")
    return bytes(vals)


def simulator_true_order(a: int, n: int, p: int, q: int) -> int:
    """Validation/simulator-only order computation. Never used by attack logic."""
    if p * q != n:
        raise ValueError("simulator factors do not multiply to N")
    lam = base.lcm(p - 1, q - 1)
    r = base.multiplicative_order_from_lambda(a, n, lam)
    if r is None:
        raise ValueError("simulator base is not coprime to N")
    return int(r)


def make_ideal_measurement_source(true_order: int, seed: int):
    """Return a closure standing in for QPE hardware.

    The closure exposes only measured y and nearest-bin metadata to its caller.
    The true order remains captured inside this simulator boundary.
    """
    rng = random.Random(int(seed))

    def measure(phase_bits: int) -> dict:
        s = rng.randrange(true_order)
        y, p_near = staged.nearest_bin_and_probability(s, true_order, phase_bits)
        credited = rng.random() <= p_near
        return {
            "phase_bits": int(phase_bits),
            "y": int(y),
            "credited_nearest_bin": bool(credited),
            "nearest_bin_probability_simulator_only": float(p_near),
        }

    return measure


def public_order_attack(
    *,
    n: int,
    public_base: int,
    measurement_source,
    start_bits: int,
    step_bits: int,
    shots_per_stage: int,
) -> dict:
    """Recover factors from public data plus QPE measurements only."""
    stage_bits = staged.stage_schedule(n, start_bits, step_bits)
    attempts = 0
    cumulative_phase_rounds = 0
    credited_nearest = 0
    transcript = []

    for stage_index, m in enumerate(stage_bits):
        for shot_in_stage in range(1, shots_per_stage + 1):
            attempts += 1
            cumulative_phase_rounds += m
            measurement = measurement_source(m)
            credited = bool(measurement["credited_nearest_bin"])
            if credited:
                credited_nearest += 1

            public_event = {
                "stage_index": int(stage_index),
                "shot_in_stage": int(shot_in_stage),
                "phase_bits": int(m),
                "y": int(measurement["y"]),
                "credited_nearest_bin": credited,
                "recovery": None,
            }

            # Conservative audit convention: simulator marks non-nearest samples
            # as discarded.  The actual recovery routine below receives only
            # public N/base and the measured (y,m) pair.
            if credited:
                rec = staged.recover_strict_verified(
                    int(measurement["y"]), int(m), int(public_base), int(n)
                )
                public_event["recovery"] = rec
                transcript.append(public_event)
                if rec is not None:
                    factors = tuple(sorted(int(x) for x in rec["factors"]))
                    return {
                        "success": True,
                        "factors": list(factors),
                        "verified_order": int(rec["verified_order"]),
                        "continued_fraction_denominator": int(
                            rec["continued_fraction_denominator"]
                        ),
                        "stop_precision_bits": int(m),
                        "stage_index": int(stage_index),
                        "shot_in_stop_stage": int(shot_in_stage),
                        "shots_attempted": int(attempts),
                        "credited_nearest_bin_events": int(credited_nearest),
                        "cumulative_phase_round_executions": int(cumulative_phase_rounds),
                        "stage_schedule": list(stage_bits),
                        "transcript": transcript,
                    }
            else:
                transcript.append(public_event)

    return {
        "success": False,
        "factors": None,
        "verified_order": None,
        "continued_fraction_denominator": None,
        "stop_precision_bits": None,
        "stage_index": None,
        "shot_in_stop_stage": None,
        "shots_attempted": int(attempts),
        "credited_nearest_bin_events": int(credited_nearest),
        "cumulative_phase_round_executions": int(cumulative_phase_rounds),
        "stage_schedule": list(stage_bits),
        "transcript": transcript,
    }


def reconstruct_private_key(n: int, e: int, factors: list[int]) -> dict:
    if len(factors) != 2:
        raise ValueError("expected two recovered prime factors")
    p, q = sorted(int(x) for x in factors)
    if p * q != n:
        raise ValueError("recovered factors do not multiply to N")
    phi = (p - 1) * (q - 1)
    if math.gcd(e, phi) != 1:
        raise ValueError("public exponent is not invertible modulo phi(N)")
    d = pow(e, -1, phi)
    return {"p": p, "q": q, "phi": int(phi), "d": int(d)}


def run_path(
    *,
    label: str,
    n: int,
    public_base: int,
    simulator_order: int,
    seed: int,
    start_bits: int,
    step_bits: int,
    shots_per_stage: int,
) -> dict:
    source = make_ideal_measurement_source(simulator_order, seed)
    attack = public_order_attack(
        n=n,
        public_base=public_base,
        measurement_source=source,
        start_bits=start_bits,
        step_bits=step_bits,
        shots_per_stage=shots_per_stage,
    )
    return {
        "label": label,
        "public_base": int(public_base),
        "attack": attack,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="End-to-end small-RSA recovery with residue-conditioned Shor order finding"
    )
    ap.add_argument("--N", type=int, default=DEFAULT_N)
    ap.add_argument("--e", type=int, default=DEFAULT_E)
    ap.add_argument("--base", type=int, default=DEFAULT_BASE)
    ap.add_argument("--ell", type=int, default=DEFAULT_ELL)
    ap.add_argument("--message", default=DEFAULT_MESSAGE)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--sim-p", type=int, default=DEFAULT_SIM_P)
    ap.add_argument("--sim-q", type=int, default=DEFAULT_SIM_Q)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    n = int(args.N)
    e = int(args.e)
    a = int(args.base)
    ell = int(args.ell)
    p_sim = int(args.sim_p)
    q_sim = int(args.sim_q)

    if n <= 255:
        raise SystemExit("Use N > 255 so arbitrary plaintext bytes fit in one RSA block.")
    if p_sim * q_sim != n:
        raise SystemExit("Simulator-only p and q must multiply to N.")
    if math.gcd(a, n) != 1:
        raise SystemExit("Public Shor base must be coprime to N.")
    if ell <= 1 or ell % 2 == 0:
        raise SystemExit("ell must be an odd integer > 1.")

    transformed = pow(a, ell, n)
    trigger = n % ell not in (0, 1)

    # Public pre-QPU shortcut guardrail.
    shortcut_a = qvalue.power2_chain_shortcut(a, n)
    shortcut_b = qvalue.power2_chain_shortcut(transformed, n)
    if shortcut_a["factor_found"] or shortcut_b["factor_found"]:
        raise SystemExit(
            "Chosen demo instance is already classically factored by the public shortcut guardrail."
        )

    # Simulator-only information.  This block stands in for the QPU's hidden
    # eigenphase physics and is not passed into public_order_attack().
    r0 = simulator_true_order(a, n, p_sim, q_sim)
    r1 = simulator_true_order(transformed, n, p_sim, q_sim)
    expected_r1 = r0 // math.gcd(r0, ell)
    if r1 != expected_r1:
        raise AssertionError("odd-power order identity failed")

    w0 = pre.factor_witness(a, r0, n)
    w1 = pre.factor_witness(transformed, r1, n)
    if not w0["factor_success"] or not w1["factor_success"]:
        raise SystemExit("Default demo requires factor-capable baseline and transformed orders.")

    blocks = encode_message_bytes(args.message, n)
    ciphertext = encrypt_blocks(blocks, e, n)

    baseline = run_path(
        label="baseline",
        n=n,
        public_base=a,
        simulator_order=r0,
        seed=args.seed,
        start_bits=args.start_bits,
        step_bits=args.step_bits,
        shots_per_stage=args.shots_per_stage,
    )
    transformed_path = run_path(
        label=f"residue_conditioned_ell_{ell}",
        n=n,
        public_base=transformed,
        simulator_order=r1,
        seed=args.seed,
        start_bits=args.start_bits,
        step_bits=args.step_bits,
        shots_per_stage=args.shots_per_stage,
    )

    attack = transformed_path["attack"]
    if not attack["success"]:
        raise SystemExit("Transformed attack did not recover factors by the textbook precision cap.")

    private = reconstruct_private_key(n, e, attack["factors"])
    plaintext_bytes = decrypt_blocks(ciphertext, private["d"], n)
    recovered_message = plaintext_bytes.decode("utf-8")
    decryption_match = recovered_message == args.message
    if not decryption_match:
        raise AssertionError("recovered RSA private key failed to decrypt the ciphertext")

    stage_bits = staged.stage_schedule(n, args.start_bits, args.step_bits)
    exact_baseline = panel.fast_exact_phase_expectation(
        n=n,
        r_validation_only=r0,
        stage_bits=stage_bits,
        shots_per_stage=args.shots_per_stage,
    )
    exact_transformed = panel.fast_exact_phase_expectation(
        n=n,
        r_validation_only=r1,
        stage_bits=stage_bits,
        shots_per_stage=args.shots_per_stage,
    )
    eb = exact_baseline["unconditional"][
        "mean_phase_round_executions_per_attempted_session"
    ]
    et = exact_transformed["unconditional"][
        "mean_phase_round_executions_per_attempted_session"
    ]

    result = {
        "experiment": "dark_star_rsa_end_to_end_demo_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "qpu_submitted": False,
        "rsa_mode": "byte-wise textbook RSA for a small synthetic demonstration",
        "public_input": {
            "N": n,
            "e": e,
            "ciphertext_blocks": ciphertext,
            "seed_base": a,
            "ell": ell,
            "N_mod_ell": n % ell,
            "selector_triggered": trigger,
            "transformed_base": transformed,
        },
        "message_demo": {
            "plaintext_utf8": args.message,
            "plaintext_byte_blocks": blocks,
            "ciphertext_blocks": ciphertext,
        },
        "public_guardrails": {
            "baseline_classical_shortcut": shortcut_a,
            "transformed_classical_shortcut": shortcut_b,
        },
        "simulator_validation_only": {
            "p": p_sim,
            "q": q_sim,
            "lambda_N": base.lcm(p_sim - 1, q_sim - 1),
            "baseline_true_order": r0,
            "transformed_true_order": r1,
            "expected_transformed_order_from_identity": expected_r1,
            "order_reduction_factor": r0 / r1,
            "note": "These values are used only to generate/validate ideal QPE measurements; public recovery does not receive them.",
        },
        "baseline_order_finding": baseline,
        "residue_conditioned_order_finding": transformed_path,
        "exact_staged_phase_model": {
            "baseline": exact_baseline,
            "transformed": exact_transformed,
            "unconditional_phase_round_ratio_transformed_over_baseline": et / eb,
            "unconditional_phase_round_reduction_fraction": 1.0 - et / eb,
        },
        "recovered_private_key": private,
        "decryption": {
            "recovered_plaintext_utf8": recovered_message,
            "matches_original": decryption_match,
        },
        "claim_boundary": {
            "is_actual_rsa_key_reconstruction": True,
            "is_small_synthetic_textbook_rsa": True,
            "uses_ideal_qpe_simulator_not_qpu": True,
            "demonstrates_rsa_2048_capability": False,
            "scalable_modular_arithmetic_implemented": False,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("===== END-TO-END RSA RECOVERY DEMO =====")
    print(f"public key: N={n}, e={e}")
    print(f"message: {args.message!r}")
    print(f"ciphertext blocks: {ciphertext}")
    print(
        f"selector: N mod {ell}={n % ell}; trigger={trigger}; "
        f"base {a}->{transformed}"
    )
    print(f"simulator-only order: {r0}->{r1} ({r0 / r1:.1f}x reduction)")
    for item in (baseline, transformed_path):
        ar = item["attack"]
        print(
            f"{item['label']}: success={ar['success']} "
            f"stop_bits={ar['stop_precision_bits']} "
            f"phase_rounds={ar['cumulative_phase_round_executions']} "
            f"recovered_order={ar['verified_order']} factors={ar['factors']}"
        )
    print(
        "exact expected phase-work ratio transformed/baseline="
        f"{et / eb:.4f} (reduction={(1.0 - et / eb) * 100:.2f}%)"
    )
    print(
        f"reconstructed private key: p={private['p']} q={private['q']} "
        f"phi={private['phi']} d={private['d']}"
    )
    print(f"decrypted: {recovered_message!r}")
    print(f"decryption_match={decryption_match}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
