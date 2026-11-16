#!/usr/bin/env python3
"""K166 range hybrid Q14->Q26 study + phase-correct selected fixed row.
Classical coefficients, coherent selector and operand; not full Helios KMX.
Depends on existing K156, K157, K159 local research Python files.
"""
import argparse,collections,hashlib,json,random,sys
from pathlib import Path
import numpy as np
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
LIMIT=3133452
MASKS=(0b00101,0b01010,0b10101,0b11010)

def modules():
    root=Path(__file__).resolve().parents[2]
    for sub in ('k156','k157','k159'):
        sys.path.insert(0,str(root/'competition'/sub))
    import k156_ripple_measure as k156
    import k157_recycled_carry as k157
    import k159_log_linear_seed as k159
    return k156,k157,k159

def row_prepare(n,selector,operand,row,flag):
    g=[]
    for s,mask in enumerate(MASKS):
        neg=[('X',selector[i]) for i in range(2) if not (s>>i)&1]
        g+=neg+[('CCX',selector[0],selector[1],flag)]+neg[::-1]
        for bit in range(n):
            if (mask>>bit)&1:g.append(('CCX',flag,operand[bit],row[bit]))
        g+=neg+[('CCX',selector[0],selector[1],flag)]+neg[::-1]
    return g

def construct(n,measured,k156,k157):
    assert n>=4
    old,_=k156.compose(n)
    a,b,z=k156.wires(n)[:3]
    base=old if not measured else k157.circuit(n)
    carry_count=n-1 if not measured else n-2
    selector=list(range(3*n+carry_count,3*n+carry_count+2))
    flag=selector[-1]+1
    prep=row_prepare(n,selector,b,a,flag)
    return prep+base+prep[::-1],{
        'selector':selector,'carry_scratch':carry_count,
        'additional_flag_scratch':1,
        'total_scratch':carry_count+1,'total_wires':flag+1}

def verify(n,old,new,k156,k157,samples=384):
    rng=random.Random(166+n);branches=0
    for _ in range(samples):
        s=rng.randrange(4);operand=rng.randrange(1<<n);z=rng.randrange(1<<n)
        result=(operand+(operand&MASKS[s]))&((1<<n)-1)
        before=(operand<<n)|(z<<(2*n))|(s<<(3*n+(n-2)))
        oldbefore=(operand<<n)|(z<<(2*n))|(s<<(3*n+(n-1)))
        oldwant=(operand<<n)|((z^result)<<(2*n))|(s<<(3*n+(n-1)))
        assert k156.play_classical(oldbefore,old)==oldwant,(n,s,operand,z,'Bennett')
        for bits in range(1<<(n-1)):
            m={f'm{i}':(bits>>(i-1))&1 for i in range(1,n)}
            actual,phase=k157.run(before,new,m)
            want=(operand<<n)|((z^result)<<(2*n))|(s<<(3*n+(n-2)))
            assert actual==want and phase==0,(n,s,operand,z,bits,phase,hex(actual^want))
            branches+=1
    return {'basis_samples':samples,'measurement_branches':branches,
            'coherent_phase':'ZERO_ON_ALL_TESTED_BRANCHES'}

def numerical(max_x,chunk,k159):
    q=14;q2=26;S=1<<q;EPS=2**-24
    coeff=k159.line_coeff(q,8,'chord')
    inter=np.array([v[0] for v in coeff],dtype=np.int64)
    slope=np.array([v[1] for v in coeff],dtype=np.int64)
    origin=np.array([v[2] for v in coeff],dtype=np.int64)
    lookup=k159.lookup(q)
    stats=[{'segment':s,'count':0,'affine_violations':0,'lut_violations':0,
           'affine_worst_fraction':0.,'lut_worst_fraction':0.} for s in range(8)]
    for first in range(1,max_x+1,chunk):
        x=np.arange(first,min(first+chunk,max_x+1),dtype=np.int64)
        exponent=np.frexp(x.astype(float))[1]-1;k=exponent//2
        shift=np.left_shift(np.int64(1),2*k)
        mant=(x<<q)//shift
        seg=np.where(mant<2*S,((mant-S)*4)//S,
                     4+((mant-2*S)*4)//(2*S))
        assert np.all((seg>=0)&(seg<8))
        affine=inter[seg]-((slope[seg]*(mant-origin[seg])+S//2)//S)
        lookup_index=np.where(mant<2*S,((mant-S)*32)//S,
                              32+((mant-2*S)*32)//(2*S))
        direct=lookup[lookup_index]
        mant2=(x<<q2)//shift
        truth=1/np.sqrt(x.astype(float))
        for label,y0 in (('affine',affine),('lut',direct)):
            y1=k159.refine(y0,mant,q)
            y2=k159.refine(y1<<(q2-q),mant2,q2)
            predicted=y2.astype(float)/(1<<q2)/np.left_shift(np.int64(1),k)
            error=np.abs(predicted-truth)/truth/EPS
            for s in range(8):
                selected=seg==s
                if not np.any(selected):continue
                row=stats[s];v=error[selected]
                if label=='affine':row['count']+=len(v)
                row[label+'_worst_fraction']=max(row[label+'_worst_fraction'],float(v.max()))
                row[label+'_violations']+=int(np.count_nonzero(v>=1))
    return stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
    p.add_argument('--out',type=Path,default=Path('competition/k166/results/hybrid.json'))
    p.add_argument('--max-x',type=int,default=LIMIT)
    p.add_argument('--chunk',type=int,default=100000)
    p.add_argument('--selftest',action='store_true')
    a=p.parse_args()
    if not 1<=a.max_x<=LIMIT or a.chunk<100:p.error('invalid range/chunk')
    k156,k157,k159=modules()
    old,oldres=construct(5,False,k156,k157)
    new,newres=construct(5,True,k156,k157)
    proof=verify(5,old,new,k156,k157,384)
    co=collections.Counter(op for op,*_ in old)
    cn=collections.Counter(op for op,*_ in new)
    assert (co['CCX'],cn['CCX'])==(50,45)
    assert (oldres['total_scratch'],newres['total_scratch'])==(5,4)
    assert proof['measurement_branches']==6144
    print('K166_SELFTEST PASS classically stored row constants, coherent selector, all phases and scratch clean',flush=True)
    if a.selftest:return
    sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
    ranges=numerical(a.max_x,a.chunk,k159)
    for row in ranges:print('K166_RANGE',json.dumps(row),flush=True)
    report={'status':'BOUNDED_COHERENT_RANGE_SELECTION_AND_FULL_DOMAIN_NUMERIC_ONLY',
      'pinned_sha256':sha,'full_domain_inputs_tested':a.max_x,'ranges':ranges,
      'selected_row':{'width':5,'classical_masks':MASKS,
        'old_CCX':co['CCX'],'new_CCX':cn['CCX'],
        'old_scratch':oldres['total_scratch'],'new_scratch':newres['total_scratch'],
        'new_HMR':cn['HMR'],'new_conditional_CZ':cn['CZ_IF'],
        'new_conditional_CX':cn['CX_IF'],'proof':proof},
      'warnings':['Row example uses four classical bitmask constants, NOT actual Q14 K159 slopes.',
         'Selector and variable operand remain coherent; constants are compiled into controlled gates.',
         'Coherent choice of full algorithms would require additional controlled arithmetic and cleanup.',
         'No reversible Q14 interpolation datapath, Kickmix conditional syntax verification or official score gain.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K166_RESULT',json.dumps({'selected_row_old_CCX':co['CCX'],
      'selected_row_measured_CCX':cn['CCX'],
      'scratch_old':oldres['total_scratch'],
      'scratch_measured':newres['total_scratch'],
      'checked_measurement_branches':proof['measurement_branches'],
      'numeric_inputs':a.max_x,'full_helios_candidate':False,
      'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
