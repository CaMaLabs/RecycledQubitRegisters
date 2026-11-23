#!/usr/bin/env python3
"""Research screen for sharing parity products across quadratic XOR outputs."""

import argparse
import hashlib
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from ..autonomous.affine_synthesis import dictionary, product
from ..autonomous.arithmetic import emit_terms, oracle_form, selected
from ..autonomous.controller import regions
from ..autonomous.core import Gate, cost, prove


def reduce_vector(vector, basis):
    coordinates = 0
    while vector and vector.bit_length() in basis:
        row, coordinate = basis[vector.bit_length()]
        vector ^= row
        coordinates ^= coordinate
    return vector, coordinates


@lru_cache(maxsize=4)
def simplest_products(width):
    pairs, products = dictionary(width)
    choices = {}
    for spectrum, correction, left, right in sorted(
        products, key=lambda item: (item[2].bit_count() + item[3].bit_count(), item)
    ):
        choices.setdefault(spectrum, (correction, left, right))
    return pairs, choices


def resynthesize(form, priced_before):
    """Emit a rank-attaining parity-product basis when one exists in the span."""
    wires, terms, modified, _ = form
    outputs = selected(wires, modified)
    inputs = selected(wires, ((1 << len(wires)) - 1) ^ modified)
    if len(outputs) < 2 or not 2 <= len(inputs) <= 5:
        return None
    wire_index = {wire: 1 << i for i, wire in enumerate(wires)}
    pairs, choices = simplest_products(len(inputs))
    pair_masks = [wire_index[inputs[a]] | wire_index[inputs[b]] for a, b in pairs]
    rows = {
        out: sum((1 << i) for i, pair in enumerate(pair_masks)
                 if terms.get(pair, 0) & wire_index[out])
        for out in outputs
    }
    span = {0}
    for row in rows.values():
        span |= {value ^ row for value in span}
    rank = len(span).bit_length() - 1
    if not rank or rank >= min(priced_before, sum(mask.bit_count() == 2 for mask in terms)):
        return None

    basis = {}
    factors = []
    for row in sorted(span.intersection(choices)):
        remainder, coordinates = reduce_vector(row, basis)
        if not remainder:
            continue
        basis[remainder.bit_length()] = (remainder, coordinates ^ (1 << len(factors)))
        factors.append(choices[row])
    if len(factors) != rank:
        return None

    recipients = defaultdict(list)
    affine = {mask: value for mask, value in terms.items() if mask.bit_count() < 2}
    for out, row in rows.items():
        _, coordinates = reduce_vector(row, basis)
        for index, (linear, _, _) in enumerate(factors):
            if (coordinates >> index) & 1:
                recipients[index].append(out)
                for wire in selected(inputs, linear):
                    mask = wire_index[wire]
                    affine[mask] = affine.get(mask, 0) ^ wire_index[out]

    result = emit_terms(wires, {mask: value for mask, value in affine.items() if value})
    for index, (_, left, right) in enumerate(factors):
        pivot, *others = recipients[index]
        spread = [Gate("CX", (pivot, target)) for target in others]
        result.extend(spread + product(inputs, pivot, left, right) + spread[::-1])
    return result


def scan(source, max_regions, span):
    raw = source.read_bytes()
    lines = [line.split("#", 1)[0] for line in raw.decode("utf-8").splitlines()]
    windows = regions(lines, {"span": span, "wires": 8}, "arithmetic", max_regions)
    findings = []
    multi_output_oracles = 0
    for start, end, gates, _ in windows:
        form = oracle_form(gates)
        if form is None or form[2].bit_count() < 2:
            continue
        multi_output_oracles += 1
        replacement = resynthesize(form, cost(gates)[0])
        if replacement is None:
            continue
        proof = prove(gates, replacement)
        if proof["status"] != "EXACT":
            raise RuntimeError(f"Quadratic span proof failed on lines {start+1}–{end}")
        findings.append({"first_line": start + 1, "last_line": end,
                         "before": cost(gates), "after": cost(replacement), "proof": proof})
    return {"source_sha256": hashlib.sha256(raw).hexdigest(), "span": span,
            "max_regions": max_regions, "regions_tested": len(windows),
            "multi_output_oracles": multi_output_oracles,
            "exact_local_findings": findings, "officially_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--max-regions", type=int, default=2000, choices=range(1, 5001),
                        metavar="1..5000")
    parser.add_argument("--span", type=int, default=32, choices=range(3, 129), metavar="3..128")
    args = parser.parse_args()
    print(json.dumps(scan(args.source, args.max_regions, args.span), indent=2))


if __name__ == "__main__":
    main()
