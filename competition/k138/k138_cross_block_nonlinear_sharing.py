#!/usr/bin/env python3
"""K138: cross-block nonlinear-sharing opportunity screen (read-only).

Different from K135-K137: examine ONE combined reversible transformation
spanning at least five CCX gates and multiple motif boundaries. For each
unconditional contiguous X/CX/CCX run, use bounded CCX-anchored windows;
compute exact ANFs for all interface wires. Compare the original CCX count
with two necessary lower bounds:
  * ceil(log2(max ANF degree)),
  * GF(2) rank of nonlinear output components.

Additionally measure the rank of the nonlinear CCX product polynomials
generated *during* the window. Dependence among products can indicate
shared/intermediate nonlinear structure, but does NOT prove a rewrite.

Important: gaps are only opportunities to investigate. These are not
independent gates that can simply be deleted, and no measured score is
claimed. All gates are modeled as acting on independent input wires.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path

PIN = "e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
ARITY = {"X": 1, "CX": 2, "CCX": 3}
Q = re.compile(r"^q([0-9]+)$")

def parse(line):
    tok = line.strip().split()
    if not tok or tok[0] not in ARITY or len(tok) != ARITY[tok[0]] + 1:
        return None
    if not all(Q.fullmatch(t) for t in tok[1:]):
        return None
    wires = tuple(int(t[1:]) for t in tok[1:])
    if len(wires) != len(set(wires)):
        return None
    return tok[0], wires

def product(a, b, cap):
    if len(a) * len(b) > cap * 32:
        raise OverflowError("ANF expansion budget exceeded")
    out = set()
    for x in a:
        for y in b:
            z = x | y
            if z in out:
                out.remove(z)
            else:
                out.add(z)
            if len(out) > cap:
                raise OverflowError("ANF monomial budget exceeded")
    return out

def gf2_rank(vectors):
    pivot_basis = {}
    for vector in vectors:
        value = set(vector)
        while value:
            pivot = max(value)
            if pivot in pivot_basis:
                value ^= pivot_basis[pivot]
            else:
                pivot_basis[pivot] = value
                break
    return len(pivot_basis)

def analyze(gates, cap):
    wires = sorted({w for _, qs in gates for w in qs})
    index = {w: i for i, w in enumerate(wires)}
    state = {w: {1 << index[w]} for w in wires}
    nonlinear_products = []
    for op, qs in gates:
        if op == "X":
            state[qs[0]] ^= {0}
        elif op == "CX":
            state[qs[1]] ^= state[qs[0]]
        elif op == "CCX":
            p = product(state[qs[0]], state[qs[1]], cap)
            nonlinear_products.append({m for m in p if m.bit_count() >= 2})
            state[qs[2]] ^= p
        else:
            raise ValueError("unexpected opcode")
        if max(len(v) for v in state.values()) > cap:
            raise OverflowError("state exceeds monomial limit")
    outputs = [{m for m in state[w] if m.bit_count() >= 2} for w in wires]
    maximum_degree = max((m.bit_count() for p in state.values() for m in p), default=0)
    degree_lb = (maximum_degree - 1).bit_length() if maximum_degree > 1 else 0
    output_rank = gf2_rank(outputs)
    bound = max(degree_lb, output_rank)
    ccx = len(nonlinear_products)
    product_rank = gf2_rank(nonlinear_products)
    return {
        "wire_count": len(wires),
        "ccx_count": ccx,
        "degree_lower_bound": degree_lb,
        "nonlinear_output_rank_lower_bound": output_rank,
        "combined_ccx_lower_bound": bound,
        "remaining_ccx_gap": ccx - bound,
        "intermediate_nonlinear_product_rank": product_rank,
        "dependent_nonlinear_product_count": ccx - product_rank,
        "max_output_anf_degree": maximum_degree,
        "max_output_monomials": max((len(v) for v in state.values()), default=0),
    }

def contiguous_runs(gates, lower, upper):
    first = None
    for i in range(lower - 1, upper):
        if gates[i] is not None:
            if first is None:
                first = i
        elif first is not None:
            yield first, i
            first = None
    if first is not None:
        yield first, upper

def screen(lines, lower, upper, sizes, maxspan, maxwires, cap):
    parsed = [parse(x) for x in lines]
    items = []
    reasons = collections.Counter()
    for a, b in contiguous_runs(parsed, lower, upper):
        ccx_indices = [i for i in range(a, b) if parsed[i][0] == "CCX"]
        if not ccx_indices:
            continue
        for n in sizes:
            for k in range(len(ccx_indices) - n + 1):
                start, stop = ccx_indices[k], ccx_indices[k + n - 1] + 1
                if stop - start > maxspan:
                    reasons["span_rejected"] += 1
                    continue
                gates = parsed[start:stop]
                w = {q for _, qs in gates for q in qs}
                if len(w) > maxwires:
                    reasons["width_rejected"] += 1
                    continue
                try:
                    evidence = analyze(gates, cap)
                except OverflowError:
                    reasons["anf_budget_rejected"] += 1
                    continue
                reasons["analyzed"] += 1
                if evidence["remaining_ccx_gap"] <= 0:
                    reasons["tight"] += 1
                    continue
                reasons["unresolved"] += 1
                items.append({
                    "start_line": start + 1,
                    "end_line": stop,
                    "length_instructions": stop - start,
                    "scored_source_ccx_upper_bound_saved": evidence["remaining_ccx_gap"],
                    **evidence
                })
    # Prefer the largest potential number of Toffolis, then evidence of
    # dependency among intermediate products. Do not sum overlapping items.
    items.sort(key=lambda x: (
        -x["remaining_ccx_gap"],
        -x["dependent_nonlinear_product_count"],
        x["wire_count"], x["length_instructions"], x["start_line"]
    ))
    return items, dict(reasons)

def selftest():
    chain = [
        ("CCX", (0, 1, 2)),
        ("CCX", (2, 3, 4)),
        ("CCX", (4, 5, 6)),
    ]
    r = analyze(chain, 2000)
    assert r["ccx_count"] == 3 and r["remaining_ccx_gap"] == 0
    # A compute/uncompute pair has no nonlinear output and exhibits
    # dependent intermediate products; this is a gap, not a rewrite proof.
    pair = [("CCX", (0, 1, 2)), ("CCX", (0, 1, 2))]
    r = analyze(pair, 2000)
    assert r["remaining_ccx_gap"] == 2
    assert r["dependent_nonlinear_product_count"] == 1
    print("K138_SELFTEST PASS exact ANF rank and product dependency", flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path,
                   default=Path("competition/k098/results/helios_immutable.kmx"))
    p.add_argument("--out", type=Path,
                   default=Path("competition/k138/results/cross_block_nonlinear_gap.json"))
    p.add_argument("--range", dest="ranges", action="append", default=[],
                   help="1-based inclusive start:end; repeat for multiple regions")
    p.add_argument("--ccx-sizes", default="5,6,8,10,12")
    p.add_argument("--max-span", type=int, default=100)
    p.add_argument("--max-wires", type=int, default=30)
    p.add_argument("--max-monomials", type=int, default=12000)
    p.add_argument("--top", type=int, default=30)
    a = p.parse_args()
    selftest()
    data = a.baseline.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != PIN:
        raise SystemExit("Pinned baseline SHA mismatch: " + sha)
    lines = data.decode().splitlines()
    sizes = sorted({int(x) for x in a.ccx_sizes.split(",")})
    if min(sizes) < 5 or a.max_span < 5 or a.max_wires < 5 or a.top < 1:
        p.error("invalid search bounds")
    intervals = a.ranges or ["21000:25700", "28000:30000"]
    combined, stats = [], collections.Counter()
    for interval in intervals:
        first, last = (int(x) for x in interval.split(":"))
        if not (1 <= first <= last <= len(lines)):
            p.error("range exceeds source")
        matches, counts = screen(lines, first, last, sizes,
                                 a.max_span, a.max_wires, a.max_monomials)
        for row in matches:
            row["scan_interval"] = interval
        combined.extend(matches)
        stats.update(counts)
        print("K138_RANGE", json.dumps({
            "range": interval, "unresolved_windows": len(matches),
            "counts": counts
        }), flush=True)
    combined.sort(key=lambda x: (
        -x["remaining_ccx_gap"],
        -x["dependent_nonlinear_product_count"],
        x["wire_count"], x["length_instructions"]))
    report = {
        "experiment": "K138",
        "status": "READ_ONLY_CROSS_BLOCK_ANALYSIS",
        "baseline_sha256": sha,
        "ranges": intervals, "ccx_sizes": sizes,
        "analysis_counts": dict(stats),
        "unresolved_windows": len(combined),
        "top_windows": combined[:a.top],
        "limitations": [
            "The lower bound is necessary but not sufficient.",
            "A positive gap does not establish an achievable cheaper circuit.",
            "Most windows overlap, so source count estimates must not be added.",
            "This scans pure unconditional X/CX/CCX regions only.",
            "No candidate generated or official verifier run."
        ]
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    for row in report["top_windows"]:
        print("K138_WINDOW", json.dumps(row), flush=True)
    print("K138_RESULT", json.dumps({
        "status": report["status"],
        "analyzed": stats["analyzed"],
        "tight": stats["tight"],
        "unresolved_windows": len(combined),
        "out": str(a.out)
    }), flush=True)

if __name__ == "__main__":
    main()
