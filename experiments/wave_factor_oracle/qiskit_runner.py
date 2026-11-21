#!/usr/bin/env python3
"""Run the generic optimized divisor oracle on Qiskit Aer, locally only.

Uses MPS to avoid allocating a dense 26-/38-qubit vector. No factor table,
known-factor initialization, cloud credentials or QPU submission is used.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'optimized_divisor_oracle'))
import baseline as reference
import optimized_division as arithmetic

import qiskit
from qiskit import QuantumCircuit, transpile, qasm2
from qiskit.quantum_info import SparsePauliOp
import qiskit_aer
from qiskit_aer import AerSimulator


def append_operations(circuit,ops):
    for name,*bits in ops:
        getattr(circuit,name)(*bits)


def build_circuit(n,pbits=3,iterations=1,*,diagnostics=True,measure=True):
    if n<4 or n.bit_length()>24 or not 2<=pbits<=8 or not 0<=iterations<=1000:
        raise ValueError('Require 4<=N<2**24, 2<=candidate bits<=8, 0<=iterations<=1000')
    layout,division,mark,oracle=arithmetic.build(n.bit_length(),pbits)
    if layout.qubits>64:
        raise ValueError('Local demonstration capped at 64 logical qubits')
    selected=layout.registers['P']+layout.registers['Q']+layout.registers['good']
    circuit=QuantumCircuit(layout.qubits,len(selected) if measure else 0,
                           name=f'reversible_factor_{n}')
    for i,bit in enumerate(layout.registers['N']):
        if n & (1<<i):
            circuit.x(bit)
    for bit in layout.registers['P']:
        circuit.h(bit)
    for _ in range(iterations):
        append_operations(circuit,oracle)
        append_operations(circuit,reference.diffusion(layout))
    if diagnostics:
        work=[bit for name,bits in layout.registers.items()
              if name not in ('P','N') for bit in bits]
        terms=[]
        for i in range(len(work)):
            word=['I']*len(work)
            word[len(work)-1-i]='Z'
            terms.append((''.join(word),1/len(work)))
        # All-zero workspace has mean Z=1. Uses O(work width) observables,
        # rather than an exponentially large saved workspace distribution.
        circuit.save_expectation_value(SparsePauliOp.from_list(terms),work,
                                       label='workspace_clean_mean_z')
    append_operations(circuit,division+mark)
    if diagnostics:
        circuit.save_probabilities_dict(layout.registers['good'],label='good_probability')
    if measure:
        circuit.measure(selected,list(range(len(selected))))
    circuit.metadata={'N':n,'candidate_bits':pbits,'iterations':iterations,
                      'registers_little_endian':layout.registers,
                      'readout_order_little_endian':selected,
                      'oracle_gates':len(oracle),
                      'oracle_ccx':sum(op[0]=='ccx' for op in oracle)}
    return circuit,layout


def run(n=35,pbits=3,iterations=1,shots=2000,seed=12345):
    if not 1<=shots<=100000:
        raise ValueError('Require 1<=shots<=100000')
    start=time.perf_counter()
    circuit,layout=build_circuit(n,pbits,iterations)
    simulator=AerSimulator(method='matrix_product_state',
        matrix_product_state_truncation_threshold=0.0,
        matrix_product_state_max_bond_dimension=None,
        mps_sample_measure_algorithm='mps_apply_measure',
        max_parallel_threads=2,max_memory_mb=2048)
    compiled=transpile(circuit,simulator,optimization_level=1,seed_transpiler=seed)
    result=simulator.run(compiled,shots=shots,seed_simulator=seed).result()
    if not result.success:
        raise RuntimeError(f'Aer failed: {result.status}')
    data=result.data(0)
    probabilities=data['good_probability']
    good_probability=float(probabilities.get(1,probabilities.get('1',0)))
    clean=float(data['workspace_clean_mean_z'])
    counts=result.get_counts(0)
    factors=Counter()
    rejected=0
    nbits=n.bit_length()
    for bits,count in counts.items():
        packed=int(bits.replace(' ',''),2)
        p=packed & ((1<<pbits)-1)
        q=(packed>>pbits) & ((1<<nbits)-1)
        good=(packed>>(pbits+nbits)) & 1
        if good:
            if p<2 or q<2 or p*q!=n:
                raise AssertionError(f'Incorrect accepted output: P={p}, Q={q}')
            factors[f'{p}*{q}']+=count
        else:
            rejected+=count
    # Independent existing sparse gate engine; not used to build Aer gates.
    expected=arithmetic.run(n,pbits,iterations,shots=1,seed=seed)
    expected_probability=expected['success_history'][-1]
    error=abs(good_probability-expected_probability)
    if error>1e-8 or abs(clean-1)>1e-8:
        raise AssertionError(f'Aer/reference or cleanup mismatch: error={error}, clean={clean}')
    if sum(factors.values())+rejected!=shots:
        raise AssertionError('Shot accounting mismatch')
    return {
        'status':'PASS_QISKIT_AER_REFERENCE_AGREEMENT',
        'N':n,'candidate_qubits':pbits,'logical_qubits':layout.qubits,
        'iterations':iterations,'shots':shots,'seed':seed,
        'accepted_shots':sum(factors.values()),'rejected_shots':rejected,
        'measured_factor_pairs':dict(sorted(factors.items())),
        'aer_success_probability':good_probability,
        'reference_success_probability':expected_probability,
        'absolute_probability_error':error,
        'workspace_clean_mean_z':clean,
        'qiskit_version':qiskit.__version__,'qiskit_aer_version':qiskit_aer.__version__,
        'simulation_method':'matrix_product_state',
        'mps_truncation_threshold':0.0,'mps_bond_dimension_cap':None,
        'logical_circuit_gate_counts':dict(circuit.count_ops()),
        'aer_transpiled_gate_counts':dict(compiled.count_ops()),
        'aer_transpiled_depth':compiled.depth(),
        'simulator_reported_time_seconds':float(result.time_taken),
        'total_wall_seconds':time.perf_counter()-start,
        'hardware_run':False,'intermediate_measurements':0,
        'postselection':'Final good flag only; failures counted in shots',
        'oracle':'Generic quantum divider, no factor lookup',
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--N',type=int,default=35)
    parser.add_argument('--candidate-qubits',type=int,default=3)
    parser.add_argument('--iterations',type=int,default=1)
    parser.add_argument('--shots',type=int,default=2000)
    parser.add_argument('--seed',type=int,default=12345)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--qasm',type=Path)
    args=parser.parse_args()
    try:
        report=run(args.N,args.candidate_qubits,args.iterations,args.shots,args.seed)
        if args.qasm:
            circuit,_=build_circuit(args.N,args.candidate_qubits,args.iterations,diagnostics=False)
            args.qasm.parent.mkdir(parents=True,exist_ok=True)
            qasm2.dump(circuit,args.qasm)
    except ValueError as error:
        parser.error(str(error))
    text=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text)
    print(text)


if __name__=='__main__':
    main()
