"""Small plugin interface: run(gates, budget, seed) -> Proposal or None."""
import itertools
import random
import time
from .core import Gate, Proposal, REV, cost, commute, signature
from .vendor import k099


def cancellation(gates, budget, seed):
    # Reuse K099's known implementation for the supported intersection.
    lines = [g.text() for g in gates]
    out, events, _ = k099.cancel(lines, min(budget['span'], 128))
    from .core import parse
    candidate = [parse(x) for x in out]
    if any(g is None for g in candidate):
        raise ValueError('vendor emitted unsupported syntax')
    if cost(candidate) < cost(gates):
        return Proposal(candidate, {'pairs': events, 'implementation': 'K099'})
    # K099 does not canonicalize CSWAP/symmetric controls; handle CSWAP explicitly.
    for i, g in enumerate(gates):
        if g.op != 'CSWAP':
            continue
        for j in range(i+1, len(gates)):
            if gates[j] == g:
                return Proposal(gates[:i]+gates[i+1:j]+gates[j+1:], {'identity': 'CSWAP involution'})
            if not commute(g, gates[j]):
                break
    return None


def factor(gates, budget, seed):
    """ab XOR ac = a(b XOR c); full-table proof guards all intervening effects."""
    for i, g in enumerate(gates):
        if g.op != 'CCX':
            continue
        for j in range(i+1, len(gates)):
            h = gates[j]
            if h.op != 'CCX' or g.q[-1] != h.q[-1]:
                continue
            shared = set(g.q[:2]) & set(h.q[:2])
            if len(shared) != 1:
                continue
            a = next(iter(shared))
            b = next(iter(set(g.q[:2])-shared))
            c = next(iter(set(h.q[:2])-shared))
            # Only move h across an explicitly commuting interval.
            if not all(commute(h, x) for x in gates[i+1:j]):
                continue
            rep = [Gate('CX', (b,c)), Gate('CCX', tuple(sorted((a,c)))+(g.q[2],)), Gate('CX',(b,c))]
            return Proposal(gates[:i]+rep+gates[i+1:j]+gates[j+1:], {'identity': 'shared-control XOR factor'})
    return None


def affine(gates, budget, seed):
    """GF(2) Gaussian elimination; only unconditional X/CX/SWAP regions."""
    if any(g.op not in {'X', 'CX', 'SWAP'} for g in gates):
        return None
    wires = sorted({q for g in gates for q in g.q})
    index = {q:i for i,q in enumerate(wires)}
    rows = [1 << i for i in range(len(wires))]
    bias = [0] * len(wires)
    for g in gates:
        q = [index[x] for x in g.q]
        if g.op == 'X': bias[q[0]] ^= 1
        elif g.op == 'CX':
            rows[q[1]] ^= rows[q[0]]; bias[q[1]] ^= bias[q[0]]
        else:
            rows[q[0]], rows[q[1]] = rows[q[1]], rows[q[0]]
            bias[q[0]], bias[q[1]] = bias[q[1]], bias[q[0]]
    elimination = []
    for col in range(len(wires)):
        pivot = next(j for j in range(col,len(wires)) if (rows[j]>>col)&1)
        if pivot != col:
            rows[pivot], rows[col] = rows[col], rows[pivot]
            elimination.append(Gate('SWAP',(wires[col],wires[pivot])))
        for row in range(len(wires)):
            if row != col and (rows[row]>>col)&1:
                rows[row] ^= rows[col]
                elimination.append(Gate('CX',(wires[col],wires[row])))
    candidate = list(reversed(elimination)) + [Gate('X',(wires[i],)) for i,x in enumerate(bias) if x]
    if cost(candidate) < cost(gates):
        return Proposal(candidate, {'identity': 'GF2 affine matrix resynthesis'})
    return None


def mitm(gates, budget, seed):
    """Bounded bidirectional permutation search, including inequivalent intermediates.

    Stores at most max_states total states; never claims optimality on timeout/cap.
    Restricted to <=3 wires to keep permutation objects bounded.
    """
    wires = sorted({q for g in gates for q in g.q})
    if len(wires)>3 or any(g.op not in REV for g in gates):
        return None
    n = len(wires)
    alphabet = [Gate('X',(q,)) for q in wires]
    alphabet += [Gate('CX',q) for q in itertools.permutations(wires,2)]
    alphabet += [Gate('CCX',tuple(sorted(set(wires)-{t}))+(t,)) for t in wires] if n==3 else []
    rng = random.Random(seed); rng.shuffle(alphabet)
    identity = tuple(range(1<<n))
    target = tuple(x for x,p in signature(gates,wires))
    permutations = [(g,tuple(x for x,p in signature([g],wires))) for g in alphabet]
    forward = {identity: ()}; backward = {target: ()}
    fronts = [forward.copy(), backward.copy()]
    tables = [forward, backward]
    deadline = time.monotonic()+budget['seconds']
    best = None
    for level in range(budget['depth']):
        side = level % 2
        nxt = {}
        for state, path in fronts[side].items():
            for gate, perm in permutations:
                if time.monotonic()>deadline or sum(map(len,tables))>=budget['max_states']:
                    return best
                new = tuple(perm[x] for x in state)
                newpath = path+(gate,)
                if new in tables[1-side]:
                    other = tables[1-side][new]
                    candidate = list(newpath)+list(reversed(other)) if side==0 else list(other)+list(reversed(newpath))
                    if cost(candidate)<cost(gates) and (best is None or cost(candidate)<cost(best.gates)):
                        best = Proposal(candidate, {'search': 'bidirectional', 'levels': level+1,
                            'states': sum(map(len,tables)), 'optimality_claim': False})
                # Keep a cheaper path to each function, not merely the shortest path.
                previous = tables[side].get(new)
                if previous is None or cost(newpath)<cost(previous):
                    tables[side][new]=newpath; nxt[new]=newpath
        fronts[side]=nxt
        if not nxt:
            break
    return best


def stochastic(gates, budget, seed):
    """Random algebraic rewriting: all moves are independently exact.

    Random ordering/neutral commutation exposes new adjacent patterns; does not
    claim an unrestricted circuit-space annealer or legacy beam functionality.
    """
    rng = random.Random(seed)
    state = list(gates)
    best = list(gates)
    deadline = time.monotonic()+budget['seconds']
    for step in range(budget['max_states']):
        if time.monotonic()>=deadline:
            break
        if len(state)>1:
            i=rng.randrange(len(state)-1)
            if commute(state[i],state[i+1]): state[i],state[i+1]=state[i+1],state[i]
        proposal = (factor if step%2 else cancellation)(state,budget,seed+step)
        if proposal:
            state=proposal.gates
            if cost(state)<cost(best): best=list(state)
        if len(best)==0:
            break
    if cost(best)<cost(gates):
        return Proposal(best, {'search': 'random exact rewrite walk', 'steps': step+1})
    return None


from .smt import synthesize as smt
from .structured import identity_screen, parity_spectrum
from .arithmetic import arithmetic_resynthesis, recycle_workspace
from .phase_precision import phase_function, phase_predicate
from .affine_synthesis import constrained_affine

from .predicate_sharing import predicate_share
from .conditional import conditional_phase

PLUGINS = {
    "predicate_share": predicate_share,
    "conditional_phase": conditional_phase,
    'arithmetic': arithmetic_resynthesis, 'workspace_reuse': recycle_workspace,
    'phase_function': phase_function, 'phase_predicate': phase_predicate, 'affine_smt': constrained_affine,
    'identity_screen': identity_screen, 'parity_spectrum': parity_spectrum, 'smt':smt, 'cancel': cancellation, 'affine': affine, 'factor': factor,
           'mitm': mitm, 'stochastic': stochastic}
