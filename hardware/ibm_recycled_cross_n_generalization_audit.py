#!/usr/bin/env python3
"""Zero-QPU cross-N generalization audit for recycled vs wide QPE.

This deliberately moves beyond the repository's N=35 validation case.  It
constructs the same *type* of exact full-register modular permutation directly
from public N, base a, and the QPE bit index for several small odd composites
with different work-register widths.  The multiplicative order and reachable
orbit are never supplied to circuit construction.

For each (N,a), phase precision, topology, and architecture we:
  * synthesize exact controlled full-register modular permutations by cycle
    decomposition and direct basis-state transpositions;
  * exhaustively validate each generated permutation on the full work register;
  * compare one-qubit recycled QPE with conventional wide QPE;
  * compile on exact-width connected topology patches so HLS/routing cannot
    borrow extra physical qubits;
  * report best and median CZ/depth across a small placement ensemble.

The authenticated Fez coupling map is used for heavy-hex.  Nighthawk uses
ibm_phoenix coupling metadata when the account can access it, otherwise the
clearly labeled 10x12 square-lattice proxy used by the preceding audits.

No Sampler is instantiated and no QPU job is submitted.  This remains a
small-N compiler/topology study, not scalable RSA modular arithmetic.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCXGate, QFTGate

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width

REV = "2026-09-16-cross-n-generalization-v1"
OUT = Path("results/qubit_recycling/ibm_recycled_cross_n_generalization.json")


def parse_cases(items: list[str]) -> list[tuple[int, int]]:
    out = []
    seen = set()
    for item in items:
        try:
            n_s, a_s = item.split(":", 1)
            n, a = int(n_s), int(a_s)
        except Exception as exc:
            raise SystemExit(f"invalid case {item!r}; expected N:a") from exc
        if n < 3 or n % 2 == 0 or a <= 1 or math.gcd(n, a) != 1:
            raise SystemExit(f"case {item!r} must use odd N>=3 and gcd(N,a)=1")
        if (n, a) not in seen:
            seen.add((n, a))
            out.append((n, a))
    if not out:
        raise SystemExit("provide at least one N:a case")
    return out


def work_bits_for(n: int) -> int:
    return max(1, (int(n) - 1).bit_length())


def modular_permutation(n: int, multiplier: int, work_bits: int) -> list[int]:
    dim = 1 << work_bits
    perm = []
    for x in range(dim):
        perm.append((multiplier * x) % n if x < n else x)
    if sorted(perm) != list(range(dim)):
        raise AssertionError("modular mapping is not a permutation")
    return perm


def cycles_of(perm: list[int]) -> list[list[int]]:
    seen = [False] * len(perm)
    cycles = []
    for start in range(len(perm)):
        if seen[start]:
            continue
        cur = start
        cyc = []
        while not seen[cur]:
            seen[cur] = True
            cyc.append(cur)
            cur = perm[cur]
        if len(cyc) > 1:
            cycles.append(cyc)
    return cycles


def star_transpositions(cycle: list[int], pivot_index: int) -> list[tuple[int, int]]:
    pivot = cycle[pivot_index]
    ordered = cycle[pivot_index + 1 :] + cycle[:pivot_index]
    # Applying these in list order reproduces the cycle under the same classical
    # convention used below: each transposition swaps the current basis label.
    return [(pivot, v) for v in reversed(ordered)]


def apply_transpositions(x: int, trans: list[tuple[int, int]]) -> int:
    y = x
    for u, v in trans:
        if y == u:
            y = v
        elif y == v:
            y = u
    return y


def bit(value: int, index: int) -> int:
    return (value >> index) & 1


def apply_fold(value: int, target: int, diff: int, work_bits: int) -> int:
    out = int(value)
    if bit(out, target):
        for j in range(work_bits):
            if j != target and bit(diff, j):
                out ^= 1 << j
    return out


def choose_target(u: int, v: int, work_bits: int) -> dict:
    diff = u ^ v
    if not diff:
        raise ValueError("identical transposition endpoints")
    rows = []
    for target in range(work_bits):
        if not bit(diff, target):
            continue
        u2 = apply_fold(u, target, diff, work_bits)
        v2 = apply_fold(v, target, diff, work_bits)
        if (u2 ^ v2) != (1 << target):
            raise AssertionError("basis fold did not make endpoints adjacent")
        zeros = sum(
            1 for j in range(work_bits)
            if j != target and bit(u2, j) == 0
        )
        rows.append((zeros, target, u2))
    zeros, target, u2 = min(rows)
    return {"target": int(target), "u2": int(u2), "zero_masks": int(zeros)}


def primitive_classical(x: int, u: int, v: int, target: int, work_bits: int) -> int:
    diff = u ^ v
    y = apply_fold(x, target, diff, work_bits)
    u2 = apply_fold(u, target, diff, work_bits)
    if all(bit(y, j) == bit(u2, j) for j in range(work_bits) if j != target):
        y ^= 1 << target
    return apply_fold(y, target, diff, work_bits)


def validate_primitive(u: int, v: int, target: int, work_bits: int) -> None:
    for x in range(1 << work_bits):
        got = primitive_classical(x, u, v, target, work_bits)
        expected = v if x == u else u if x == v else x
        if got != expected:
            raise AssertionError(f"primitive failed ({u},{v}) at x={x}")


def plan_transpositions(perm: list[int], work_bits: int) -> tuple[list[tuple[int, int]], dict]:
    all_trans = []
    cycle_meta = []
    for cyc in cycles_of(perm):
        candidates = []
        for p in range(len(cyc)):
            trans = star_transpositions(cyc, p)
            basis_cx = sum(2 * ((u ^ v).bit_count() - 1) for u, v in trans)
            masks = 0
            for u, v in trans:
                masks += 2 * choose_target(u, v, work_bits)["zero_masks"]
            candidates.append((basis_cx, masks, cyc[p], trans))
        basis_cx, masks, pivot, trans = min(candidates, key=lambda x: (x[0], x[1], x[2]))
        all_trans.extend(trans)
        cycle_meta.append({
            "cycle_length": len(cyc),
            "pivot": int(pivot),
            "basis_change_cx": int(basis_cx),
            "pattern_x": int(masks),
        })

    for x, expected in enumerate(perm):
        if apply_transpositions(x, all_trans) != expected:
            raise AssertionError("transposition network failed full-register validation")

    total_basis = 0
    total_masks = 0
    for u, v in all_trans:
        ch = choose_target(u, v, work_bits)
        validate_primitive(u, v, ch["target"], work_bits)
        total_basis += 2 * ((u ^ v).bit_count() - 1)
        total_masks += 2 * ch["zero_masks"]

    return all_trans, {
        "cycle_count": len(cycle_meta),
        "basis_transpositions": len(all_trans),
        "direct_mcx": len(all_trans),
        "basis_change_cx": int(total_basis),
        "pattern_x": int(total_masks),
        "full_register_validation": True,
        "cycle_meta": cycle_meta,
    }


def append_controlled_transposition(qc, phase_control, work, u: int, v: int, work_bits: int) -> dict:
    work = list(work)
    diff = u ^ v
    ch = choose_target(u, v, work_bits)
    target = ch["target"]
    u2 = ch["u2"]
    folded = [j for j in range(work_bits) if j != target and bit(diff, j)]
    for j in folded:
        qc.cx(work[target], work[j])
    controls = [work[j] for j in range(work_bits) if j != target]
    masked = []
    for j in range(work_bits):
        if j == target:
            continue
        if bit(u2, j) == 0:
            qc.x(work[j])
            masked.append(work[j])
    qc.append(MCXGate(1 + len(controls)), [phase_control] + controls + [work[target]])
    for q in reversed(masked):
        qc.x(q)
    for j in reversed(folded):
        qc.cx(work[target], work[j])
    return {"direct_mcx": 1, "basis_change_cx": 2 * len(folded)}


def append_modular(qc, phase_control, work, n: int, multiplier: int, work_bits: int, cache: dict) -> dict:
    key = (n, multiplier, work_bits)
    if key not in cache:
        perm = modular_permutation(n, multiplier, work_bits)
        cache[key] = plan_transpositions(perm, work_bits)
    trans, meta = cache[key]
    for u, v in trans:
        append_controlled_transposition(qc, phase_control, work, u, v, work_bits)
    return {**meta, "multiplier": int(multiplier)}


def build(kind: str, n: int, a: int, phase_bits: int, scratch_bits: int) -> tuple[QuantumCircuit, list[dict]]:
    wb = work_bits_for(n)
    phase_width = 1 if kind == "recycled" else phase_bits
    phase_q = QuantumRegister(phase_width, "phase_q")
    work = QuantumRegister(wb, "work")
    scratch = AncillaRegister(scratch_bits, "mcx_hls_scratch")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work, scratch, phase,
                        name=f"crossn_N{n}_a{a}_{kind}_{phase_bits}b")
    qc.x(work[0])
    rounds = []
    cache = {}

    if kind == "recycled":
        anc = phase_q[0]
        for k in range(phase_bits - 1, -1, -1):
            dest = phase_bits - 1 - k
            qc.reset(anc)
            qc.h(anc)
            mult = pow(a, 1 << k, n)
            meta = append_modular(qc, anc, work, n, mult, wb, cache)
            meta["qpe_bit"] = k
            rounds.append(meta)
            for j in range(k + 1, phase_bits):
                prior_c = phase_bits - 1 - j
                angle = -2.0 * math.pi / (2 ** (j - k + 1))
                with qc.if_test((phase[prior_c], 1)):
                    qc.p(angle, anc)
            qc.h(anc)
            qc.measure(anc, phase[dest])
    elif kind == "wide":
        for k in range(phase_bits):
            qc.h(phase_q[k])
            mult = pow(a, 1 << k, n)
            meta = append_modular(qc, phase_q[k], work, n, mult, wb, cache)
            meta["qpe_bit"] = k
            rounds.append(meta)
        qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
        qc.measure(list(phase_q), list(phase))
    else:
        raise ValueError(kind)
    return qc, rounds


def summarize(values: list[int | float]) -> dict:
    xs = sorted(float(x) for x in values)
    return {
        "count": len(xs),
        "min": min(xs),
        "median": statistics.median(xs),
        "mean": statistics.fmean(xs),
        "max": max(xs),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU cross-N recycled-register audit")
    ap.add_argument("--cases", nargs="+", default=["21:2", "35:2", "77:2"])
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[16, 32])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--subgraph-samples", type=int, default=8)
    ap.add_argument("--subgraph-seed", type=int, default=62026)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--transpiler-seeds", default="2026")
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    cases = parse_cases(args.cases)
    bits_list = sorted(set(args.phase_bits))
    t_seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not bits_list or min(bits_list) < 1 or args.scratch_bits < 0 or args.subgraph_samples < 1 or not t_seeds:
        raise SystemExit("invalid arguments")

    max_wb = max(work_bits_for(n) for n, _ in cases)
    max_width = max_wb + max(bits_list) + args.scratch_bits
    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, max_width, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, night_src = topo.nighthawk_map(service)
    if max_width > night_full.size():
        raise SystemExit("requested wide width exceeds Nighthawk topology width")
    topologies = {
        "fez_heavy_hex_topology": fez_full,
        "nighthawk_square_lattice_topology": night_full,
    }

    print("ZERO-QPU CROSS-N GENERALIZATION AUDIT: no Sampler or QPU job is used.")
    print(f"Fez={fez.name} Nighthawk_source={night_src['mode']}")
    if night_src.get("proxy"):
        print("IMPORTANT: Nighthawk side is a square-lattice PROXY, not exact Phoenix.")
    print(f"cases={cases} phase_bits={bits_list} patches={args.subgraph_samples} seeds={t_seeds}")

    result = {
        "experiment": "ibm_recycled_cross_n_generalization_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "cases": [{"N": n, "base": a, "work_bits": work_bits_for(n)} for n, a in cases],
        "phase_bits": bits_list,
        "scratch_bits": args.scratch_bits,
        "subgraph_samples": args.subgraph_samples,
        "subgraph_seed": args.subgraph_seed,
        "transpiler_seeds": t_seeds,
        "profile": args.profile,
        "optimization_level": args.optimization_level,
        "nighthawk_source": night_src,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "scope_boundary": (
            "Exact small-N full-register permutation compiler/topology audit only; "
            "not scalable RSA modular arithmetic and no QPU execution."
        ),
        "rows": [],
    }

    patch_cache = {}
    for n, a in cases:
        wb = work_bits_for(n)
        for bits in bits_list:
            for kind in ("recycled", "wide"):
                qc, rounds = build(kind, n, a, bits, args.scratch_bits)
                logical = int(qc.num_qubits)
                direct_mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
                if not all(r.get("full_register_validation") for r in rounds):
                    raise AssertionError("semantic validation failed")
                print(f"\n===== N={n} a={a} bits={bits} kind={kind} width={logical}q direct_mcx={direct_mcx} =====")

                for topology_name, full_cm in topologies.items():
                    cache_key = (topology_name, logical)
                    if cache_key not in patch_cache:
                        salt = args.subgraph_seed + (0 if topology_name.startswith("fez") else 1_000_003)
                        patch_cache[cache_key] = ens.patch_ensemble(
                            full_cm, logical, args.subgraph_samples, salt
                        )
                    for patch in patch_cache[cache_key]:
                        subcm = cap.relabeled_subgraph(full_cm, patch["nodes"])
                        backend = topo.generic(logical, subcm)
                        good = []
                        for seed in t_seeds:
                            try:
                                st = width.compile_one(qc, backend, args.profile, args.optimization_level, seed)
                                touched = int(st["compiled_touched_qubits"])
                                if touched > logical:
                                    raise AssertionError("capacity lock violated")
                                good.append({
                                    "success": True,
                                    "N": n,
                                    "base": a,
                                    "work_bits": wb,
                                    "phase_bits": bits,
                                    "kind": kind,
                                    "topology": topology_name,
                                    "logical_qubits": logical,
                                    "patch_index": int(patch["patch_index"]),
                                    "patch_mode": patch["mode"],
                                    "patch_nodes": [int(x) for x in patch["nodes"]],
                                    "patch_undirected_edges": int(patch["stats"]["undirected_edges"]),
                                    "patch_mean_degree": float(patch["stats"]["degree_mean"]),
                                    "seed_transpiler": seed,
                                    "total_direct_mcx": direct_mcx,
                                    "compiled_touched_qubits": touched,
                                    **{k: v for k, v in st.items() if k != "compiled_touched_qubits"},
                                })
                            except Exception as exc:
                                result["rows"].append({
                                    "success": False,
                                    "N": n,
                                    "base": a,
                                    "work_bits": wb,
                                    "phase_bits": bits,
                                    "kind": kind,
                                    "topology": topology_name,
                                    "logical_qubits": logical,
                                    "patch_index": int(patch["patch_index"]),
                                    "seed_transpiler": seed,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                })
                        if good:
                            best_seed = min(good, key=lambda r: (r["native_cz"], r["compiled_depth"], r["seed_transpiler"]))
                            result["rows"].append(best_seed)
                            print(
                                f"topology={topology_name} patch={patch['patch_index']} "
                                f"CZ={best_seed['native_cz']} depth={best_seed['compiled_depth']}"
                            )
                        args.out.parent.mkdir(parents=True, exist_ok=True)
                        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    summaries = {}
    for n, a in cases:
        case_key = f"N{n}_a{a}"
        summaries[case_key] = {}
        for bits in bits_list:
            bkey = str(bits)
            summaries[case_key][bkey] = {}
            for topology_name in topologies:
                objs = {}
                for kind in ("recycled", "wide"):
                    rows = [r for r in result["rows"] if r.get("success") and r["N"] == n and r["base"] == a and r["phase_bits"] == bits and r["topology"] == topology_name and r["kind"] == kind]
                    objs[kind] = {
                        "logical_qubits": int(rows[0]["logical_qubits"]),
                        "native_cz": summarize([r["native_cz"] for r in rows]),
                        "compiled_depth": summarize([r["compiled_depth"] for r in rows]),
                        "best": min(rows, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"])) if rows else None,
                    } if rows else None
                rr, ww = objs.get("recycled"), objs.get("wide")
                if rr and ww:
                    summaries[case_key][bkey][topology_name] = {
                        "recycled": rr,
                        "wide": ww,
                        "qubits_saved": ww["logical_qubits"] - rr["logical_qubits"],
                        "best_cz_ratio": rr["best"]["native_cz"] / ww["best"]["native_cz"],
                        "best_depth_ratio": rr["best"]["compiled_depth"] / ww["best"]["compiled_depth"],
                        "median_cz_ratio": rr["native_cz"]["median"] / ww["native_cz"]["median"],
                        "median_depth_ratio": rr["compiled_depth"]["median"] / ww["compiled_depth"]["median"],
                    }
    result["summaries"] = summaries
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== CROSS-N GENERALIZATION SUMMARY =====")
    for n, a in cases:
        ck = f"N{n}_a{a}"
        for bits in bits_list:
            for topology_name in topologies:
                s = summaries[ck][str(bits)].get(topology_name)
                if not s:
                    print(f"N={n} a={a} bits={bits} topology={topology_name}: missing")
                    continue
                print(
                    f"N={n} a={a} work={work_bits_for(n)} bits={bits} topology={topology_name} "
                    f"width {s['wide']['logical_qubits']}->{s['recycled']['logical_qubits']} saved={s['qubits_saved']} | "
                    f"best_R/W_CZ={s['best_cz_ratio']:.4f} best_R/W_depth={s['best_depth_ratio']:.4f} | "
                    f"median_R/W_CZ={s['median_cz_ratio']:.4f} median_R/W_depth={s['median_depth_ratio']:.4f}"
                )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
