#!/usr/bin/env python3
"""Matched executable arithmetic comparison and final-postselection cost sweep.

Uses published COMP-N-SUB-I inside OUR wrapper, not the authors' full divider.
No input normalization/solution-count promises from the full paper are assumed.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'optimized_divisor_oracle'))
import baseline as original
import optimized_division as ours
from comparison import published_2026 as published
from qiskit import QuantumCircuit,transpile

BUILDERS={'history_baseline':original.build,'qrr_in_place':ours.build,
          'published_cns_in_our_wrapper':published.build}


def gate_counts(ops):
    return dict(Counter(op[0] for op in ops))


def clifford_t_counts(layout,ops):
    circuit=QuantumCircuit(layout.qubits)
    for name,*bits in ops:
        getattr(circuit,name)(*bits)
    compiled=transpile(circuit,basis_gates=['h','s','sdg','t','tdg','x','cx'],
                       optimization_level=0,seed_transpiler=12345)
    counts=compiled.count_ops()
    return {'T_plus_Tdg':int(counts.get('t',0)+counts.get('tdg',0)),
            'CNOT':int(counts.get('cx',0)),'depth':compiled.depth(),
            'method':'Same Qiskit opt-level-0 exact Clifford+T decomposition; no routing'}


def primitive_validation():
    cases=0
    for k in range(2,6):
        c=original.Circuit();a=c.reg('a',k);b=c.reg('b',k);z=c.reg('z',1)[0]
        ops=published.comp_n_sub_i(a,b,z)
        counts=Counter(op[0] for op in ops)
        assert counts['ccx']==3*k-1 and counts['cx']==4*k-5
        for av in range(1<<k):
            for bv in range(1<<k):
                initial=sum(((av>>i)&1)<<bit for i,bit in enumerate(a))
                initial|=sum(((bv>>i)&1)<<bit for i,bit in enumerate(b))
                out=original.sparse_apply({initial:1+0j},ops)
                basis=next(iter(out))
                assert original.value(basis,a)==av
                assert original.value(basis,b)==(bv-av if bv>=av else bv)
                assert ((basis>>z)&1)==int(bv<av)
                assert original.sparse_apply(out,ops[::-1])=={initial:1+0j}
                cases+=1
    return cases


def divider_validation():
    cases=0
    for n in range(4,128):
        c,division,mark,oracle=published.build(n.bit_length(),3)
        for p in range(8):
            initial=original.loaded_basis(c,n,p)
            computed=original.sparse_apply({initial:1+0j},division+mark)
            basis=next(iter(computed))
            if p:
                # Independent classical arithmetic only in the test harness.
                assert original.value(basis,c.registers['Q'])==n//p
                assert original.value(basis,c.registers['R'])==n%p
            expected=p>=2 and p<n and n%p==0
            assert bool(original.value(basis,c.registers['good']))==expected
            assert original.value(basis,c.registers['mcx_scratch'])==0
            assert original.sparse_apply({initial:1+0j},oracle)=={initial:-1+0j if expected else 1+0j}
            cases+=1
    return cases


def coherent_validation():
    import numpy as np
    rng=np.random.default_rng(260318)
    checked=0
    for m in [2,4,5,6]:
        c,division,mark,oracle=published.build(8,m)
        pairs=list(dict.fromkeys((int(rng.integers(4,256)),int(rng.integers(0,1<<m))) for _ in range(32)))
        amps=rng.normal(size=len(pairs))+1j*rng.normal(size=len(pairs))
        amps/=np.linalg.norm(amps)
        state={original.loaded_basis(c,n,p):amp for (n,p),amp in zip(pairs,amps)}
        expected={original.loaded_basis(c,n,p):amp*(-1 if p>=2 and p<n and n%p==0 else 1)
                  for (n,p),amp in zip(pairs,amps)}
        assert original.sparse_apply(state,oracle)==expected
        assert original.sparse_apply(original.sparse_apply(state,division),division[::-1])==state
        checked+=len(pairs)
    return checked


def resources():
    rows=[]
    for n,m in [(4,2),(6,3),(8,4),(9,5),(12,6),(16,8),(32,16),(64,32)]:
        row={'dividend_bits':n,'divisor_bits':m,'architectures':{}}
        for name,builder in BUILDERS.items():
            c,division,mark,oracle=builder(n,m)
            row['architectures'][name]={
                'logical_qubits':c.qubits,'division_counts':gate_counts(division),
                'oracle_counts':gate_counts(oracle),'oracle_total_gates':len(oracle),
                'oracle_schedule':ours.schedule_cost(oracle),
                'uniform_clifford_t_oracle':clifford_t_counts(c,oracle),
            }
        rows.append(row)
    return rows


def postselection_costs():
    rows=[]
    # Same unamplified state; no target-dependent candidate preparation.
    for n,m in [(35,3),(323,5),(331,5)]:
        initial=original.run(n,m,0,shots=1)['success_history'][0]
        theta=math.asin(math.sqrt(min(1,initial)))
        for architecture,builder in BUILDERS.items():
            c,division,mark,oracle=builder(n.bit_length(),m)
            prep=m+n.bit_count()
            diffuse=original.diffusion(c)
            samples=[]
            for k in range(7):
                probability=math.sin((2*k+1)*theta)**2
                gates=prep+k*(len(oracle)+len(diffuse))+len(division)+len(mark)
                ccx=k*(Counter(op[0] for op in oracle)['ccx']+
                       Counter(op[0] for op in diffuse)['ccx'])
                ccx+=Counter(op[0] for op in division+mark)['ccx']
                samples.append({'rounds':k,'success_probability':probability,
                    'unitary_gates_per_attempt':gates,'ccx_per_attempt':ccx,
                    'attempts_per_success':1/probability if probability>1e-15 else None,
                    'expected_unitary_gates_per_success':gates/probability if probability>1e-15 else None,
                    'expected_ccx_per_success':ccx/probability if probability>1e-15 else None})
            viable=[sample for sample in samples if sample['expected_ccx_per_success'] is not None]
            best=min(viable,key=lambda s:s['expected_ccx_per_success']) if viable else None
            rows.append({'N':n,'candidate_bits':m,'architecture':architecture,
                         'round_sweep':samples,'best_ccx_rounds_retrospective':best['rounds'] if best else None,
                         'selection_note':'Retrospective resource analysis using simulated solution probability; not a blind stopping algorithm',
                         'excluded_costs':['classical control','wall time','measurement duration','error correction','routing']})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'results'/'published_comparison.json')
    parser.add_argument('--selftest-only',action='store_true')
    args=parser.parse_args()
    start=time.perf_counter()
    report={'validation':{'status':'PASS','published_primitive_basis_cases':primitive_validation(),
                         'published_adapter_N_P_cases':divider_validation(),
                         'random_coherent_basis_terms':coherent_validation()},
            'reference':'https://arxiv.org/pdf/2603.18110v2',
            'reference_section':'2.2.1, COMP-N-SUB-I steps 1-8, printed p.11',
            'scope':'Executable primitive adaptation in common wrapper, not full authors divider',
            'full_paper_layout_or_T_pair_optimization_implemented':False}
    if not args.selftest_only:
        report['resource_grid']=resources()
        report['final_postselection_cost_sweep']=postselection_costs()
    report['wall_seconds']=time.perf_counter()-start
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'validation':report['validation'],'wall_seconds':report['wall_seconds'],
                      'resource_shapes':len(report.get('resource_grid',[])),
                      'output':str(args.output)},indent=2))


if __name__=='__main__':
    main()
