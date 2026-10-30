#!/usr/bin/env python3
"""N35 validity-only comparator candidate. No QPU. Run --qiskit for source proof."""
import argparse,itertools,json
def emit(qc,x,flag,carry,chain,controls=(),geq=True):
    import qrr_n35_single_modmul_ripple_toffoli as primitive
    assert len(x)==6 and len(carry)>=4
    t=carry[:4]
    qc.ccx(x[0],x[1],t[0])
    for a,b,d in ((x[2],t[0],t[1]),(x[3],t[1],t[2]),(x[4],t[2],t[3])):
        qc.cx(a,d);qc.cx(b,d);qc.ccx(a,b,d)
    if not geq:primitive.multi_x(qc,list(controls),flag,chain)
    primitive.multi_x(qc,list(controls)+[x[5],t[3]],flag,chain)
    for a,b,d in ((x[4],t[2],t[3]),(x[3],t[1],t[2]),(x[2],t[0],t[1])):
        qc.ccx(a,b,d);qc.cx(b,d);qc.cx(a,d)
    qc.ccx(x[0],x[1],t[0])
def local():
    count=0
    for y,f in itertools.product(range(64),range(2)):
        s=[(y>>i)&1 for i in range(6)]+[0]*4+[f]
        def cx(a,t):s[t]^=s[a]
        def ccx(a,b,t):s[t]^=s[a]&s[b]
        ccx(0,1,6)
        for a,b,t in ((2,6,7),(3,7,8),(4,8,9)):
            cx(a,t);cx(b,t);ccx(a,b,t)
        ccx(5,9,10)
        for a,b,t in ((4,8,9),(3,7,8),(2,6,7)):
            ccx(a,b,t);cx(b,t);cx(a,t)
        ccx(0,1,6)
        assert s==[(y>>i)&1 for i in range(6)]+[0]*4+[f^int(y>=35)]
        count+=1
    return count
def qiskit_proof():
    from qiskit import QuantumCircuit,QuantumRegister
    import qrr_n35_single_modmul_ripple_toffoli as primitive
    results={}
    for variant in ('baseline','candidate'):
        c=QuantumRegister(1,'control');x=QuantumRegister(6,'x');f=QuantumRegister(1,'flag')
        carry=QuantumRegister(6,'carry');chain=QuantumRegister(9,'chain')
        qc=QuantumCircuit(c,x,f,carry,chain)
        if variant=='baseline':primitive.predicate(qc,x,35,f[0],carry,chain,controls=[c[0]],geq=False)
        else:emit(qc,x,f[0],carry,chain,controls=[c[0]],geq=False)
        indices={q:i for i,q in enumerate(qc.qubits)}
        for ctrl,y,flag in itertools.product(range(2),range(64),range(2)):
            s=[0]*qc.num_qubits;s[indices[c[0]]]=ctrl;s[indices[f[0]]]=flag
            for i,q in enumerate(x):s[indices[q]]=(y>>i)&1
            for inst in qc.data:
                name=inst.operation.name;j=[indices[q] for q in inst.qubits]
                if name=='x':s[j[0]]^=1
                elif name=='cx':s[j[1]]^=s[j[0]]
                elif name=='ccx':s[j[2]]^=s[j[0]]&s[j[1]]
                else:raise AssertionError('not exact X/CX/CCX: '+name)
            assert s[indices[c[0]]]==ctrl and s[indices[f[0]]]==(flag^(ctrl and y<35))
            assert all(s[indices[q]]==((y>>i)&1) for i,q in enumerate(x))
            assert all(s[indices[q]]==0 for q in list(carry)+list(chain))
        results[variant]={'cases':256,'gates':dict(qc.count_ops()),'phase_plus_one':True}
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--qiskit',action='store_true');a=p.parse_args()
    result={'cpu_cases':local(),'qiskit_executed':False,'native_compiles':0,'qpu_jobs':0}
    if a.qiskit:result['source']=qiskit_proof();result['qiskit_executed']=True
    print(json.dumps(result,indent=2))
