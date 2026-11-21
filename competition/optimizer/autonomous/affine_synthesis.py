"""Constrained synthesis of single-target quadratic Boolean oracles."""

from functools import lru_cache
from itertools import combinations
import time

from .arithmetic import oracle_form
from .core import Gate, Proposal, cost


@lru_cache(maxsize=8)
def dictionary(n):
    """Index equivalent products by quadratic spectrum and linear correction."""
    pairs = tuple(combinations(range(n), 2))
    result = {}
    for left, right in combinations(range(1, 1 << n), 2):
        a_only, b_only = left & ~right, right & ~left
        if not a_only or not b_only:
            continue
        spectrum = sum(
            ((((left >> i) & (right >> j)) ^ ((left >> j) & (right >> i))) & 1) << k
            for k, (i, j) in enumerate(pairs)
        )
        # left*right over GF(2) contributes x_i^2 = x_i on overlap.
        key = spectrum, left & right
        rank = left.bit_count() + right.bit_count()
        if key not in result or rank < result[key][0]:
            result[key] = rank, left, right
    return pairs, tuple((spectrum, linear, left, right)
                        for (spectrum, linear), (_, left, right) in sorted(result.items()))


def product(wires, target, left, right):
    a = ((left & ~right) & -(left & ~right)).bit_length() - 1
    b = ((right & ~left) & -(right & ~left)).bit_length() - 1
    basis = [Gate("CX", (q, wires[pivot]))
             for mask, pivot in [(left, a), (right, b)]
             for i, q in enumerate(wires) if i != pivot and (mask >> i) & 1]
    return basis + [Gate("CCX", (*sorted((wires[a], wires[b])), target))] + basis[::-1]


def rank_lower_bound(pairs, spectrum, width):
    """Every parity product contributes a polar matrix of rank at most two."""
    rows = [0] * width
    for k, (i, j) in enumerate(pairs):
        if (spectrum >> k) & 1:
            rows[i] |= 1 << j
            rows[j] |= 1 << i
    basis = {}
    for row in rows:
        while row:
            pivot = row.bit_length()
            if pivot not in basis:
                basis[pivot] = row
                break
            row ^= basis[pivot]
    return (len(basis) + 1) // 2


def constrained_affine(gates, budget, seed):
    """Search increasing numbers of parity products, never gate selectors."""
    if cost(gates)[0] < 2:
        return None
    form = oracle_form(gates)
    if form is None:
        return None
    wires, terms, targets, _ = form
    if targets.bit_count() != 1:
        return None
    target_index = targets.bit_length() - 1
    inputs = [q for i, q in enumerate(wires) if i != target_index]
    if not 2 <= len(inputs) <= 5:
        return None
    try:
        import z3
    except ImportError:
        return Proposal(gates, {"solver_status": "UNAVAILABLE", "reason": "Install optional z3-solver"})

    def old_mask(mask):
        indices = [i for i in range(len(wires)) if i != target_index]
        return sum(1 << index for j, index in enumerate(indices) if (mask >> j) & 1)

    pairs, products = dictionary(len(inputs))
    expected = sum((old_mask((1 << i) | (1 << j)) in terms) << k
                   for k, (i, j) in enumerate(pairs))
    if not expected:
        return None
    linear = sum((old_mask(1 << i) in terms) << i for i in range(len(inputs)))
    target = wires[target_index]
    deadline = time.monotonic() + budget["seconds"]
    minimum = rank_lower_bound(pairs, expected, len(inputs))
    maximum = min(cost(gates)[0] - 1, budget["depth"])
    attempts = []
    if minimum > maximum:
        return Proposal(gates, {"solver_status": "UNSAT", "attempts": attempts,
                                "rank_lower_bound": minimum, "max_products": maximum})
    for count in range(minimum, maximum + 1):
        left = deadline - time.monotonic()
        if left <= 0:
            return Proposal(gates, {"solver_status": "TIMEOUT", "attempts": attempts})
        solver = z3.Solver()
        solver.set(timeout=max(1, int(left * 1000)), rlimit=budget["max_states"] * 10,
                   random_seed=seed & 0x7fffffff)
        use = [z3.Bool(f"product_{i}") for i in range(len(products))]
        # Each product appears at most once. XOR terms have no ordering symmetry.
        solver.add(z3.PbEq([(v, 1) for v in use], count))
        for bit in range(len(pairs)):
            parity = z3.BoolVal(False)
            for variable, (spectrum, _, _, _) in zip(use, products):
                if (spectrum >> bit) & 1:
                    parity = z3.Xor(parity, variable)
            solver.add(parity == bool((expected >> bit) & 1))
        status = solver.check()
        reason = solver.reason_unknown() if status == z3.unknown else None
        label = "TIMEOUT" if reason == "timeout" else str(status).upper()
        attempts.append({"products": count, "status": label, "reason": reason})
        if status == z3.sat:
            model = solver.model()
            candidate = [Gate("X", (target,))] if 0 in terms else []
            for variable, (_, correction, left, right) in zip(use, products):
                if z3.is_true(model.eval(variable)):
                    candidate.extend(product(inputs, target, left, right))
                    linear ^= correction
            candidate.extend(Gate("CX", (wire, target))
                             for i, wire in enumerate(inputs) if (linear >> i) & 1)
            return Proposal(candidate, {"solver_status": "SAT", "attempts": attempts,
                                        "dictionary_size": len(products)})
        if status == z3.unknown:
            return Proposal(gates, {"solver_status": label, "attempts": attempts})
    return Proposal(gates, {"solver_status": "UNSAT", "attempts": attempts,
                            "scope": "bounded quadratic parity-product dictionary"})
