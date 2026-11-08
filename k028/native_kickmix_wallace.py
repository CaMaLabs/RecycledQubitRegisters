#!/usr/bin/env python3
"""K028-C: Native Kickmix Wallace-tree experiment for _multiply_m.

Produces reference and experimental KMB circuits using identical Precision.
Does NOT imply official-verifier acceptance; compare/verify separately.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIERS = ROOT / "competition/k001/private/official/verifiers"
sys.path.insert(0, str(VERIFIERS))
import kickmix as km


def wallace_multiply_m(builder, inverse, x, square, z, scratch):
    """Compute T(M * square) and add/subtract it to/from z, reversibly.

    The reference interprets square[j]*x[i] at target weight:
       j + wz - wsq + i - width + 2
    Terms outside z are truncated; dropped low bits and overflow have no
    impact on the reference's modular target arithmetic.
    """
    width, wsq, wz = len(x), len(square), len(z) - 2
    n = len(z)
    columns = [[] for _ in range(n)]
    log = []
    temps = []

    def alloc():
        q = builder.alloc_qubits(1)[0]
        temps.append(q)
        return q

    def cx(a, b):
        builder.cx(a, b)
        log.append(("cx", a, b))

    def ccx(a, b, c):
        builder.ccx(a, b, c)
        log.append(("ccx", a, b, c))

    for i in range(width):
        e = wz - wsq + i - width + 2
        for j in range(max(0, -e), wsq):
            position = j + e
            if position >= n:
                continue
            q = alloc()
            ccx(x[i], square[j], q)
            columns[position].append(q)

    stages = 0
    while any(len(col) > 2 for col in columns):
        nxt = [[] for _ in range(n)]
        for i, col in enumerate(columns):
            groups = len(col) // 3
            for k in range(groups):
                a, b, c = col[3*k:3*k+3]
                xor_ab = alloc()
                summed = alloc()
                carried = alloc()
                cx(a, xor_ab)
                cx(b, xor_ab)
                cx(xor_ab, summed)
                cx(c, summed)
                ccx(a, b, carried)
                ccx(xor_ab, c, carried)
                nxt[i].append(summed)
                if i + 1 < n:
                    nxt[i + 1].append(carried)
            nxt[i].extend(col[3*groups:])
        columns = nxt
        stages += 1

    # Materialize two conventional contiguous little-endian addends.
    # They are copies: their origin bits must remain unchanged to uncompute.
    row0 = builder.alloc_qubits(n)
    row1 = builder.alloc_qubits(n)
    for i, col in enumerate(columns):
        if col:
            builder.cx(col[0], row0[i])
        if len(col) > 1:
            builder.cx(col[1], row1[i])

    # z accumulates the modular product; inverse path subtracts it.
    # Reference uncompute is not a bitwise inverse of the forward local
    # gate sequence alone: the two additions/subtractions commute modulo 2^n.
    if inverse:
        builder.isub(row1, target=z)
        builder.isub(row0, target=z)
    else:
        builder.iadd(row0, target=z)
        builder.iadd(row1, target=z)

    # Erase copies of the two reduced operand rows while their source bits
    # are still available. Reversing the compressor before this step would
    # leave entangled/nonzero garbage in row0 and row1.
    for i in reversed(range(n)):
        col = columns[i]
        if len(col) > 1:
            builder.cx(col[1], row1[i])
        if col:
            builder.cx(col[0], row0[i])

    for gate in reversed(log):
        if gate[0] == "cx":
            builder.cx(*gate[1:])
        else:
            builder.ccx(*gate[1:])
    builder.free(row1)
    builder.free(row0)
    if temps:
        builder.free(temps)
    return stages


def build(reference, precision, out):
    b = reference.build_nr_circuit(10, prec=precision)
    b.to_file(str(out), format="kmb")
    return {"path": str(out), "bytes": out.stat().st_size}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=str(ROOT / "competition/k028c/results"))
    p.add_argument("--reference-only", action="store_true")
    args = p.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ref = importlib.import_module("invsqrt.nr_reference_circuit")
    prec = ref.Precision(coef_bits=17, delta_bits=12,
                         product_bits=27, result_bits=28,
                         square_bits=27)

    print("K028-C baseline: building official-source circuit...", flush=True)
    baseline = build(ref, prec, out / "control.kmb")
    print(json.dumps({"control": baseline}), flush=True)
    if args.reference_only:
        return

    original = ref._multiply_m
    calls = [0, 0]
    def patched(builder, inverse, x, square, z, scratch):
        calls[int(bool(inverse))] += 1
        return wallace_multiply_m(builder, inverse, x, square, z, scratch)
    ref._multiply_m = patched
    try:
        print("K028-C experiment: building native Wallace _multiply_m...", flush=True)
        variant = build(ref, prec, out / "wallace_m.kmb")
    finally:
        ref._multiply_m = original

    if not all(calls):
        raise RuntimeError(f"_multiply_m forward and inverse paths not both used: {calls}")
    print(json.dumps({"wallace": variant, "calls": {
        "forward": calls[0], "inverse": calls[1]},
        "status": "BUILT_NOT_YET_OFFICIALLY_VERIFIED"}), flush=True)


if __name__ == "__main__":
    main()
