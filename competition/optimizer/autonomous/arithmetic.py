"""Exact Boolean arithmetic resynthesis using shared nonlinear terms."""

from .core import Gate, Proposal, REV, cost, signature

ARITHMETIC_OPS = {"X", "CX", "CCX", "SWAP", "CSWAP"}


def anf(table):
    """Vector-valued Möbius transform over GF(2)."""
    coefficients = list(table)
    for bit in range((len(table) - 1).bit_length()):
        for mask in range(len(table)):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    return coefficients


def oracle_form(gates):
    """Recognize y ^= f(x), including helper wires that are restored."""
    wires = sorted({wire for gate in gates for wire in gate.q})
    if len(wires) > 8 or any(gate.op not in REV for gate in gates):
        return None
    table = tuple(x ^ y for x, (y, _) in enumerate(signature(gates, wires)))
    terms = {mask: out for mask, out in enumerate(anf(table)) if out}
    modified = 0
    for out in terms.values():
        modified |= out
    # No target of the oracle may control another operation in its ANF.
    if any(mask & modified or mask.bit_count() > 2 for mask in terms):
        return None
    return wires, terms, modified, table


def selected(wires, mask):
    return [wire for i, wire in enumerate(wires) if (mask >> i) & 1]


def emit_terms(wires, terms, share=True):
    result = []
    for mask, target in sorted(terms.items()):
        controls = selected(wires, mask)
        targets = selected(wires, target)
        if len(controls) == 0:
            result.extend(Gate("X", (t,)) for t in targets)
        elif len(controls) == 1:
            result.extend(Gate("CX", (*controls, t)) for t in targets)
        elif len(controls) == 2 and share:
            pivot, *others = targets
            compute = [Gate("CX", (pivot, t)) for t in others]
            result.extend(compute + [Gate("CCX", (*controls, pivot))] + compute[::-1])
        elif len(controls) == 2:
            result.extend(Gate("CCX", (*controls, t)) for t in targets)
        else:
            raise ValueError("Oracle degree exceeds two")
    return result


def classify(wires, terms, modified, table):
    """Report only arithmetic families that match a full observed truth table.

    Layouts are small and inferred from sorted wire indices, in little-endian
    order. A fixed-point scale cannot be inferred from circuit dynamics.
    """
    outputs = [i for i in range(len(wires)) if (modified >> i) & 1]
    inputs_mask = 0
    for mask in terms:
        inputs_mask |= mask
    inputs = [i for i in range(len(wires)) if (inputs_mask >> i) & 1]
    if len(inputs) == 3 and len(outputs) == 1:
        if all(bool(table[x]) == (sum((x >> i) & 1 for i in inputs) >= 2)
               for x in range(len(table))):
            return "full_adder_carry"
    if len(inputs) and len(inputs) % 2 == 0 and outputs:
        size = len(inputs) // 2
        mask = (1 << len(outputs)) - 1

        def word(x, layout):
            return sum(((x >> i) & 1) << j for j, i in enumerate(layout))

        for name, fn in (("add_mod_power_of_two", lambda a, b: a+b),
                         ("subtract_mod_power_of_two", lambda a, b: a-b),
                         ("multiply_low_word", lambda a, b: a*b),
                         ("unsigned_less_than", lambda a, b: int(a < b))):
            if all(word(y, outputs) == fn(word(x, inputs[:size]), word(x, inputs[size:])) & mask
                   for x, y in enumerate(table)):
                return name
    return "quadratic_xor_oracle"


def two_bit_ripple(gates):
    """Detect in-place two-bit word addition and subtraction on either operand."""
    wires = sorted({wire for gate in gates for wire in gate.q})
    if len(wires) != 4 or any(gate.op not in REV for gate in gates):
        return None
    observed = signature(gates, wires)
    for inputs, outputs in ((wires[:2], wires[2:]), (wires[2:], wires[:2])):
        a0, a1 = inputs
        b0, b1 = outputs
        add = [Gate("CCX", (*sorted((a0, b0)), b1)), Gate("CX", (a1, b1)),
               Gate("CX", (a0, b0))]
        for family, candidate in (("in_place_add_2", add), ("in_place_subtract_2", add[::-1])):
            if cost(candidate) < cost(gates) and signature(candidate, wires) == observed:
                return Proposal(candidate, {"arithmetic_family": family,
                                            "architecture": "no_ancilla_ripple"})
    return None


def arithmetic_resynthesis(gates, budget, seed):
    """Try shared ANF and the factored majority architecture for a carry bit."""
    ripple = two_bit_ripple(gates)
    form = oracle_form(gates)
    if form is None:
        return ripple
    wires, terms, targets, table = form
    family = classify(wires, terms, targets, table)
    options = [("shared_anf", emit_terms(wires, terms)),
               ("direct_anf", emit_terms(wires, terms, share=False))]
    if family == "full_adder_carry":
        a, b, c = sorted({wire for mask in terms for wire in selected(wires, mask)})
        target, = selected(wires, targets)
        change_basis = [Gate("CX", (a, b)), Gate("CX", (a, c))]
        options.append(("majority_affine_sandwich", change_basis +
                        [Gate("CCX", (b, c, target)), Gate("CX", (a, target))] +
                        change_basis[::-1]))
    architecture, best = min(options, key=lambda item: cost(item[1]))
    if ripple and cost(ripple.gates) < cost(best):
        return ripple
    if cost(best) < cost(gates):
        return Proposal(best, {"arithmetic_family": family, "architecture": architecture,
                               "dirty_wire_contract": "arbitrary"})
    return None


def recycle_workspace(gates, budget, seed):
    """Replace fanout compute/use/uncompute with one shared nonlinear term.

    The original helper value still reaches every target. Intervening gates
    may move only if their entire wire support is disjoint from the gadget.
    """
    for start, compute in enumerate(gates[:-2]):
        if compute.op != "CCX":
            continue
        a, b, helper = compute.q
        fanout = []
        disjoint = []
        for end in range(start + 1, len(gates)):
            gate = gates[end]
            if gate == compute:
                break
            if gate.op == "CX" and gate.q[0] == helper and gate.q[1] not in (a, b):
                fanout.append(gate)
            else:
                disjoint.append(gate)
        else:
            continue
        if not fanout:
            continue
        targets = {g.q[1] for g in fanout}
        support = {a, b, helper} | targets
        if any(support.intersection(g.q) for g in disjoint):
            continue
        odd_targets = sorted(t for t in targets if sum(g.q[1] == t for g in fanout) % 2)
        replacement = [Gate("CX", (helper, q)) for q in odd_targets]
        if odd_targets:
            pivot, *others = odd_targets
            spread = [Gate("CX", (pivot, q)) for q in others]
            replacement.extend(spread + [Gate("CCX", (a, b, pivot))] + spread[::-1])
        candidate = gates[:start] + disjoint + replacement + gates[end+1:]
        return Proposal(candidate, {"architecture": "dirty_workspace_uncompute_elision",
                                    "workspace": helper, "fanout": len(odd_targets),
                                    "clean_ancilla_required": False})
    return None
