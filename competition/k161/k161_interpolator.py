#!/usr/bin/env python3
"""K161 exact X/CX/CCX bounded reversible selected-slope affine interpolation.

This is a small-width circuit prototype, NOT a full K159 Q14 or Helios circuit.
Checks: coherent segment selector, variable offset, rounded multiplication,
XOR into arbitrary output, complete workspace uncomputation.
"""
import argparse, collections, hashlib, json, random
from pathlib import Path

PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def coeff(q=4):
    S=1<<q; d=[]
    for j in range(8):
        if j<4: m0=1+j/4; m1=1+(j+1)/4
        else: m0=2+2*(j-4)/4; m1=2+2*(j-3)/4
        a=round(S/(m0**0.5))
        b=round(S*((m0**-0.5)-(m1**-0.5))/(m1-m0))
        d.append((a,b))
    return d

def mcx(controls, target, anc):
    n=len(controls)
    assert target not in controls and len(set(controls))==n
    if n==0:return [('X',target)]
    if n==1:return [('CX',controls[0],target)]
    if n==2:return [('CCX',controls[0],controls[1],target)]
    if len(anc)<n-2:raise ValueError(f'Need {n-2} clean scratch')
    chain=[('CCX',controls[0],controls[1],anc[0])]
    for i in range(2,n-1):chain.append(('CCX',anc[i-2],controls[i],anc[i-1]))
    return chain+[('CCX',anc[n-3],controls[-1],target)]+chain[::-1]

def power_add(controls, word, position, subtract, anc):
    """Reversible modular add/subtract 2^position, if all controls are one.
    High-to-low update reads original less significant bits; subtract uses NOT those bits.
    """
    g=[]
    for index in reversed(range(position,len(word))):
        lower=word[position:index]
        if subtract:g.extend(('X',q) for q in lower)
        g+=mcx(list(controls)+lower,word[index],anc)
        if subtract:g.extend(('X',q) for q in reversed(lower))
    return g

def lookup(selector, out, values, anc):
    assert len(values)==1<<len(selector)
    # Unconditional reversible truth-table via per-key bit-controlled X.
    # It is deliberately naive: exact and easy to audit, not globally optimized.
    g=[]
    for address,value in enumerate(values):
        for j,q in enumerate(selector):
            if not ((address>>j)&1):g.append(('X',q))
        for bit, target in enumerate(out):
            if (value>>bit)&1:g+=mcx(selector,target,anc)
        for j in reversed(range(len(selector))):
            if not ((address>>j)&1):g.append(('X',selector[j]))
    return g

def circuit(q=4):
    # selector 3 / unsigned offset q / XOR target q+1 / seed q+1
    # product 2q+1 / clean MCX chain q+6.
    ob=q+1; pw=2*q+1
    sel=list(range(3))
    off=list(range(3,3+q))
    out=list(range(3+q,3+q+ob))
    seed=list(range(out[-1]+1,out[-1]+1+ob))
    prod=list(range(seed[-1]+1,seed[-1]+1+pw))
    # Highest number of controls: 3 selector+1 offset+(pw-1) product low = pw+3
    anc=list(range(prod[-1]+1,prod[-1]+1+(pw+1)))
    c=coeff(q)
    compute=lookup(sel,seed,[v[0] for v in c],anc)
    for address,(_,slope) in enumerate(c):
        mask=[]
        for j,t in enumerate(sel):
            if not ((address>>j)&1):mask.append(('X',t))
        compute+=mask
        for j,qoff in enumerate(off):
            for k in range(slope.bit_length()):
                if (slope>>k)&1:
                    compute+=power_add(sel+[qoff],prod,j+k,False,anc)
        compute+=mask[::-1]
    compute+=power_add([],prod,q-1,False,anc)
    # Compute rounded product into the seed via modular subtraction.
    for bit in range(ob):
        compute+=power_add([prod[q+bit]],seed,bit,True,anc)
    extract=[('CX',seed[j],out[j]) for j in range(ob)]
    gates=compute+extract+compute[::-1]
    resource={'selector_bits':len(sel),'offset_bits':len(off),
      'xor_output_bits':len(out),'seed_work_bits':len(seed),
      'product_work_bits':len(prod),'mcx_chain_work_bits':len(anc),
      'total_wires':len(sel)+len(off)+len(out)+len(seed)+len(prod)+len(anc),
      'scratch_wires':len(seed)+len(prod)+len(anc)}
    return gates,resource,c

def play(v,g):
    for op,*a in g:
        if op=='X':v^=1<<a[0]
        elif op=='CX':v^=((v>>a[0])&1)<<a[1]
        elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
        else:raise ValueError(op)
    return v

def check(q,g,c,exhaustive=True):
    rng=random.Random(161+q);states=0;mask=(1<<(q+1))-1
    for s in range(8):
        for off in range(1<<q):
            dvals=(0,mask,rng.randrange(mask+1)) if exhaustive else (0,)
            for d in dvals:
                v=s|(off<<3)|(d<<(3+q))
                seed=(c[s][0] - ((c[s][1]*off + (1<<(q-1)))>>q))&mask
                desired=s|(off<<3)|((d^seed)<<(3+q))
                actual=play(v,g)
                assert actual==desired,(q,s,off,d,seed,hex(actual^desired))
                assert play(actual,g)==v,(q,s,off,d,'not self inverse')
                states+=1
    return states

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--q',type=int,default=4,choices=(3,4))
    p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
    p.add_argument('--out',type=Path,default=Path('competition/k161/results/interpolator.json'))
    p.add_argument('--selftest',action='store_true')
    args=p.parse_args()
    # q4 384 state checks, q3 192; no q14 gate generation
    g,resources,c=circuit(args.q)
    states=check(args.q,g,c)
    ct=collections.Counter(op for op,*_ in g)
    print('K161_SELFTEST PASS selected slope times coherent offset, rounding, arbitrary XOR outputs, all scratch clean',flush=True)
    if args.selftest:return
    sha=hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
    row={'status':'BOUNDED_REVERSIBLE_AFFINE_INTERPOLATOR_NOT_FULL_HELIOS',
         'q':args.q,'states':states,'counts':dict(ct),'resources':resources,'coefficients':c,
         'pinned_sha256':sha,'warnings':[
           'Exact small-width gate-level oracle only; the q14 K159 datapath is not synthesized.',
           'Naive selected partial-products and modular subtract may far exceed cost savings.',
           'Scratch footprint exceeds K151 free 12, so this architecture does NOT fit the compact 62-qubit plan.',
           'No official verifier or leaderboard score improvement.']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(row,indent=2)+'\n')
    print('K161_RESULT',json.dumps({'q':args.q,'CCX':ct['CCX'],'CX':ct['CX'],
       'X':ct['X'],'scratch':resources['scratch_wires'],
       'total_wires':resources['total_wires'],'tested_cases':states,
       'full_helios_candidate':False,'out':str(args.out)}),flush=True)
if __name__=='__main__':main()
