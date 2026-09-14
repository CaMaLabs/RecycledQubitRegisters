import math
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path

OUT = Path("results/simulation")
OUT.mkdir(parents=True, exist_ok=True)
SEED=8776
rng=np.random.default_rng(SEED)

# Wide-register QPE probability distribution for an eigenphase phi.
def qpe_reference(phi,m):
    N=2**m
    probs=np.empty(N)
    for y in range(N):
        d=phi-y/N
        den=math.sin(math.pi*d)
        probs[y]=1.0 if abs(den)<1e-14 else (math.sin(math.pi*N*d)/(N*den))**2
    return probs/probs.sum()

# Exact branch enumeration for iterative/recycled QPE using one phase ancilla
# and one system qubit. The measured phase bits are retained classically.
def iterative_qpe(phi,m):
    branches={():1.0}
    for k in range(m-1,-1,-1):
        nxt={}
        for revbits,p in branches.items():
            prior={m-1-i:b for i,b in enumerate(revbits)}
            corr=sum(prior[j]/(2**(j-k+1)) for j in prior)
            phase=((2**k)*phi-corr)%1.0
            p0=math.cos(math.pi*phase)**2
            nxt[revbits+(0,)]=nxt.get(revbits+(0,),0.0)+p*p0
            nxt[revbits+(1,)]=nxt.get(revbits+(1,),0.0)+p*(1-p0)
        branches=nxt
    out=np.zeros(2**m)
    for revbits,p in branches.items():
        y=0
        for b in revbits[::-1]:
            y=(y<<1)|b
        out[y]+=p
    return out

qpe_rows=[]
for m in (4,8,12,16):
    errs=[]
    for _ in range(40):
        phi=float(rng.random())
        errs.append(float(np.max(np.abs(qpe_reference(phi,m)-iterative_qpe(phi,m)))))
    qpe_rows.append({"phase_bits":m,"wide_qubits":m+1,"recycled_qubits":2,"max_distribution_error":max(errs)})
pd.DataFrame(qpe_rows).to_csv(OUT/'hybrid_qpe_results.csv',index=False)

# Entanglement-width stress proxy. Random graph edges model simultaneously
# coherent interactions; architectures fail as required live width exceeds capacity.
stress=[]
for depth in (2,4,6,8,10):
    for qcap in (2,4,8):
        vals=[]
        for _ in range(500):
            active=set()
            for __ in range(depth):
                a,b=rng.choice(16,size=2,replace=False)
                active.update((int(a),int(b)))
                if len(active)>qcap:
                    break
            vals.append(1.0 if len(active)<=qcap else math.exp(-0.45*(len(active)-qcap)))
        stress.append({"depth":depth,"physical_qbits":qcap,"fidelity_proxy":float(np.mean(vals))})
pd.DataFrame(stress).to_csv(OUT/'hybrid_entanglement_results.csv',index=False)

# Lightweight synthetic scheduler experiment. Features represent circuit width,
# edge count, depth and measurement friendliness; the label is the smallest
# resource class expected to support the workload.
rows=[]
for _ in range(240):
    width=int(rng.integers(1,17))
    depth=int(rng.integers(1,21))
    edges=int(rng.integers(0,max(1,width*(width-1)//3+1)))
    meas=float(rng.random())
    if width<=2 and meas>0.35:
        label=2
    elif width<=4 and (edges<8 or meas>0.55):
        label=4
    else:
        label=8
    rows.append((width,depth,edges,meas,label))
df=pd.DataFrame(rows,columns=['logical_width','depth','entangling_edges','measurement_friendliness','qmem_class'])
idx=rng.permutation(len(df))
train=df.iloc[idx[:180]]
test=df.iloc[idx[180:]].copy()
clf=RandomForestClassifier(n_estimators=200,random_state=SEED,max_depth=7).fit(train.iloc[:,:4],train['qmem_class'])
test['prediction']=clf.predict(test.iloc[:,:4])
test['correct']=test['prediction']==test['qmem_class']
test.to_csv(OUT/'hybrid_scheduler_results.csv',index=False)

print('Wrote:', OUT/'hybrid_qpe_results.csv')
print('Wrote:', OUT/'hybrid_entanglement_results.csv')
print('Wrote:', OUT/'hybrid_scheduler_results.csv')
