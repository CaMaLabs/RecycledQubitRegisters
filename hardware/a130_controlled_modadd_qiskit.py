#!/usr/bin/env python3
"""A130: exact controlled modular-add constant search on 3-bit register.

Compare repeated controlled +/-1 vs binary power-of-two decompositions
for c-ADD(k) modulo 8. Verify every 4-qubit unitary against a 16x16
permutation up to *one global phase* (not independently per input).
Qiskit CX/depth and logical high-controlled gate counts are reported
separately; neither is the Kickmix weighted score.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

N=3
CONTROL=3
WIDTH=4
D=1<<WIDTH

def controlled_increment(qc,direction,shift=0):
    """Conditional add/subtract 2**shift modulo 8, high-bit-first ripple."""
    assert direction in (-1,1)
    operations=[]
    for j in range(N-1,shift-1,-1):
        controls=[CONTROL]+list(range(shift,j))
        operations.append((controls,j))
    if direction<0:operations.reverse()
    for controls,target in operations:
        if len(controls)==1:qc.cx(controls[0],target)
        elif len(controls)==2:qc.ccx(*controls,target)
        else:qc.mcx(controls,target)

def build(k,method):
    from qiskit import QuantumCircuit
    qc=QuantumCircuit(WIDTH)
    if method=='repeat_forward':
        for _ in range(k):controlled_increment(qc,1)
    elif method=='repeat_backward':
        for _ in range((8-k)%8):controlled_increment(qc,-1)
    elif method=='binary_forward':
        for shift in range(N-1,-1,-1):
            if (k>>shift)&1:controlled_increment(qc,1,shift)
    elif method=='binary_backward':
        m=(-k)%8
        for shift in range(N-1,-1,-1):
            if (m>>shift)&1:controlled_increment(qc,-1,shift)
    else:raise ValueError(method)
    return qc

def oracle(k):
    u=np.zeros((D,D),complex)
    for x in range(D):
        control=(x>>CONTROL)&1
        y=x&7
        dest=(control<<CONTROL)|((y+k*control)%8)
        u[dest,x]=1
    return u

def phase_error(actual,expected):
    overlap=np.vdot(expected,actual)
    phase=np.exp(1j*np.angle(overlap))
    return float(np.max(np.abs(actual-phase*expected)))

def metrics(qc):
    counts={str(k):int(v) for k,v in qc.count_ops().items()}
    return {'depth':qc.depth(),'size':qc.size(),'cx':counts.get('cx',0),
        'ccx':counts.get('ccx',0),'mcx':sum(v for k,v in counts.items() if k.startswith('mcx')),
        'counts':counts}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--constants',type=int,nargs='+',default=[1,2,3,4,5,6,7])
    p.add_argument('--levels',type=int,nargs='+',default=[1,3])
    p.add_argument('--seed',type=int,default=130)
    p.add_argument('--out',type=Path,default=Path('results/a130_controlled_modadd_qubit.json'))
    a=p.parse_args()
    from qiskit import transpile
    from qiskit.quantum_info import Operator
    methods=['repeat_forward','repeat_backward','binary_forward','binary_backward']
    rows=[]
    for k in a.constants:
        if not 1<=k<=7:p.error('constants must be integers from 1 to 7')
        target=oracle(k)
        for method in methods:
            logical=build(k,method)
            exact_error=phase_error(Operator(logical).data,target)
            if exact_error>1e-10:raise AssertionError(f'Logical circuit FAIL k={k} method={method}: {exact_error}')
            logical_metric=metrics(logical)
            for architecture,coupling in [('all_to_all',None),
               ('linear',[[i,i+1] for i in range(WIDTH-1)]+[[i+1,i] for i in range(WIDTH-1)])]:
                for level in a.levels:
                    compiled=transpile(logical,optimization_level=level,
                        basis_gates=['rz','sx','x','cx'],
                        coupling_map=coupling,initial_layout=list(range(WIDTH)),
                        seed_transpiler=a.seed)
                    layout=list(compiled.layout.final_index_layout(filter_ancillas=True))
                    perm=np.zeros((D,D),complex)
                    for old in range(D):
                        new=sum(((old>>i)&1)<<phys for i,phys in enumerate(layout))
                        perm[new,old]=1
                    err=phase_error(perm.conj().T@Operator(compiled).data,target)
                    row={'k':k,'method':method,'architecture':architecture,
                        'optimization_level':level,'exact_error':exact_error,
                        'transpiled_error':err,'logical_gates':logical_metric,
                        'compiled':metrics(compiled),'final_layout':layout}
                    rows.append(row)
                    if err>1e-10:raise AssertionError(f'Transpile FAIL {row}')
            print('A130_K',json.dumps({'k':k,'method':method,
                'logical':{q:logical_metric[q] for q in ('cx','ccx','mcx','depth')},
                'all_to_all_lvl3_cx':next((r['compiled']['cx'] for r in rows
                    if r['k']==k and r['method']==method and r['architecture']=='all_to_all'
                    and r['optimization_level']==3),None)}),flush=True)
    winners=[]
    for k in a.constants:
        for arch in ('all_to_all','linear'):
            for level in a.levels:
                group=[r for r in rows if r['k']==k and r['architecture']==arch and r['optimization_level']==level]
                best=min(group,key=lambda r:(r['compiled']['cx'],r['compiled']['depth'],r['compiled']['size']))
                winners.append({'k':k,'architecture':arch,'optimization_level':level,
                    'method':best['method'],'cx':best['compiled']['cx'],'depth':best['compiled']['depth'],
                    'final_layout':best['final_layout']})
    result={'status':'PASS_CONTROLLED_MODADD_EXACT','constants':a.constants,
        'records':rows,'winners':winners,
        'caveats':[
          '4 qubits represent a 3-bit target and one control; no native qudit hardware tested.',
          'Qiskit CX/depth is not the Kaggle weighted cost; no leaderboard claim.',
          'Final layout permutations are logically tracked, but restoration routing not priced.',
          'For Kaggle transfer, an exact candidate rewrite and official full verifier are required.'
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    for r in winners:print('A130_WINNER',json.dumps(r),flush=True)
    print('A130_RESULT',json.dumps({'status':result['status'],'comparisons':len(rows),'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
