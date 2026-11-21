#!/usr/bin/env python3
"""History-free reversible division; exact phase oracle and final postselection.

The compiler takes ONLY widths. No factors or divisibility table are inputs.
Uses in-place MAJ/UMA arithmetic and restores the remainder on underflow.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np
import baseline as ref


def majority(a,b,c):
    return [('cx',a,b),('cx',a,c),('ccx',c,b,a)]


def unmajority_add(a,b,c):
    return [('ccx',c,b,a),('cx',a,c),('cx',c,b)]


def add_padded(a,b,carry):
    """|a,b,0> -> |a,(b+a) mod 2**len(b),0>, len(b)=len(a)+1.

    Upper addend bit is known zero; omit its MAJ/UMA pair. All lower carry
    information is restored, allowing the same ancilla at every divider stage.
    """
    if len(b)!=len(a)+1 or not a:
        raise ValueError('Require nonempty A and one extra high B bit')
    # The incoming carry is clean. Specialize the first stage rather than
    # synthesizing a general three-input MAJ/UMA pair (three fewer CNOTs).
    ops=[('ccx',a[0],b[0],carry)]
    for i in range(1,len(a)):
        prev=carry if i==1 else a[i-1]
        ops.extend(majority(a[i],b[i],prev))
    top_carry=carry if len(a)==1 else a[-1]
    ops.append(('cx',top_carry,b[-1]))
    for i in reversed(range(1,len(a))):
        prev=carry if i==1 else a[i-1]
        ops.extend(unmajority_add(a[i],b[i],prev))
    ops.extend([('ccx',a[0],b[0],carry),('cx',a[0],b[0])])
    return ops


def build(nbits,pbits):
    if nbits<3 or pbits<2:
        raise ValueError('Require nbits>=3 and pbits>=2')
    c=ref.Circuit()
    p=c.reg('P',pbits)
    n=c.reg('N',nbits)
    r=c.reg('R',pbits+1)
    q=c.reg('Q',nbits)
    vp=c.reg('P_at_least_2',1)[0]
    vq=c.reg('Q_at_least_2',1)[0]
    flag=c.reg('good',1)[0]
    # Shared by arithmetic, validity, phase marking and diffusion at disjoint
    # lifetimes. The scratch register is zero at every handoff.
    shared=c.reg('mcx_scratch',max(len(r),nbits-3,pbits-3,1))
    masked=shared[:pbits]
    carry=shared[pbits]
    subtract=add_padded(p,r,carry)[::-1]
    restore=add_padded(masked,r,carry)
    ops=ref.nontrivial(p,vp,shared)
    for i in reversed(range(nbits)):
        for j in reversed(range(1,len(r))):
            a,b=r[j],r[j-1]
            ops.extend([('cx',a,b),('cx',b,a),('cx',a,b)])
        ops.append(('cx',n[i],r[0]))
        # At the stage boundary R<p for p>=1. After shift, 0<=R<2p.
        # Therefore the high bit of (R-p) mod 2**len(r) is exactly underflow.
        ops.extend(subtract)
        ops.append(('cx',r[-1],q[i]))
        # Conditional add-back P on underflow. Store the borrow temporarily in
        # Q so it stays stable while restoration changes the high remainder bit.
        mask_ops=[('ccx',q[i],pi,ti) for pi,ti in zip(p,masked)]
        ops.extend(mask_ops)
        ops.extend(restore)
        ops.extend(mask_ops[::-1])
        # Store borrow during restoration, then complement once to retain q_i.
        ops.append(('x',q[i]))
        # R is reduced, masked P and carry are clean. Only q_i remains as
        # reversible branch information; no per-stage difference/borrow history.
    ops.extend(ref.nontrivial(q,vq,shared))
    flips=[('x',bit) for bit in r]
    mark=flips+ref.mcx([vp,vq,*r],flag,shared)+flips[::-1]
    oracle=ops+mark+[('z',flag)]+mark[::-1]+ops[::-1]
    return c,ops,mark,oracle


def schedule_cost(ops):
    """Conservative all-to-all gate depth and Toffoli-weighted dependency depth."""
    depth={}
    weighted={}
    for name,*bits in ops:
        t=1+max((depth.get(b,0) for b in bits),default=0)
        w=(1 if name=='ccx' else 0)+max((weighted.get(b,0) for b in bits),default=0)
        for bit in bits:
            depth[bit]=t
            weighted[bit]=w
    return {'logical_gate_depth':max(depth.values(),default=0),
            'toffoli_weighted_dependency_depth':max(weighted.values(),default=0)}


def run(n,pbits=3,iterations=1,shots=2000,seed=12345):
    report=ref.run(n,pbits,iterations,shots,seed,builder=build)
    _,_,_,oracle=build(n.bit_length(),pbits)
    report['scope']='Exact sparse gate simulation; in-place divider with shared clean scratch'
    report['oracle_schedule_cost']=schedule_cost(oracle)
    report['intermediate_measurements']=0
    report['postselection']='Final good-flag readout only; failed shots retained in totals'
    return report


def selftest():
    add_cases=0
    for m in range(1,5):
        c=ref.Circuit()
        a=c.reg('a',m); b=c.reg('b',m+1); carry=c.reg('carry',1)[0]
        ops=add_padded(a,b,carry)
        for av in range(1<<m):
            for bv in range(1<<(m+1)):
                source=sum(((av>>i)&1)<<bit for i,bit in enumerate(a))
                source|=sum(((bv>>i)&1)<<bit for i,bit in enumerate(b))
                out=ref.sparse_apply({source:1+0j},ops)
                basis=next(iter(out))
                assert ref.value(basis,a)==av
                assert ref.value(basis,b)==(av+bv)%(1<<(m+1))
                assert not basis & (1<<carry)
                assert ref.sparse_apply(out,ops[::-1])=={source:1+0j}
                add_cases+=1
    division_cases=0
    for n in range(4,64):
        c,division,mark,oracle=build(n.bit_length(),3)
        old_c,old_div,old_mark,old_oracle=ref.build(n.bit_length(),3)
        for p in range(8):
            initial=ref.loaded_basis(c,n,p)
            out=ref.sparse_apply({initial:1+0j},division+mark)
            basis=next(iter(out))
            if p:
                assert ref.value(basis,c.registers['Q'])==n//p
                assert ref.value(basis,c.registers['R'])==n%p
            expected=p>=2 and p<n and n%p==0
            assert bool(ref.value(basis,c.registers['good']))==expected
            sign=-1+0j if expected else 1+0j
            assert ref.sparse_apply({initial:1+0j},oracle)=={initial:sign}
            old_initial=ref.loaded_basis(old_c,n,p)
            assert ref.sparse_apply({old_initial:1+0j},old_oracle)=={old_initial:sign}
            assert ref.sparse_apply(ref.sparse_apply({initial:1+0j},division),division[::-1])=={initial:1+0j}
            # All shared ancillas are clean even before the final uncompute.
            assert ref.value(basis,c.registers['mcx_scratch'])==0
            division_cases+=1
    rng=np.random.default_rng(917)
    random_cases=0
    for pbits in [2,4,5,6]:
        c,division,mark,oracle=build(8,pbits)
        pairs=[(int(rng.integers(4,256)),int(rng.integers(0,1<<pbits))) for _ in range(32)]
        # Deduplicate then give each N/P basis state an arbitrary complex weight.
        pairs=list(dict.fromkeys(pairs))
        amps=rng.normal(size=len(pairs))+1j*rng.normal(size=len(pairs))
        amps/=np.linalg.norm(amps)
        initial={ref.loaded_basis(c,n,p):amp for (n,p),amp in zip(pairs,amps)}
        expected={ref.loaded_basis(c,n,p):amp*(-1 if p>=2 and p<n and n%p==0 else 1)
                  for (n,p),amp in zip(pairs,amps)}
        out=ref.sparse_apply(initial,oracle)
        assert out==expected
        computed=ref.sparse_apply(initial,division+mark)
        for basis in computed:
            p=ref.value(basis,c.registers['P']); n=ref.value(basis,c.registers['N'])
            if p:
                assert ref.value(basis,c.registers['Q'])==n//p
                assert ref.value(basis,c.registers['R'])==n%p
            assert ref.value(basis,c.registers['mcx_scratch'])==0
        random_cases+=len(pairs)
    for n,m,k in [(15,3,1),(35,3,1),(74,3,1),(77,3,2),(143,4,2),(323,5,3),(331,5,3)]:
        new=run(n,m,k,100)
        old=ref.run(n,m,k,100)
        assert np.allclose(new['success_history'],old['success_history'])
        assert new['measured_factor_pairs']==old['measured_factor_pairs']
    return {'status':'PASS','exhaustive_adder_cases':add_cases,
            'exhaustive_divider_and_baseline_equivalence_cases':division_cases,
            'random_coherent_N_P_basis_terms':random_cases,
            'end_to_end_Grover_comparisons':7,
            'exact_phase_and_shared_scratch_cleanup_verified':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--N',type=int,default=35)
    parser.add_argument('--candidate-qubits',type=int,default=3)
    parser.add_argument('--iterations',type=int,default=1)
    parser.add_argument('--shots',type=int,default=2000)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--qasm',type=Path)
    parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    try:
        report=selftest() if args.selftest else run(args.N,args.candidate_qubits,args.iterations,args.shots)
        if args.qasm and not args.selftest:
            c,division,mark,oracle=build(args.N.bit_length(),args.candidate_qubits)
            load=[('x',bit) for i,bit in enumerate(c.registers['N']) if args.N & (1<<i)]
            ops=load+[('h',bit) for bit in c.registers['P']]
            for _ in range(args.iterations):
                ops+=oracle+ref.diffusion(c)
            ops+=division+mark
            args.qasm.write_text(ref.qasm(c,ops))
    except ValueError as error:
        parser.error(str(error))
    text=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__=='__main__':
    main()
