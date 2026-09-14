#!/usr/bin/env python3
"""Reproducible ISA-level experiments for recycled quantum registers.

This script tests four things:
1. exact equivalence of iterative/recycled QPE to the wide ideal distribution,
2. a normalized latency model for local vs host feedback,
3. an entanglement-width stress proxy,
4. a learned resource router over synthetic circuits.

The latency units are normalized serialized costs, not claimed hardware ns/us.
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

OUT = Path("results/simulation")
OUT.mkdir(parents=True, exist_ok=True)
SEED = 8776
rng = np.random.default_rng(SEED)

LAT = {
    "1q": 1.0,
    "2q": 5.0,
    "measure": 20.0,
    "reset": 10.0,
    "local_feedback": 1.0,
    "host_roundtrip": 250.0,
}

ARCHS = [
    ("8C0Q", 8, 0, "none"),
    ("6C2Q", 6, 2, "local"),
    ("4C4Q", 4, 4, "local"),
    ("Host-2Q-QPU", 0, 2, "host"),
]

def qpe_reference(phi, m):
    N = 2**m
    p = np.empty(N)
    for y in range(N):
        d = phi - y/N
        den = math.sin(math.pi*d)
        p[y] = 1.0 if abs(den) < 1e-14 else (math.sin(math.pi*N*d)/(N*den))**2
    return p/p.sum()

def iterative_qpe(phi, m):
    branches = {(): 1.0}
    for k in range(m-1, -1, -1):
        nxt = {}
        for revbits, weight in branches.items():
            prior = {m-1-i:b for i,b in enumerate(revbits)}
            corr = sum(prior[j]/(2**(j-k+1)) for j in prior)
            phase = ((2**k)*phi - corr) % 1.0
            p0 = math.cos(math.pi*phase)**2
            nxt[revbits+(0,)] = nxt.get(revbits+(0,), 0.0) + weight*p0
            nxt[revbits+(1,)] = nxt.get(revbits+(1,), 0.0) + weight*(1-p0)
        branches = nxt
    out = np.zeros(2**m)
    for revbits, weight in branches.items():
        y = 0
        for b in revbits[::-1]:
            y = (y << 1) | b
        out[y] += weight
    return out

def standard_cost(m):
    inv2 = m*(m-1)//2
    return m*LAT['1q'] + m*LAT['2q'] + m*LAT['1q'] + inv2*LAT['2q'] + LAT['measure']

def iterative_cost(m, feedback):
    fb = LAT['local_feedback'] if feedback == 'local' else LAT['host_roundtrip']
    return m*(LAT['1q']+LAT['2q']+LAT['measure']+LAT['reset']+fb) + max(m-1,0)*LAT['1q']

def break_even_feedback(m):
    fixed = m*(LAT['1q']+LAT['2q']+LAT['measure']+LAT['reset']) + max(m-1,0)*LAT['1q']
    return (standard_cost(m)-fixed)/m

# QPE / latency comparison
qpe_rows = []
for m in (4, 8, 12, 16):
    errs = []
    for _ in range(40):
        phi = float(rng.random())
        errs.append(float(np.max(np.abs(qpe_reference(phi,m)-iterative_qpe(phi,m)))))
    for name, cbits, qbits, feedback in ARCHS:
        if qbits == 0:
            qpe_rows.append({
                'architecture': name, 'phase_bits': m, 'native_supported': False,
                'physical_qbits': 0, 'classical_bits_per_word': cbits,
                'max_distribution_error': np.nan, 'serialized_latency': np.nan,
                'standard_qpe_qubits_required': m+1,
                'standard_qpe_serialized_latency': standard_cost(m),
                'break_even_feedback_per_round': break_even_feedback(m),
                'parallel_ipe_lanes': 0,
            })
            continue
        qpe_rows.append({
            'architecture': name, 'phase_bits': m, 'native_supported': True,
            'physical_qbits': qbits, 'classical_bits_per_word': cbits,
            'max_distribution_error': max(errs),
            'serialized_latency': iterative_cost(m,feedback),
            'standard_qpe_qubits_required': m+1,
            'standard_qpe_serialized_latency': standard_cost(m),
            'break_even_feedback_per_round': break_even_feedback(m),
            'parallel_ipe_lanes': max(1,qbits//2),
        })
pd.DataFrame(qpe_rows).to_csv(OUT/'isa_qpe_comparison.csv', index=False)

# Batch throughput at 8 phase bits, 64 jobs.
batch = []
for name, cbits, qbits, feedback in ARCHS:
    lanes = 0 if qbits == 0 else max(1,qbits//2)
    supported = qbits >= 2
    latency = np.nan if not supported else math.ceil(64/lanes)*iterative_cost(8,feedback)
    batch.append({'architecture':name,'jobs':64,'phase_bits':8,'supported':supported,'parallel_lanes':lanes,'batch_latency':latency})
pd.DataFrame(batch).to_csv(OUT/'isa_batch_throughput.csv', index=False)

# Feedback-latency sensitivity.
rows=[]
for m in (8,12,16):
    std=standard_cost(m)
    for fb in (0,1,2,5,10,20,50,100,250):
        fixed=m*(LAT['1q']+LAT['2q']+LAT['measure']+LAT['reset'])+max(m-1,0)*LAT['1q']
        hy=fixed+m*fb
        rows.append({'phase_bits':m,'feedback_latency_per_round':fb,'hybrid_latency':hy,'standard_latency':std,'hybrid_speedup_vs_standard':std/hy})
pd.DataFrame(rows).to_csv(OUT/'isa_feedback_latency_sweep.csv', index=False)

# Entanglement-width proxy calibrated to expose the qualitative boundary.
def fidelity_proxy(required_width, capacity):
    if required_width <= capacity:
        return 1.0
    return math.exp(-0.42*(required_width-capacity))

stress=[]
for depth in (2,4,6,8,10):
    vals={2:[],4:[],8:[]}
    for _ in range(700):
        active=set()
        for __ in range(depth):
            a,b=rng.choice(16,size=2,replace=False)
            active.update((int(a),int(b)))
        required=max(2,min(16,len(active)))
        for cap in vals:
            vals[cap].append(fidelity_proxy(required,cap))
    stress.append({
        'logical_qubits':16,'depth':depth,
        '6C2Q_fidelity_proxy':float(np.mean(vals[2])),
        '4C4Q_fidelity_proxy':float(np.mean(vals[4])),
        '8Q_memory_fidelity_proxy':float(np.mean(vals[8])),
        'full_16Q_fidelity':1.0,
    })
pd.DataFrame(stress).to_csv(OUT/'isa_entanglement_stress.csv', index=False)

# Synthetic circuit-resource router.
records=[]
for _ in range(220):
    n=int(rng.choice([6,8,10,12]))
    depth=int(rng.integers(1,13))
    max_edges=n*(n-1)//2
    density=float(rng.random())
    ent=int(round(density*min(max_edges,depth*n/2)))
    max_cut=max(0,min(n//2,int(round(density*depth/2))))
    # Label from a simple fidelity-oriented capacity rule.
    if max_cut <= 2 and ent <= max(8,depth*2):
        req=2
    elif max_cut <= 5 and ent <= max(30,depth*5):
        req=4
    else:
        req=8
    records.append({'n':n,'depth':depth,'ent_gate_count':ent,'ent_gate_density':density,'max_cut_ent_gates':max_cut,'required_qmem':req})

df=pd.DataFrame(records)
X=df[['n','depth','ent_gate_count','ent_gate_density','max_cut_ent_gates']]
y=df['required_qmem']
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.30,random_state=SEED,stratify=y)
clf=RandomForestClassifier(n_estimators=300,max_depth=7,random_state=SEED).fit(Xtr,ytr)
pred=clf.predict(Xte)
hold=Xte.copy()
hold['required_qmem']=yte.values
hold['predicted_qmem']=pred
hold['exact_class']=hold['required_qmem']==hold['predicted_qmem']
hold['underprovision']=hold['predicted_qmem']<hold['required_qmem']
hold['overprovision']=hold['predicted_qmem']>hold['required_qmem']
hold['route']=hold['predicted_qmem'].map({2:'6C2Q',4:'4C4Q',8:'8Q accelerator'})
hold.to_csv(OUT/'isa_scheduler_holdout.csv',index=False)
summary=pd.DataFrame([{
    'samples_total':len(df), 'holdout_samples':len(hold),
    'holdout_accuracy':accuracy_score(yte,pred),
    'underprovision_rate':float(hold['underprovision'].mean()),
    'overprovision_rate':float(hold['overprovision'].mean()),
    'mean_required_qmem':float(hold['required_qmem'].mean()),
    'mean_predicted_qmem':float(hold['predicted_qmem'].mean()),
    'required_class_counts':dict(hold['required_qmem'].value_counts().sort_index()),
}])
summary.to_csv(OUT/'isa_scheduler_summary.csv',index=False)

print('Wrote ISA benchmark tables to', OUT)
