#!/usr/bin/env python3
"""N35 reversible comparator CPU proof; not a Qiskit or native Fez benchmark."""
import itertools,json
def cx(s,a,t): s[t]^=s[a]
def ccx(s,a,b,t): s[t]^=s[a]&s[b]
def circuit(y,flag):
    s=[(y>>i)&1 for i in range(6)]+[0]*4+[flag]; gates=[]
    def gate(name,*idx):
        gates.append((name,idx))
        (cx if name=='cx' else ccx)(s,*idx)
    gate('ccx',0,1,6)
    stages=[(2,6,7),(3,7,8),(4,8,9)]
    for a,b,t in stages:
        gate('cx',a,t);gate('cx',b,t);gate('ccx',a,b,t)
    gate('ccx',5,9,10)
    for a,b,t in reversed(stages):
        gate('ccx',a,b,t);gate('cx',b,t);gate('cx',a,t)
    gate('ccx',0,1,6)
    return s,gates
def main():
    for y,flag in itertools.product(range(64),range(2)):
        state,_=circuit(y,flag)
        expected=[(y>>i)&1 for i in range(6)]+[0]*4+[flag^int(y>=35)]
        assert state==expected,(y,flag)
    _,gates=circuit(0,0)
    result={'pass':True,'cases':128,'width_data':6,'clean_scratch':4,
      'dirty_flag_restored_by_second_application':True,
      'exact_plus_one_phase':'CX/CCX reversible basis permutation',
      'gate_counts':{k:sum(name==k for name,_ in gates) for k in ('cx','ccx')},
      'source_versus_baseline':'not measured','qiskit_circuit_built':False,
      'ibm_fez_compiles':0,'qpu_jobs':0}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
