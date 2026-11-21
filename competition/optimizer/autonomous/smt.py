"""Optional Z3 bit-parallel exact synthesis for <=4 arbitrary dirty wires."""
import itertools
import time
from .core import Gate, Proposal, cost, signature


def synthesize(gates,budget,seed):
    wires=sorted({q for g in gates for q in g.q})
    if len(wires)>4 or cost(gates)[0]==0 or any(g.op not in {'X','CX','CCX','SWAP','CSWAP'} for g in gates):
        return None
    try: import z3
    except ImportError:
        return Proposal(gates,{'solver_status':'UNAVAILABLE','reason':'Install optional z3-solver'})
    alphabet=[None]+[Gate('X',(q,)) for q in wires]
    alphabet += [Gate('CX',q) for q in itertools.permutations(wires,2)]
    alphabet += [Gate('CCX',tuple(c)+(t,)) for t in wires for c in itertools.combinations([q for q in wires if q!=t],2)]
    n=len(wires);bits=1<<n;index={q:i for i,q in enumerate(wires)}
    initial=[sum(((v>>i)&1)<<v for v in range(bits)) for i in range(n)]
    target=signature(gates,wires)
    outputs=[sum(((v>>i)&1)<<j for j,(v,p) in enumerate(target)) for i in range(n)]
    deadline=time.monotonic()+budget['seconds'];attempts=[]
    for length in range(1,min(16,budget['depth'])+1):
        remaining=deadline-time.monotonic()
        if remaining<=0: break
        solver=z3.Solver();solver.set(timeout=max(1,int(remaining*1000)),random_seed=seed & 0x7fffffff,
                                     rlimit=budget['max_states']*10)
        selectors=[z3.Int(f'g{k}') for k in range(length)]
        state=[z3.BitVecVal(v,bits) for v in initial]
        counts=[]
        for k,selector in enumerate(selectors):
            solver.add(selector>=0,selector<len(alphabet))
            next_state=[]
            for i in range(n):
                value=state[i]
                for j,g in enumerate(alphabet[1:],1):
                    q=[index[x] for x in g.q]
                    if i!=q[-1]: continue
                    control=z3.BitVecVal((1<<bits)-1,bits)
                    for c in q[:-1]: control=control & state[c]
                    value=z3.If(selector==j,state[i]^control,value)
                output=z3.BitVec(f's{k}_{i}',bits)
                solver.add(output==value);next_state.append(output)
            counts.append(z3.If(z3.Or([selector==j for j,g in enumerate(alphabet) if g and g.op=='CCX']),1,0))
            state=next_state
        solver.add(z3.Sum(counts)<cost(gates)[0])
        solver.add(*[s==t for s,t in zip(state,outputs)])
        status=solver.check();attempts.append({'slots':length,'status':str(status),'reason_unknown':solver.reason_unknown() if status==z3.unknown else None})
        if status==z3.sat:
            model=solver.model();candidate=[alphabet[model[x].as_long()] for x in selectors]
            candidate=[g for g in candidate if g is not None]
            return Proposal(candidate,{'solver':'Z3','version':z3.get_version_string(),
                'attempts':attempts,'proof':'Independent exhaustive truth table required',
                'optimality_claim':False})
        if status==z3.unknown: break
    return Proposal(gates,{'solver':'Z3','attempts':attempts,'optimality_claim':False,
                          'reason':'Bounded synthesis only; unknown/timeouts prove no optimality'})
