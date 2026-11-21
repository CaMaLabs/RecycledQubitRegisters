#!/usr/bin/env python3
"""Generic reversible restoring divider and factor oracle, no answer lookup.

Compiler depends ONLY on register widths. N is loaded into a quantum register.
Allowed gates: H, Z, X, CX, CCX. No modulo/division is used to construct gates.
This transparent history-preserving construction is NOT qubit optimized.
The sparse simulator is exact on these small-superposition experiments.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np


class Circuit:
    def __init__(self):
        self.registers={}
        self.qubits=0

    def reg(self,name,width):
        result=list(range(self.qubits,self.qubits+width))
        self.registers[name]=result
        self.qubits+=width
        return result


def mcx(controls,target,scratch):
    """Conjunction into target, restored scratch; no opaque multi-qubit gate."""
    if not controls:
        return [('x',target)]
    if len(controls)==1:
        return [('cx',controls[0],target)]
    if len(controls)==2:
        return [('ccx',*controls,target)]
    if len(scratch)<len(controls)-2:
        raise ValueError('Insufficient MCX scratch')
    chain=[('ccx',controls[0],controls[1],scratch[0])]
    for j in range(2,len(controls)-1):
        chain.append(('ccx',scratch[j-2],controls[j],scratch[j-1]))
    return chain+[('ccx',scratch[len(controls)-3],controls[-1],target)]+chain[::-1]


def nontrivial(bits,flag,scratch):
    """flag XOR= value>=2, i.e. OR of all bits except the least significant."""
    controls=bits[1:]
    flips=[('x',q) for q in controls]
    return [('x',flag)]+flips+mcx(controls,flag,scratch)+flips[::-1]


def borrows(a,b,workspace):
    """Compute subtraction borrows, preserving inputs. Missing high b bits=0."""
    ops=[]
    for i,ai in enumerate(a):
        bi=b[i] if i<len(b) else None
        prev=workspace[i-1] if i else None
        out=workspace[i]
        # borrow_out = (~a & b) XOR (~a & borrow_in) XOR (b & borrow_in)
        ops.append(('x',ai))
        if bi is not None:
            ops.append(('ccx',ai,bi,out))
        if prev is not None:
            ops.append(('ccx',ai,prev,out))
        ops.append(('x',ai))
        if bi is not None and prev is not None:
            ops.append(('ccx',bi,prev,out))
    return ops


def build(nbits,pbits):
    if nbits<3 or pbits<2:
        raise ValueError('Require nbits>=3 and pbits>=2')
    c=Circuit()
    p=c.reg('P',pbits)
    n=c.reg('N',nbits)
    r=c.reg('R',pbits+1)
    q=c.reg('Q',nbits)
    vp=c.reg('P_at_least_2',1)[0]
    vq=c.reg('Q_at_least_2',1)[0]
    flag=c.reg('good',1)[0]
    scratch=c.reg('mcx_scratch',max(len(r),nbits-3,pbits-3,1))
    ops=nontrivial(p,vp,scratch)
    # N's bits are quantum controls. Gate list is independent of N's value.
    for i in reversed(range(nbits)):
        temp=c.reg(f'difference_{i}',len(r))
        borrow=c.reg(f'borrows_{i}',len(r))
        # Rotate left. Reachable R<p makes the wrapping top bit zero for p>=1.
        for j in reversed(range(1,len(r))):
            a,b=r[j],r[j-1]
            ops.extend([('cx',a,b),('cx',b,a),('cx',a,b)])
        ops.append(('cx',n[i],r[0]))
        chain=borrows(r,p,borrow)
        # q_i = [R>=p]. Uncompute comparator scratch before subtraction.
        ops.extend(chain)
        ops.extend([('x',q[i]),('cx',borrow[-1],q[i])])
        ops.extend(chain[::-1])
        # Compute difference R-p into fresh history bits, then select it.
        ops.extend(chain)
        for j in range(len(r)):
            ops.append(('cx',r[j],temp[j]))
            if j<len(p):
                ops.append(('cx',p[j],temp[j]))
            if j:
                ops.append(('cx',borrow[j-1],temp[j]))
        for a,b in zip(r,temp):
            # Fredkin(q_i,a,b), expressed only in CX and CCX.
            ops.extend([('cx',a,b),('ccx',q[i],b,a),('cx',a,b)])
        # History is retained; reversing the whole divider clears it later.
    ops.extend(nontrivial(q,vq,scratch))
    flips=[('x',bit) for bit in r]
    mark=flips+mcx([vp,vq,*r],flag,scratch)+flips[::-1]
    oracle=ops+mark+[('z',flag)]+mark[::-1]+ops[::-1]
    return c,ops,mark,oracle


def sparse_apply(state,ops):
    """Exact ideal statevector as {basis_integer: complex_amplitude}."""
    for op in ops:
        name,*bits=op
        if name=='h':
            out={}
            mask=1<<bits[0]
            for basis,amp in state.items():
                low=basis & ~mask
                high=low | mask
                out[low]=out.get(low,0)+amp/math.sqrt(2)
                out[high]=out.get(high,0)+amp*(-1 if basis & mask else 1)/math.sqrt(2)
            state={key:amp for key,amp in out.items() if abs(amp)>1e-14}
        elif name=='z':
            mask=1<<bits[0]
            state={basis:(-amp if basis & mask else amp) for basis,amp in state.items()}
        else:
            target=1<<bits[-1]
            controls=sum(1<<bit for bit in bits[:-1])
            state={(basis^target if basis & controls == controls else basis):amp
                   for basis,amp in state.items()}
    return state


def value(basis,bits):
    return sum(((basis>>bit)&1)<<j for j,bit in enumerate(bits))


def loaded_basis(c,n,p=0):
    basis=0
    for name,number in [('N',n),('P',p)]:
        for j,bit in enumerate(c.registers[name]):
            if number & (1<<j):
                basis|=1<<bit
    return basis


def diffusion(c):
    p=c.registers['P']
    scratch=c.registers['mcx_scratch']
    h=[('h',bit) for bit in p]
    x=[('x',bit) for bit in p]
    # H X MCZ X H: negative of the usual reflection, an irrelevant global phase.
    z=[('h',p[-1])]+mcx(p[:-1],p[-1],scratch)+[('h',p[-1])]
    return h+x+z+x[::-1]+h[::-1]


def run(n,pbits=3,iterations=1,shots=2000,seed=12345):
    if n<4 or iterations<0 or shots<1 or not 2<=pbits<=8:
        raise ValueError('Require N>=4, iterations>=0, shots>=1, 2<=pbits<=8')
    if n.bit_length()>24:
        raise ValueError('This demonstration limits N to 24 bits')
    c,division,mark,oracle=build(n.bit_length(),pbits)
    p=c.registers['P']
    state=sparse_apply({loaded_basis(c,n):1+0j},[('h',bit) for bit in p])
    history=[]
    def good_probability(current):
        final=sparse_apply(current,division+mark)
        return float(sum(abs(amp)**2 for basis,amp in final.items()
                         if value(basis,c.registers['good'])))
    history.append(good_probability(state))
    # Generic gates, not a classically enumerated list of satisfying candidates.
    for _ in range(iterations):
        state=sparse_apply(state,oracle+diffusion(c))
        history.append(good_probability(state))
    clean_mask=sum(1<<bit for name,bits in c.registers.items() if name not in ('N','P') for bit in bits)
    assert all(basis & clean_mask == 0 for basis in state)
    assert all(value(basis,c.registers['N'])==n for basis in state)
    final=sparse_apply(state,division+mark)
    basis=list(final)
    probabilities=np.array([abs(final[b])**2 for b in basis])
    norm=float(probabilities.sum())
    assert abs(norm-1)<1e-10
    probabilities/=norm
    samples=np.random.default_rng(seed).choice(len(basis),shots,p=probabilities)
    factors=Counter()
    for index in samples:
        b=basis[int(index)]
        if value(b,c.registers['good']):
            # BOTH factors are measured from quantum registers. No classical N/p.
            factor=value(b,p)
            partner=value(b,c.registers['Q'])
            assert factor*partner==n
            factors[f'{factor}*{partner}']+=1
    theta=math.asin(math.sqrt(min(1,history[0])))
    assert abs(history[-1]-math.sin((2*iterations+1)*theta)**2)<1e-10
    counts=Counter(op[0] for op in oracle)
    return {
        'N':n,'candidate_qubits':pbits,'total_qubits':c.qubits,
        'candidate_capacity':1<<pbits,'candidate_range':[0,(1<<pbits)-1],
        'validity':'P>=2, Q>=2 and R=0, computed reversibly',
        'iterations':iterations,'success_history':history,
        'shots':shots,'accepted_shots':sum(factors.values()),
        'measured_factor_pairs':dict(factors),
        'gate_counts_per_oracle':dict(counts),
        'division_gates':len(division),'oracle_gates':len(oracle),
        'postselection_readout_gates':len(division)+len(mark),
        'scratch_clean_after_each_oracle':True,
        'cofactor_from_quantum_quotient_register':True,
        'answer_lookup_or_classical_factor_preparation':False,
        'oracle_compiler_inputs':['N register width','P register width'],
        'sparse_basis_states_before_measurement':len(final),
        'norm':norm,
        'scope':'Exact sparse gate simulation; generic non-optimized reversible divider',
        'coverage':'At least one nontrivial divisor must fit P; no success is not a primality proof.',
    }


def selftest():
    cases=0
    for n in range(4,64):
        c,division,mark,oracle=build(n.bit_length(),3)
        for p in range(8):
            initial=loaded_basis(c,n,p)
            out=sparse_apply({initial:1+0j},division+mark)
            assert len(out)==1
            basis=next(iter(out))
            if p:
                # Python arithmetic is used ONLY for independent validation.
                assert value(basis,c.registers['Q'])==n//p
                assert value(basis,c.registers['R'])==n%p
            expected=(p>=2 and p<n and n%p==0)
            assert bool(value(basis,c.registers['good']))==expected
            oracle_out=sparse_apply({initial:1+0j},oracle)
            assert oracle_out=={initial:(-1+0j if expected else 1+0j)}
            assert sparse_apply(sparse_apply({initial:1+0j},division),division[::-1])=={initial:1+0j}
            cases+=1
    for n,m,k in [(15,3,1),(35,3,1),(74,3,1),(77,3,2),(143,4,2),(323,5,3),(331,5,3)]:
        result=run(n,m,k,100)
        assert result['scratch_clean_after_each_oracle']
    # One compiled oracle also works when N itself is in superposition.
    c,_,_,oracle=build(6,3)
    pairs=[(35,5),(35,3),(39,3),(39,5),(55,5),(55,7),(63,7),(63,2)]
    initial={loaded_basis(c,n,p):1/math.sqrt(len(pairs)) for n,p in pairs}
    expected={loaded_basis(c,n,p):(-1 if n%p==0 else 1)/math.sqrt(len(pairs))
              for n,p in pairs}
    assert sparse_apply(initial,oracle)==expected
    return {'status':'PASS','exhaustive_N_P_cases':cases,'grover_runs':7,
            'verified':['quotient','remainder','validity flag','phase oracle sign',
                        'division inverse','scratch cleanup','Grover probability',
                        'coherent superposition of target N values'],
            'oracle_compilation_uses_no_factors_or_divisibility_table':True}


def qasm(c,ops):
    lines=['OPENQASM 2.0;','include "qelib1.inc";',f'qreg q[{c.qubits}];',f'creg c[{c.qubits}];']
    for name,bits in c.registers.items():
        lines.append('// '+name+' little-endian bits: '+','.join(map(str,bits)))
    for name,*bits in ops:
        lines.append(name+' '+','.join(f'q[{b}]' for b in bits)+';')
    lines.append('measure q -> c;')
    return '\n'.join(lines)+'\n'


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
            load=[('x',bit) for j,bit in enumerate(c.registers['N']) if args.N & (1<<j)]
            ops=load+[('h',bit) for bit in c.registers['P']]
            for _ in range(args.iterations):
                ops+=oracle+diffusion(c)
            ops+=division+mark
            args.qasm.write_text(qasm(c,ops))
    except ValueError as error:
        parser.error(str(error))
    text=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__=='__main__':
    main()
