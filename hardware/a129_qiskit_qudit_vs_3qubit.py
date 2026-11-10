#!/usr/bin/env python3
"""A129: Qiskit 3-qubit baseline for an eight-level increment.

This measures qubit *gate counts and depth*, not runtime, noise, or actual
native spin-7/2 operation cost. The eight-level physical-order X8 is also
compiled as a generic 3-qubit unitary for a fair functional comparison.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

DIM=8
L2P=(0,2,4,6,7,5,3,1)
X8=np.roll(np.eye(DIM,dtype=complex),1,axis=0)
P=np.zeros((DIM,DIM),complex)
for logical,physical in enumerate(L2P):P[physical,logical]=1
SPIN_X8=P@X8@P.conj().T

def error_phase_invariant(actual,target):
    # Circuits are physically equivalent up to a global phase.
    overlap=np.vdot(target,actual)
    phase=np.exp(1j*np.angle(overlap))
    return float(np.max(np.abs(actual-phase*target)))

def metrics(circuit):
    counts={str(k):int(v) for k,v in circuit.count_ops().items()}
    return {'qubits':circuit.num_qubits,'depth':circuit.depth(),
        'size':circuit.size(),'ops':counts,
        'cx_count':counts.get('cx',0),'two_qubit_count':sum(
            v for k,v in counts.items() if k in ('cx','cz','ecr','swap'))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--optimization-levels',type=int,nargs='+',default=[0,1,2,3])
    p.add_argument('--out',type=Path,default=Path('results/a129_qiskit_three_qubit_comparison.json'))
    a=p.parse_args()
    try:
        from qiskit import QuantumCircuit,transpile
        from qiskit.quantum_info import Operator
        import qiskit
    except ImportError as exc:
        raise SystemExit('Install Qiskit in your experiment venv: python -m pip install qiskit') from exc
    inc=QuantumCircuit(3,name='ripple_increment_mod8')
    # Little endian. High-to-low carries use OLD low bits.
    inc.ccx(0,1,2)
    inc.cx(0,1)
    inc.x(0)
    decoded=QuantumCircuit(3,name='dense_logical_x8')
    decoded.unitary(Operator(X8),[0,1,2])
    encoded=QuantumCircuit(3,name='encoded_spin_level_x8')
    encoded.unitary(Operator(SPIN_X8),[0,1,2])
    circuits={'ripple_increment':(inc,X8),
              'dense_logical_x8':(decoded,X8),
              'spin_level_encoded_dense':(encoded,SPIN_X8)}
    records=[]
    for architecture,cmap in [('all_to_all',None),
                              ('linear_0_1_2',[[0,1],[1,0],[1,2],[2,1]])]:
        for level in a.optimization_levels:
            for label,(circuit,target) in circuits.items():
                compiled=transpile(circuit,
                    basis_gates=['rz','sx','x','cx'],
                    coupling_map=cmap,
                    optimization_level=level,
                    seed_transpiler=129)
                error=error_phase_invariant(Operator(compiled).data,target)
                row={'architecture':architecture,'optimization_level':level,
                     'circuit':label,'max_unitary_error_up_to_global_phase':error,
                     **metrics(compiled)}
                records.append(row)
                print('A129_POINT',json.dumps(row),flush=True)
    status='PASS_QISKIT_EQUIVALENCE' if all(
       row['max_unitary_error_up_to_global_phase']<1e-10 for row in records) else 'FAIL'
    result={'status':status,'qiskit_version':getattr(qiskit,'__version__','unknown'),
            'encoding_logical_to_physical_levels':list(L2P),
            'records':records,
            'limitations':[
              'Three qubits represent one ideal eight-level system; this does not run on native qudit hardware.',
              'Circuit counts compare CX and single-qubit gates; CCX is transpiled to the chosen basis.',
              'Native multitone qudit pulse duration and Qiskit gate depth have different units.',
              'No hardware calibration, T1/T2, leakage, routing overhead beyond the chosen coupling map, or physical fidelity is measured.',
              'The Kaggle competition cost metric cannot be inferred from these CX/depth figures.'
            ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A129_RESULT',json.dumps({'status':status,'out':str(a.out),
      'comparisons':len(records),'qiskit_version':result['qiskit_version']}),flush=True)
    if status=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
