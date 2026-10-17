#!/usr/bin/env python3
"""Full public N35 comparator minterms replacing ripple carry comparator, zero QPU.

One fixed alternative to the verified cached-enable controlled modular
multiply. It keeps the old full-residue arithmetic and all cached-control
logic, changing ONLY public-constant add and comparator lowering. Exhaustive
actual emitted X/CX/CCX ideal-gate tests precede read-only IBM Fez compilation.

Research lead Chase Lunsford / CaMaLabs. No QPU methods or paid fallback.
"""
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from datetime import datetime,timezone
from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_single_modmul_ripple_toffoli as primitive
import qrr_n35_latched_controls_single_modmul as verified

N=35
BITS=6
REV="qrr-n35-disjoint-prefix-comparator-v1-20261017"
OUT=Path("results/ibm_shor35_disjoint_prefix_comparator")
BASELINES={2:dict(cz=12517,depth=32312,primitive=1817,logical=32),
           8:dict(cz=12680,depth=33138,primitive=1883,logical=32)}


def public_threshold_predicate(qc,x,threshold,flag,carry,chain,
                               controls=(),geq=True):
    """XOR >= or < threshold via public disjoint comparator prefix minterms.

    All minterms toggle the flag exactly once when x<t; no carry chain.
    Keep original trailing-zero public threshold reduction.
    """
    x=list(x)
    carry=list(carry)
    controls=list(controls)
    assert len(x)==len(carry)
    threshold=int(threshold)
    assert 0<threshold<(1<<len(x)),(threshold,len(x))
    s=(threshold&-threshold).bit_length()-1
    x=x[s:]
    reduced=threshold>>s
    # geq equals (not less-than); complement only for ACTIVE controls.
    if geq:
        primitive.multi_x(qc,controls,flag,chain)
    for i in range(len(x)):
        if not ((reduced>>i)&1):
            continue
        # x<t exactly when the first differing bit i is 0 while t_i=1,
        # and all higher bits agree with public threshold.
        # Change comparison literals only transiently, restore each input bit.
        inverse=[x[j] for j in range(i,len(x))
                 if j==i or not ((reduced>>j)&1)]
        for bit in inverse:
            qc.x(bit)
        primitive.multi_x(qc,controls+x[i:],flag,chain)
        for bit in reversed(inverse):
            qc.x(bit)


def exhaustive_comparator_gate_proof():
    """42,672 direct X/CX/CCX basis checks, both signs/control/flag states."""
    trials=0
    distinct=0
    for w in range(1,BITS+1):
        for threshold in range(1,1<<w):
            for geq in (True,False):
                enable=QuantumRegister(1,"enable")
                x=QuantumRegister(w,"x")
                flag=QuantumRegister(1,"flag")
                carry=QuantumRegister(w,"carry")
                scratch=QuantumRegister(BITS+3,"scratch")
                qc=QuantumCircuit(enable,x,flag,carry,scratch)
                public_threshold_predicate(qc,x,threshold,flag[0],carry,scratch,
                                           controls=[enable[0]],geq=geq)
                idx,instructions,_=gate_instructions(qc)
                ci=idx[enable[0]]
                fi=idx[flag[0]]
                xpos=[idx[z] for z in x]
                aux=[idx[z] for z in list(carry)+list(scratch)]
                distinct+=1
                for value in range(1<<w):
                    for enabled in (0,1):
                        for flag_initial in (0,1):
                            state=(enabled<<ci)|(flag_initial<<fi)
                            for j,pos in enumerate(xpos):
                                state|=((value>>j)&1)<<pos
                            out=interpret(instructions,state)
                            expected=flag_initial^(enabled and (
                                value>=threshold if geq else value<threshold))
                            actual=(out>>fi)&1
                            actual_x=sum(((out>>pos)&1)<<j
                                         for j,pos in enumerate(xpos))
                            dirty=[p for p in aux if (out>>p)&1]
                            if actual!=expected or actual_x!=value or dirty or ((out>>ci)&1)!=enabled:
                                raise AssertionError(json.dumps(
                                   dict(w=w,threshold=threshold,geq=geq,x=value,
                                    enabled=enabled,flag_initial=flag_initial,
                                    actual=actual,expected=expected,
                                    actual_x=actual_x,dirty=dirty)))
                            trials+=1
    assert trials==42672,(trials,distinct)
    return dict(pass_all=True,comparator_basis_cases=trials,
                unique_comparator_circuits=distinct,
                both_flag_states=True,both_controls=True,
                geq_and_lt=True,all_carry_scratch_clean=True)


def constant_add_from_prefix_carry(qc,target,value,controls,carry,chain):
    """Directly toggle each output bit from UNCHANGED lower input bits.

    In +k mod 2**w: output bit j = old_bit_j xor k_j xor carry_into_j;
    carry_into_j = [low input j-bit value >= 2**j - (k mod 2**j)]
    for nonzero lower public k. Higher output bits change before lower
    input bits, so all comparator controls see original lower bits.
    Reversible, no persistent carry state or extra registers.
    """
    target=list(target)
    n=len(target)
    v=int(value)%(1<<n)
    controls=list(controls)
    for j in range(n-1,-1,-1):
        low=v&((1<<j)-1)
        if low:
            threshold=(1<<j)-low
            public_threshold_predicate(qc,target[:j],threshold,target[j],
                                       carry[:j],chain,controls=controls,
                                       geq=True)
        if (v>>j)&1:
            primitive.multi_x(qc,controls,target[j],chain)


def optimized_modadd(qc,target,k,modulus,controls,flag,carry,chain):
    """Same complete reversible conditional modular addition as verified source."""
    k=int(k)%int(modulus)
    if k==0:return
    controls=list(controls)
    public_threshold_predicate(qc,target,modulus-k,flag,carry,chain,
                               controls=controls,geq=True)
    constant_add_from_prefix_carry(qc,target,k,controls,carry,chain)
    constant_add_from_prefix_carry(qc,target,-modulus,[flag],carry,chain)
    public_threshold_predicate(qc,target,k,flag,carry,chain,
                               controls=controls,geq=False)


# The old multiplier builder and cached enabled-control layout stay EXACTLY
# unchanged; only its invoked modular-add function is replaced in-memory.
primitive.modadd=optimized_modadd


def gate_instructions(qc):
    idx={q:i for i,q in enumerate(qc.qubits)}
    rows=[]
    counts={}
    for i in qc.data:
        name=i.operation.name
        if name not in ('x','cx','ccx'):
            raise AssertionError('Nonprimitive X/CX/CCX gate: '+name)
        bits=[idx[z] for z in i.qubits]
        assert len(bits)=={'x':1,'cx':2,'ccx':3}[name] and len(set(bits))==len(bits)
        rows.append((tuple(bits[:-1]),bits[-1]))
        counts[name]=counts.get(name,0)+1
    return idx,rows,counts


def interpret(instructions,initial):
    state=int(initial)
    for controls,target in instructions:
        if all((state>>q)&1 for q in controls):
            state^=1<<target
    return state


def exhaustive_modadd_gate_test(constants):
    """Test ACTUAL gate stream on 99 work/control states per public constant."""
    per=[]
    allcases=0
    for k in sorted(constants):
        ctrl=QuantumRegister(1,'enable')
        target=QuantumRegister(BITS,'target')
        flag=QuantumRegister(1,'wrap')
        carry=QuantumRegister(BITS,'carry')
        scratch=QuantumRegister(BITS+3,'scratch')
        qc=QuantumCircuit(ctrl,target,flag,carry,scratch)
        optimized_modadd(qc,target,k,N,[ctrl[0]],flag[0],carry,scratch)
        idx,inst,counts=gate_instructions(qc)
        enable=idx[ctrl[0]]
        targetpos=[idx[z] for z in target]
        aux=[idx[z] for z in list(flag)+list(carry)+list(scratch)]
        count=0
        for active in (False,True):
            for x in range(64 if not active else N):
                state=int(active)<<enable
                for b,pos in enumerate(targetpos):
                    state|=((x>>b)&1)<<pos
                end=interpret(inst,state)
                y=sum(((end>>pos)&1)<<j for j,pos in enumerate(targetpos))
                expected=((x+k)%N if active else x)
                dirty=[q for q in aux if (end>>q)&1]
                if y!=expected or dirty or ((end>>enable)&1)!=int(active):
                    raise AssertionError(json.dumps(dict(stage='modadd',
                      constant=k,active=active,x=x,result=y,
                      expected=expected,dirty=dirty,
                      control=int((end>>enable)&1))))
                count+=1
        assert count==99
        allcases+=count
        per.append(dict(constant=k,gate_count=len(inst),gate_types=counts,
                        input_cases=count,all_aux_clean=True,pass_all=True))
    return dict(pass_all=True,real_instruction_interpreter=True,
                unique_public_constants=sorted(constants),unique_count=len(constants),
                ideal_gate_cases=allcases,per_constant=per,
                external_enable_off_all_64_inputs=True,
                active_on_all_35_valid_inputs=True,all_aux_clean=True)


def source_constants():
    constants=set()
    for b in (2,8):
        inv=pow(b,-1,N)
        for i in range(BITS):
            constants.add((b*(1<<i))%N)
            constants.add((-inv*(1<<i))%N)
    constants.discard(0)
    return constants


def main(base):
    assert base in (2,8)
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/f'qrr_n35_disjoint_comparator_base{base}.json'
    r=dict(revision=REV,research_lead='Chase Lunsford / CaMaLabs',
           date_utc=datetime.now(timezone.utc).isoformat(),
           preregistered_document='docs/QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md',
           N=N,base=base,experiment='One public full-residue controlled modular multiplier',
           previous_baseline=BASELINES[base],
           changed_components=['disjoint public prefix minterms replacing comparator carry recurrence ONLY'],
           old_cached_enable_layout_preserved=True,
           true_order_not_used=True,orbit_not_used=True,
           target_backend='ibm_fez',optimization_level=1,seed_transpiler=8776,
           frozen_limit_cz=800,frozen_limit_depth=2000,
           qpu_jobs_submitted=0,no_QPU_runtime=True,
           status='STARTED',success=False)
    def save():path.write_text(json.dumps(r,indent=2,default=str)+'\n')
    save()
    try:
        # Test every concrete source/inverse modular-add constant emitted by
        # either public arm, independent of the full modular multiplier proof.
        r['comparator_gate_proof']=exhaustive_comparator_gate_proof()
        save()
        print('DISJOINT COMPARATOR ACTUAL-GATE PROOFS PASS',r['comparator_gate_proof']['comparator_basis_cases'],flush=True)
        constants=source_constants()
        r['modadd_subroutine_proof']=exhaustive_modadd_gate_test(constants)
        save()
        print('MODADD ACTUAL-GATE PROOFS PASS',
              r['modadd_subroutine_proof']['unique_count'],'public constants',
              r['modadd_subroutine_proof']['ideal_gate_cases'],'basis cases',
              flush=True)
        qc,regs=verified.build(base)
        proof=verified.exhaustive_actual_gate_proof(qc,regs,base)
        assert proof['pass_all'] and proof['exhaustive_control_residue_inputs']==128
        assert proof['all_aux_25_clean'] and qc.num_qubits==32
        r.update(status='FULL_IDEAL_GATE_PROOF_PASSED',
                 complete_multiplier_proof=proof,
                 application_logical_qubits=qc.num_qubits,
                 source_native_primitive_counts=proof['source_primitive_gate_counts'])
        save()
        print('FULL MULTIPLIER ACTUAL GATE PROOF PASS base',base,
              '128/128, all 25 auxiliary qubits CLEAN',
              'source primitive',qc.size(),'logical',qc.num_qubits,flush=True)
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
            plans_preference=['open'],**({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        assert not getattr(backend,'simulator',False)
        assert backend.num_qubits>=qc.num_qubits
        r['backend_device_width']=backend.num_qubits
        r['status']='COMPILING'
        save()
        pm=generate_preset_pass_manager(backend=backend,
            optimization_level=1,seed_transpiler=8776)
        t0=time.perf_counter()
        native=pm.run(qc)
        sec=time.perf_counter()-t0
        ops={str(k):int(v) for k,v in native.count_ops().items()}
        cz=ops.get('cz',0)
        depth=native.depth()
        r.update(status='COMPILE_SUCCESS',success=True,
            native_cz=cz,native_depth=depth,native_size=native.size(),
            compiled_device_width=native.num_qubits,
            compiler_seconds=sec,native_ops=ops,
            engineering_gain_both_cz_depth=(
              cz<BASELINES[base]['cz'] and depth<BASELINES[base]['depth']),
            qpu_feasibility_pass=(cz<=800 and depth<=2000),
            cz_saving_pct=(BASELINES[base]['cz']-cz)/BASELINES[base]['cz']*100,
            depth_saving_pct=(BASELINES[base]['depth']-depth)/BASELINES[base]['depth']*100)
        save()
        print('N35 DISJOINT COMPARATOR BASE',base,'native CZ',cz,'DEPTH',depth,
              'ENGINEERING',r['engineering_gain_both_cz_depth'],
              'HARDWARE',r['qpu_feasibility_pass'],'ZERO QPU',flush=True)
        return 0
    except Exception as exc:
        r.update(status='FAIL',success=False,
            failure_type=type(exc).__name__,failure=str(exc)[:1800],
            qpu_jobs_submitted=0,no_QPU_runtime=True)
        save()
        print('N35 DISJOINT COMPARATOR FAIL',base,type(exc).__name__,str(exc)[:900],
              'ZERO QPU',flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=int,required=True,choices=[2,8])
    raise SystemExit(main(parser.parse_args().base))
