"""Fail-closed KMX subset and exact reversible/diagonal semantics.

Unsupported operations, inline conditions, and classical control are barriers.
Truth signatures compare every basis state including dirty ancillary wires.
Z_POW semantics are deliberately unsupported until the local official API is read.
"""
from dataclasses import dataclass
import hashlib
import json
from collections import Counter

ARITY = {'X': 1, 'CX': 2, 'CCX': 3, 'SWAP': 2, 'CSWAP': 3,
         'Z': 1, 'CZ': 2, 'CCZ': 3, 'S': 1, 'S_DAG': 1, 'T': 1, 'T_DAG': 1}
REV = {'X', 'CX', 'CCX', 'SWAP', 'CSWAP'}
DIAG = set(ARITY) - REV
PHASE = {'Z': 4, 'CZ': 4, 'CCZ': 4, 'S': 2, 'S_DAG': -2, 'T': 1, 'T_DAG': -1}
SCORED = {'CCX', 'CCZ', 'CSWAP'}

@dataclass(frozen=True)
class Gate:
    op: str
    q: tuple

    def text(self):
        return self.op + ' ' + ' '.join(f'q{x}' for x in self.q) + '\n'


def parse(line):
    tokens = line.split()
    if not tokens or tokens[0] not in ARITY or len(tokens) != ARITY[tokens[0]] + 1:
        return None
    if any(not q.startswith('q') or not q[1:].isascii() or not q[1:].isdigit() for q in tokens[1:]):
        return None
    q = tuple(int(x[1:]) for x in tokens[1:])
    if len(set(q)) != len(q):
        return None
    op = tokens[0]
    if op in {'CCX', 'CZ', 'CCZ', 'SWAP'}:
        q = tuple(sorted(q)) if op != 'CCX' else tuple(sorted(q[:2])) + q[2:]
    if op == 'CSWAP':
        q = q[:1] + tuple(sorted(q[1:]))
    return Gate(op, q)


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def signature(gates, wires):
    if len(wires) > 10:
        raise ValueError('exact table width exceeds 10')
    index = {q: i for i, q in enumerate(wires)}
    result = []
    for v in range(1 << len(wires)):
        phase = 0
        for gate in gates:
            q = [index[x] for x in gate.q]
            bits = [(v >> x) & 1 for x in q]
            if gate.op == 'X':
                v ^= 1 << q[0]
            elif gate.op == 'CX':
                v ^= bits[0] << q[1]
            elif gate.op == 'CCX':
                v ^= (bits[0] & bits[1]) << q[2]
            elif gate.op in {'SWAP', 'CSWAP'}:
                if gate.op == 'SWAP' or bits[0]:
                    if bits[-1] != bits[-2]:
                        v ^= (1 << q[-1]) | (1 << q[-2])
            elif gate.op in PHASE:
                if all(bits):
                    phase += PHASE[gate.op]
            else:
                raise ValueError('unsupported proof operation: ' + gate.op)
        result.append((v, phase % 8))
    return tuple(result)


def prove(before, after, max_wires=10):
    wires = sorted({q for g in before + after for q in g.q})
    if len(wires) > max_wires:
        return {'status': 'UNPROVED_WIDTH_LIMIT', 'wires': len(wires)}
    equivalent = signature(before, wires) == signature(after, wires)
    return {'status': 'EXACT' if equivalent else 'REJECTED', 'wires': len(wires),
            'basis_states': 1 << len(wires), 'phase_modulus': 8,
            'reference': sha(json.dumps(signature(before, wires)))}


def canonical(gates):
    mapping = {}
    normalized = []
    for g in gates:
        for q in g.q:
            mapping.setdefault(q, len(mapping))
        normalized.append((g.op, tuple(mapping[q] for q in g.q)))
    return sha(json.dumps(normalized))


def cost(gates):
    c = Counter(g.op for g in gates)
    # Ranking proxy only. No claim of an official score estimate.
    return (sum(c[x] for x in SCORED), c['T'] + c['T_DAG'], len(gates))


def census(lines):
    c = Counter(line.split()[0] for line in lines if line.split())
    return {'source_opcodes': dict(c), 'syntactically_unguarded_subset': dict(Counter(
        g.op for line in lines if (g := parse(line)) is not None)),
        'official_score': None, 'executed_toffoli': None, 'reaction_depth': None,
        'reason': 'Static counts cannot determine conditional execution or rotation synthesis precision.'}


def commute(a, b):
    if a is None or b is None:
        return False
    if set(a.q).isdisjoint(b.q):
        return True
    if a.op in DIAG and b.op in DIAG:
        return True
    if a.op in {'X', 'CX', 'CCX'} and b.op in {'X', 'CX', 'CCX'}:
        return a.q[-1] not in b.q[:-1] and b.q[-1] not in a.q[:-1]
    return False


@dataclass
class Proposal:
    gates: list
    detail: dict
