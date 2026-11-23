"""Look for exact nonlinear gate savings across long, free CNOT frames."""

import argparse
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, islice
import json
from pathlib import Path

from ..autonomous.arithmetic import anf
from ..autonomous.core import Gate, cost, sha
from ..autonomous.kickmix_trace import Instruction, load_program, physical_lines

FRAME = {"X", "CX", "SWAP"}
PAID = {"CCX", "CSWAP"}


@dataclass(frozen=True)
class Kernel:
    line: int
    left: int
    right: int
    bias_left: int
    bias_right: int
    delta: int


def reduce_mask(row, basis):
    coordinates = 0
    while row:
        existing = basis.get(row.bit_length())
        if existing is None:
            break
        mask, coordinate = existing
        row ^= mask
        coordinates ^= coordinate
    return row, coordinates


def extend_basis(row, basis):
    remainder, coordinates = reduce_mask(row, basis)
    if remainder:
        added = 1 << len(basis)
        basis[remainder.bit_length()] = remainder, coordinates ^ added
        coordinates = added
    return coordinates


def rank(rows):
    basis = {}
    for row in rows:
        extend_basis(row, basis)
    return len(basis)


def vector_indices(vector):
    while vector:
        bit = vector & -vector
        yield bit.bit_length() - 1
        vector ^= bit


class AffineFrame:
    def __init__(self, wires):
        self.rows = {wire: 1 << i for i, wire in enumerate(wires)}
        self.inverse = self.rows.copy()
        self.bias = dict.fromkeys(wires, 0)

    def apply(self, op):
        rows, inverse, bias = self.rows, self.inverse, self.bias
        if op.opcode == "X":
            bias[op.qubits[0]] ^= 1
        elif op.opcode == "CX":
            control, target = op.qubits
            rows[target] ^= rows[control]
            bias[target] ^= bias[control]
            inverse[control] ^= inverse[target]
        elif op.opcode == "SWAP":
            a, b = op.qubits
            rows[a], rows[b] = rows[b], rows[a]
            bias[a], bias[b] = bias[b], bias[a]
            inverse[a], inverse[b] = inverse[b], inverse[a]
        elif op.opcode == "CCX":
            a, b, target = op.qubits
            return Kernel(op.line, rows[a], rows[b], bias[a], bias[b], inverse[target])
        elif op.opcode == "CSWAP":
            c, a, b = op.qubits
            return Kernel(op.line, rows[c], rows[a] ^ rows[b], bias[c],
                          bias[a] ^ bias[b], inverse[a] ^ inverse[b])
        else:
            raise ValueError(f"Unsupported frame opcode {op.opcode}")
        return None


def sections(program, wires):
    """Conjugate each paid gate by the affine prefix of its uninterrupted section."""
    frame = AffineFrame(wires)
    kernels = []
    dirty = False
    depth = 0
    for op in program:
        if op.opcode == "PUSH_CONDITION":
            depth += 1
        if op.opcode == "POP_CONDITION":
            depth -= 1
            if depth < 0:
                raise ValueError("Unmatched POP_CONDITION")
        if depth or op.guard is not None or op.opcode not in FRAME | PAID:
            if kernels:
                yield kernels
            if kernels or dirty:
                kernels = []
                frame = AffineFrame(wires)
                dirty = False
        else:
            kernel = frame.apply(op)
            dirty = True
            if kernel is not None:
                kernels.append(kernel)
    if depth:
        raise ValueError("Unterminated condition stack")
    if kernels:
        yield kernels


def window_polynomial(kernels):
    """Return the vector ANF and the independent physical parity controls."""
    basis = {}
    controls = []
    coordinate_masks = []
    for kernel in kernels:
        pair = []
        for row in (kernel.left, kernel.right):
            count = len(basis)
            pair.append(extend_basis(row, basis))
            if len(basis) != count:
                coordinate_masks.append(row)
        controls.append(tuple(pair))
    values = []
    for x in range(1 << len(basis)):
        delta = 0
        for kernel, (left, right) in zip(kernels, controls):
            a = ((x & left).bit_count() + (kernel.left & delta).bit_count() + kernel.bias_left) & 1
            b = ((x & right).bit_count() + (kernel.right & delta).bit_count() + kernel.bias_right) & 1
            if a and b:
                delta ^= kernel.delta
        values.append(delta)
    return dict(filter(lambda item: item[1], enumerate(anf(values)))), coordinate_masks


def window_bound(kernels):
    coefficients, coordinates = window_polynomial(kernels)
    outputs = {delta for x, delta in coefficients.items() if x.bit_count() >= 2}
    lower = rank(outputs)
    degree = max(map(int.bit_count, coefficients), default=0)
    if lower == 1 and degree == 2:
        rows = [0] * len(coordinates)
        for pair in coefficients:
            if pair.bit_count() != 2:
                continue
            a, b = pair & -pair, pair ^ (pair & -pair)
            rows[a.bit_length()-1] ^= b
            rows[b.bit_length()-1] ^= a
        lower = rank(rows) // 2
    return lower, degree


def product_spectrum(left, right, pairs):
    """Quadratic part of a product of two parity forms."""
    return sum(((((left >> a) & (right >> b)) ^ ((left >> b) & (right >> a))) & 1) << i
               for i, (a, b) in enumerate(pairs))


def scalar_factors(spectrum, pairs, width):
    """Split an alternating quadratic form into parity products over GF(2)."""
    while spectrum:
        a, b = pairs[(spectrum & -spectrum).bit_length() - 1]
        rows = [0] * width
        for i in vector_indices(spectrum):
            x, y = pairs[i]
            rows[x] ^= 1 << y
            rows[y] ^= 1 << x
        left = rows[b]
        right = rows[a]
        yield left, right
        spectrum ^= product_spectrum(left, right, pairs)


@lru_cache(maxsize=8)
def rank_two_spectra(width):
    pairs = tuple(combinations(range(width), 2))
    return {
        product_spectrum(left, right, pairs): (left, right)
        for left, right in combinations(range(1, 1 << width), 2) if left ^ right > right
    }


def product_bases(output_rows, pairs, width, paid):
    span = {0}
    for row in output_rows:
        span |= {value ^ row for value in span}
    span.remove(0)
    needed = len(span).bit_length()
    if not needed or needed >= paid:
        return
    shapes = {row: list(scalar_factors(row, pairs, width)) for row in sorted(span)}
    simple = [row for row, factors in shapes.items() if len(factors) == 1]
    if rank(simple) == needed:
        for group in combinations(simple, needed):
            if rank(group) == needed:
                yield [shapes[row][0] for row in group]
    if needed < 2 or paid <= needed + 1:
        return
    if len(simple) >= needed - 1:
        for group in combinations(simple, needed - 1):
            if rank(group) != len(group):
                continue
            for other in sorted(span):
                if rank((*group, other)) != needed:
                    continue
                if len(shapes[other]) == 2:
                    yield [*(shapes[row][0] for row in group), *shapes[other]]
    elif needed == 2 and width <= 8:
        a, b, _ = sorted(span)
        products = rank_two_spectra(width)
        for row, product in products.items():
            if row ^ a in products and row ^ b in products:
                yield [product, products[row ^ a], products[row ^ b]]


def affine_network(rows, bias, wires):
    """Emit an invertible binary map by reversing Gaussian row operations."""
    rows = list(rows)
    elimination = []
    for col, wire in enumerate(wires):
        pivot = next((i for i in range(col, len(rows)) if rows[i] >> col & 1), None)
        if pivot is None:
            return None
        if pivot != col:
            rows[col], rows[pivot] = rows[pivot], rows[col]
            elimination.append(Gate("SWAP", (wire, wires[pivot])))
        for i in range(len(rows)):
            if i != col and rows[i] >> col & 1:
                rows[i] ^= rows[col]
                elimination.append(Gate("CX", (wire, wires[i])))
    return list(reversed(elimination)) + [Gate("X", (wires[i],)) for i in vector_indices(bias)]


def transform_vector(rows, vector):
    return sum((((row & vector).bit_count() & 1) << i) for i, row in enumerate(rows))


def parity_mask(coordinates, form):
    mask = 0
    for i in vector_indices(form):
        mask ^= coordinates[i]
    return mask


def transvection(wires, left, right, direction):
    """Realize x -> x + direction * left(x) * right(x) in free affine frames."""
    if not direction:
        return []
    target = next(vector_indices(direction))
    a, b = [i for i in range(len(wires)) if i != target][:2]
    rows = {target: 1 << target, a: left, b: right}
    basis = {}
    for row in rows.values():
        extend_basis(row, basis)
    remaining = (i for i in range(len(wires)) if i not in rows)
    for i in range(len(wires)):
        row = (1 << i) ^ (((direction >> i) & 1) << target)
        count = len(basis)
        extend_basis(row, basis)
        if len(basis) > count:
            rows[next(remaining)] = row
    frame = affine_network([rows[i] for i in range(len(wires))], 0, wires)
    if frame is None:
        raise RuntimeError("Singular transvection frame")
    return frame + [Gate("CCX", (wires[a], wires[b], wires[target]))] + frame[::-1]


def synthesize(terms, coordinates, wires, paid):
    if max(map(int.bit_count, terms), default=0) > 2:
        return None
    pairs = tuple(combinations(range(len(coordinates)), 2))
    quadratic = [terms.get((1 << a) | (1 << b), 0) for a, b in pairs]
    output_rows = [sum(((value >> wire) & 1) << i for i, value in enumerate(quadratic))
                   for wire in range(len(wires))]
    for products in islice(product_bases(output_rows, pairs, len(coordinates), paid), 64):
        basis = {}
        for left, right in products:
            extend_basis(product_spectrum(left, right, pairs), basis)
        directions = [0] * len(products)
        for wire, row in enumerate(output_rows):
            residual, represented = reduce_mask(row, basis)
            if residual:
                raise RuntimeError("Selected products do not cover the quadratic map")
            for i in vector_indices(represented):
                directions[i] ^= 1 << wire
        rows = [1 << i for i in range(len(wires))]
        for i, coord in enumerate(coordinates):
            for wire in vector_indices(terms.get(1 << i, 0)):
                rows[wire] ^= coord
        for (left, right), delta in zip(products, directions):
            for wire in vector_indices(delta):
                rows[wire] ^= parity_mask(coordinates, left & right)
        correction = affine_network(rows, terms.get(0, 0), wires)
        if correction is None:
            continue
        inverse_frame = AffineFrame(wires)
        for gate in correction:
            inverse_frame.apply(_instruction(gate))
        pre_directions = [parity_mask(list(inverse_frame.inverse.values()), v) for v in directions]
        forms = [(parity_mask(coordinates, a), parity_mask(coordinates, b)) for a, b in products]
        if any((control & delta).bit_count() & 1 for form in forms for control in form
               for delta in pre_directions):
            continue
        candidate = []
        for (a, b), delta in zip(forms, pre_directions):
            candidate.extend(transvection(wires, a, b, delta))
        return candidate + correction
    return None


def _instruction(gate):
    return Instruction(0, gate.op, gate.q, None, None)


def normalize(ops, wires):
    frame = AffineFrame(wires)
    kernels = []
    for op in ops:
        kernel = frame.apply(op)
        if kernel is not None:
            kernels.append(kernel)
    return frame, kernels


def signature(ops, wires):
    """Canonical polynomial over all physical inputs, for an unconditional block."""
    frame, kernels = normalize(ops, wires)
    terms, controls = window_polynomial(kernels)
    rows = list(frame.rows.values())
    coefficients = {1 << i: transform_vector(rows, 1 << i) for i in range(len(wires))}
    coefficients[0] = sum(value << i for i, value in enumerate(frame.bias.values()))
    for form, delta in terms.items():
        if form.bit_count() > 2:
            raise ValueError("Only a quadratic block can be certified")
        monomials = [0]
        for i in vector_indices(form):
            monomials = [prefix | (1 << j) for prefix in monomials for j in vector_indices(controls[i])]
        output = transform_vector(rows, delta)
        for term in monomials:
            coefficients[term] = coefficients.get(term, 0) ^ output
    return dict(filter(lambda item: item[1], coefficients.items()))


def replace_window(ops, paid):
    wires = sorted({wire for op in ops for wire in op.qubits})
    _, kernels = normalize(ops, wires)
    if len(kernels) != paid:
        raise ValueError("Paid gate count changed during window extraction")
    terms, coordinates = window_polynomial(kernels)
    result = synthesize(terms, coordinates, wires, paid)
    if result is None:
        return None
    affine = [Gate(op.opcode, op.qubits) for op in ops if op.opcode in FRAME]
    result.extend(affine)
    if cost(result)[0] >= paid:
        return None
    if signature(ops, wires) != signature([_instruction(g) for g in result], wires):
        raise RuntimeError("Emitted affine-frame circuit failed its polynomial certificate")
    return result


def optimize(source, width=6):
    if not 2 <= width <= 6:
        raise ValueError("Window must contain 2 to 6 paid gates")
    text = source.decode("utf-8")
    lines = physical_lines(text)
    program, pinned = load_program(text)
    wires = sorted(pinned | {wire for op in program for wire in op.qubits})
    if len(wires) > 512:
        raise ValueError("Screen supports at most 512 wire IDs")
    blocks = list(sections(program, wires))
    by_line = {op.line: i for i, op in enumerate(program)}
    windows = Counter()
    open_windows = []
    beyond_rank_limit = 0
    replacements = []
    for kernels in blocks:
        for size in range(2, width + 1):
            for i in range(len(kernels) - size + 1):
                window = kernels[i:i+size]
                if rank(mask for gate in window for mask in (gate.left, gate.right)) > 10:
                    beyond_rank_limit += 1
                    continue
                lower, degree = window_bound(window)
                windows[(size, lower)] += 1
                if lower < size:
                    detail = {"paid_gates": size, "lower_bound": lower, "degree": degree,
                              "source_lines": [kernel.line for kernel in window]}
                    open_windows.append(detail)
                    if degree > 2:
                        continue
                    first, last = window[0].line, window[-1].line
                    if any(line.split(None, 1)[0] in {"INFO_TAG", "REGISTER", "APPEND_TO_REGISTER"}
                           for line in lines[first-1:last] if line.strip()):
                        continue
                    ops = program[by_line[first]:by_line[last]+1]
                    result = replace_window(ops, size)
                    if result is not None:
                        saved = size - cost(result)[0]
                        replacements.append((saved, first, last, result))
    chosen = []
    for saved, first, last, result in sorted(replacements, key=lambda option: (-option[0], option[1], option[2])):
        if any(first <= b and last >= a for _, a, b, _ in chosen):
            continue
        chosen.append((saved, first, last, result))
    for _, first, last, result in sorted(chosen, key=lambda option: -option[1]):
        lines[first-1:last] = [gate.text() for gate in result]
    candidate = "".join(lines).encode("utf-8") if chosen else None
    return candidate, {
        "source_sha256": sha(source),
        "sections": len(blocks),
        "paid_gates_in_unconditional_sections": sum(map(len, blocks)),
        "max_paid_gates_per_window": width,
        "max_product_bases_per_window": 64,
        "tested_windows": sum(windows.values()),
        "windows_above_control_rank_limit": beyond_rank_limit,
        "window_counts_by_size_and_rank": [
            {"size": size, "rank": lower, "count": count} for (size, lower), count in sorted(windows.items())
        ],
        "windows_below_full_nonlinear_rank": open_windows,
        "certified_replacements": len(replacements),
        "selected_replacements": [
            {"from_line": first, "to_line": last, "paid_gates_saved": saved} for saved, first, last, _ in chosen
        ],
        "candidate": sha(candidate) if candidate is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--window", type=int, choices=range(2, 7), default=6)
    parser.add_argument("--output", type=Path, help="New path for a certified candidate, if found")
    args = parser.parse_args()
    candidate, report = optimize(args.source.read_bytes(), args.window)
    if candidate is not None and args.output is not None:
        with args.output.open("xb") as stream:
            stream.write(candidate)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
