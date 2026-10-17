#!/usr/bin/env python3
"""N35 controlled modular multiplication from primitive reversible ripple gates.

Fully constructed from X, CX and CCX. No synthesized generic QFT adders,
IntegerComparator, borrowed oracle, precomputed multiplicative order, or
secret factoring inputs. The entire actual gate sequence is *exhaustively*
interpreted on all 128 control/residue basis inputs and all scratch bits.

Research lead: Chase Lunsford / CaMaLabs. ZERO QPU.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json,math,time,os
from pathlib import Path

from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

N=35
BITS=6
REV="qrr-n35-primitive-clean-ripple-modmul-20261016-v1"
BASES=(2,8)
ROOT=Path("results/ibm_shor35_ripple_toffoli_kernel")


def multi_x(qc,ctrl,target,chain):
    """Exact coherent multi-controlled X using only Toffolis + CLEAN chain."""
    controls=list(ctrl)
    if target in controls:raise AssertionError("Target included as own control")
    if len(set(controls))!=len(controls):raise AssertionError("Duplicate controls")
    if len(controls)==0:qc.x(target);return
    if len(controls)==1:qc.cx(controls[0],target);return
    if len(controls)==2:qc.ccx(controls[0],controls[1],target);return
    need=len(controls)-2
    if len(chain)<need:raise AssertionError(f"Need {need} clean multi-X chain qubits")
    if any(z in controls or z==target for z in chain[:need]):
        raise AssertionError("Multi-X scratch overlaps controls/target")
    qc.ccx(controls[0],controls[1],chain[0])
    for i in range(2,len(controls)-1):
        qc.ccx(chain[i-2],controls[i],chain[i-1])
    qc.ccx(chain[need-1],controls[-1],target)
    for i in range(len(controls)-2,1,-1):
        qc.ccx(chain[i-2],controls[i],chain[i-1])
    qc.ccx(controls[0],controls[1],chain[0])


def predicate(qc,x,threshold,flag,carry,chain,controls=(),geq=True):
    """XOR the pred into flag via reversible unsigned ripple compare.

    c[i+1] = (x_i & c_i) for complement bit 0,
             (x_i | c_i) for complement bit 1.
    Initially c0=0; final c_n is overflow from x+(2^n-threshold).
    Carries fully UNCOMPUTED before return, all x bits untouched.
    """
    n=len(x)
    if len(carry)!=n:raise AssertionError("Wrong carry width")
    if not (1<=threshold<(1<<n)):raise ValueError("Threshold strictly interior")
    const=(1<<n)-threshold
    def carrybit(i,prev,cur):
        b=(const>>i)&1
        if prev is None:
            if b:qc.cx(x[i],cur)
            return
        if b==0:
            qc.ccx(x[i],prev,cur)
        else:
            qc.cx(x[i],cur)
            qc.cx(prev,cur)
            qc.ccx(x[i],prev,cur)
    for i in range(n):
        carrybit(i,carry[i-1] if i else None,carry[i])
    if not geq:qc.x(carry[-1])
    multi_x(qc,list(controls)+[carry[-1]],flag,chain)
    if not geq:qc.x(carry[-1])
    for i in reversed(range(n)):
        carrybit(i,carry[i-1] if i else None,carry[i])


def add_constant_mod2n(qc,target,value,controls,chain):
    """Controlled +constant mod2^n by descending ripple increments.

    Increment 2^i: flip each higher bit when all lower suffix bits are
    1, in DESCENDING order before any of those lower bits are changed.
    All gates compile directly from explicitly reversible CCX v-chains.
    """
    n=len(target)
    v=int(value)%(1<<n)
    for i in range(n):
        if ((v>>i)&1)==0:continue
        for j in range(n-1,i,-1):
            multi_x(qc,list(controls)+list(target[i:j]),target[j],chain)
        multi_x(qc,controls,target[i],chain)


def modadd(qc,target,k,modulus,controls,flag,carry,chain):
    """On valid target<N, apply +k mod N, return flag/chain/carries to zero."""
    k=k%modulus
    if k==0:return
    predicate(qc,target,modulus-k,flag,carry,chain,controls,geq=True)
    add_constant_mod2n(qc,target,k,controls,chain)
    add_constant_mod2n(qc,target,-modulus,[flag],chain)
    predicate(qc,target,k,flag,carry,chain,controls,geq=False)


def controlled_swap(qc,a,b,controls,chain):
    qc.cx(a,b)
    multi_x(qc,list(controls)+[b],a,chain)
    qc.cx(a,b)


def build_kernel(base):
    if base not in BASES:raise ValueError("Not a frozen public base")
    q=QuantumRegister(1,"phase")
    work=QuantumRegister(BITS,"work")
    acc=QuantumRegister(BITS,"acc")
    wrap=QuantumRegister(1,"wrap")
    valid=QuantumRegister(1,"valid")
    carry=QuantumRegister(BITS,"carry")
    scratch=QuantumRegister(BITS+3,"scratch")
    qc=QuantumCircuit(q,work,acc,wrap,valid,carry,scratch,
        name=f"n35_public_ctrlmul_{base}_primitive_toffoli")
    ctrl=q[0]
    # validity == NOT( work>=35). For all full 64-state inputs, invalid
    # codes remain unchanged. No private group orbit or multiplicative order.
    predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    for i in range(BITS):
        modadd(qc,acc,(base*(1<<i))%N,N,
               [ctrl,valid[0],work[i]],wrap[0],carry,scratch)
    for a,b in zip(work,acc):
        controlled_swap(qc,a,b,[ctrl,valid[0]],scratch)
    inv=pow(base,-1,N)
    for i in range(BITS):
        modadd(qc,acc,-inv*(1<<i),N,
               [ctrl,valid[0],work[i]],wrap[0],carry,scratch)
    predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    return qc,dict(phase=list(q),work=list(work),acc=list(acc),
        wrap=list(wrap),valid=list(valid),carry=list(carry),scratch=list(scratch))


def verify_actual_basis_gates(qc,regs,base):
    """Interpret *actual emitted* x/cx/ccx instruction-by-instruction on all 128.

    This is a strict gate-level computational-basis equivalence proof for the
    ideal noiseless circuit, unlike testing only a separate shadow arithmetic
    implementation.
    """
    qubit_index={q:i for i,q in enumerate(qc.qubits)}
    instructions=[]
    names={}
    for instruction in qc.data:
        name=instruction.operation.name
        if name not in {"x","cx","ccx"}:
            raise AssertionError(f"Nonprimitive or hidden unitary {name}")
        operands=tuple(qubit_index[q] for q in instruction.qubits)
        names[name]=names.get(name,0)+1
        instructions.append((operands[:-1],operands[-1]))
    index=lambda reg:[qubit_index[q] for q in regs[reg]]
    work=index("work");p=index("phase")[0]
    extras=[i for name in ("acc","wrap","valid","carry","scratch")
              for i in index(name)]
    tests=0
    first_failure=None
    for bit in (0,1):
        for y in range(1<<BITS):
            state=(bit<<p)
            for i,pos in enumerate(work):
                state|=((y>>i)&1)<<pos
            for controls,target in instructions:
                if all((state>>i)&1 for i in controls):
                    state^=1<<target
            result=sum(((state>>pos)&1)<<i for i,pos in enumerate(work))
            expected=(base*y)%N if bit and y<N else y
            rest=sum((state>>pos)&1 for pos in extras)
            if result!=expected or rest!=0 or ((state>>p)&1)!=bit:
                first_failure=dict(control=bit,input_y=y,actual_y=result,
                    expected_y=expected,dirty_ancilla_count=rest,
                    final_control=(state>>p)&1)
                break
            tests+=1
        if first_failure is not None:break
    if first_failure:
        raise AssertionError("ACTUAL PRIMITIVE GATE SEMANTICS FAIL: "+json.dumps(first_failure))
    return dict(passed=True,tested_basis_inputs=tests,all_ancillas_zero=True,
        invalid_states_identity_checked=True,control_zero_identity_checked=True,
        primitive_gate_count=len(instructions),source_primitive_ops=names,
        genuine_gate_level_equivalence=True)


def run(base):
    dest=ROOT/f"qrr_n35_toffoli_ripple_single_mul_base{base}.json"
    ROOT.mkdir(parents=True,exist_ok=True)
    receipt=dict(experiment=REV,
        research_lead="Chase Lunsford / CaMaLabs",
        preregistration="docs/QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_PREREG.md",
        date_utc=datetime.now(timezone.utc).isoformat(),
        N=N,base=base,public_cubic_policy=base==8,
        backend_target="ibm_fez",
        single_controlled_multiplier_no_QPE=True,
        order_injected_into_circuit=False,orbit_precomputed=False,
        QPU_jobs_submitted=0,paid_QPU_runtime=False,
        transpiler_seed=8776,optimization_level=1,
        heuristic_max_cz=800,heuristic_max_depth=2000,
        status="STARTED",success=False)
    def write():dest.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    write()
    try:
        qc,regs=build_kernel(base)
        receipt["logical_qubits"]=qc.num_qubits
        receipt["primitive_equivalence"]=verify_actual_basis_gates(qc,regs,base)
        receipt["status"]="SEMANTIC_VERIFIED"
        write()
        print("EXHAUSTIVE GATE SEMANTICS PASS",base,
            "basis",receipt["primitive_equivalence"]["tested_basis_inputs"],
            "all helpers CLEAN","prim_gates",qc.size(),"logical",qc.num_qubits,flush=True)
        # Backend target READ only, no sampler construction, job submission.
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False):raise RuntimeError("Not hardware backend")
        if backend.num_qubits<qc.num_qubits:raise RuntimeError("backend too small")
        receipt["backend_qubits"]=backend.num_qubits
        receipt["status"]="COMPILING"
        write()
        pm=generate_preset_pass_manager(backend=backend,
            optimization_level=1,seed_transpiler=8776)
        start=time.perf_counter()
        compiled=pm.run(qc)
        elapsed=time.perf_counter()-start
        ops={str(k):int(v) for k,v in compiled.count_ops().items()}
        cz=ops.get("cz",0);depth=compiled.depth()
        receipt.update(status="COMPILE_SUCCESS",success=True,
          compile_seconds=elapsed,compiled_device_width=compiled.num_qubits,
          compiled_depth=depth,compiled_size=compiled.size(),
          compiled_native_ops=ops,native_cz=cz,
          physical_device_feasible_heuristic=(cz<=800 and depth<=2000))
        write()
        print("COMPILED_SINGLE_CTRL_MODMUL",base,"CZ",cz,"DEPTH",depth,
          "LOGICAL",qc.num_qubits,"FEASIBLE_HEURISTIC",
          receipt["physical_device_feasible_heuristic"],"ZERO_QPU",flush=True)
        return 0
    except Exception as e:
        receipt.update(status="FAIL",success=False,failure_class=type(e).__name__,
            failure_message=str(e)[:1100],QPU_jobs_submitted=0)
        write()
        print("FAILED GATE_EQUIVALENCE_OR_NATIVE_COMPILER",base,
            type(e).__name__,str(e)[:440],"ZERO_QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=BASES)
    args=p.parse_args()
    raise SystemExit(run(args.base))
