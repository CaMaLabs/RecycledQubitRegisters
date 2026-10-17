#!/usr/bin/env python3
"""Strict zero-QPU shared-carry reversible public N35 arithmetic benchmark.

Change ONLY the conditional +public-constant mod2**6 routine used by the
already-validated combined prefix carry / threshold-shortened mod35 adder.
Compute ONE coherent carry ladder on old input, re-use across bit updates,
then use the updated-output subtract-k BORROW ladder to clean ALL carries.
X/CX/CCX ONLY. Real IBM Fez target read for CPU transpilation; NO QPU jobs.

Research lead: Chase Lunsford / CaMaLabs.
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
import qrr_n35_public_prefix_carry_single_modmul as combined

N=35
BITS=6
REV="qrr-n35-shared-carry-clean-borrow-v1-20261017"
OUT=Path("results/ibm_shor35_shared_carry_borrow")
BASELINE={2:dict(cz=12517,depth=32312,primitive=1817,logical=32),
          8:dict(cz=12680,depth=33138,primitive=1883,logical=32)}


def constant_add_shared_carry(qc,target,value,controls,carry,chain):
    """Reversible conditional +k mod2^n with reused clean carry/borrow ladder.

    Forward: carry into each bit j from original lower bits, with a single
    controlled public-constant majority recurrence (AND for k_i=0, OR k_i=1).
    Emit each sum bit: new_y_j = x_j xor (enable & k_j) xor carry_j.
    Reverse: on UPDATED y bits the borrow into bit j for subtracting k
    is exactly the old addition carry_j. Use inverted output bit to XOR each
    stored carry back to zero from highest index to lowest.

    All gates primitive X/CX/CCX; controls and target restored except sum.
    Input carry and v-chain scratch must be clean and EXIT clean.
    """
    target=list(target)
    carry=list(carry)
    controls=list(controls)
    n=len(target)
    if len(carry)<n:
        raise AssertionError("carry register too narrow")
    if n<1 or n>6:
        raise AssertionError("Frozen arithmetic width must be 1..6")
    k=int(value)%(1<<n)
    if k==0:
        return
    for i in range(n-1):
        prev=carry[i-1] if i else None
        # compute c_{i+1} from OLD input bit and c_i.
        if (k>>i)&1:
            primitive.multi_x(qc,controls+[target[i]],carry[i],chain)
            if prev is not None:
                primitive.multi_x(qc,controls+[prev],carry[i],chain)
                primitive.multi_x(qc,controls+[target[i],prev],carry[i],chain)
        elif prev is not None:
            primitive.multi_x(qc,controls+[target[i],prev],carry[i],chain)
    # All carries materialized. Sum bits can be updated in descending order.
    for j in range(n-1,-1,-1):
        if (k>>j)&1:
            primitive.multi_x(qc,controls,target[j],chain)
        if j:
            qc.cx(carry[j-1],target[j])
    # BORROW of (new sum) - k is exactly the OLD carry of x+k.
    # Compute in inverse recurrence order to zero all clean carry bits.
    for i in range(n-2,-1,-1):
        prev=carry[i-1] if i else None
        qc.x(target[i])   # negative control ~new_y_i; restore below
        if (k>>i)&1:
            primitive.multi_x(qc,controls+[target[i]],carry[i],chain)
            if prev is not None:
                primitive.multi_x(qc,controls+[prev],carry[i],chain)
                primitive.multi_x(qc,controls+[target[i],prev],carry[i],chain)
        elif prev is not None:
            primitive.multi_x(qc,controls+[target[i],prev],carry[i],chain)
        qc.x(target[i])


# The ORIGINAL combined modular addition still handles exact compare/wrap and
# uncompute via output<k. Rebinding only its public 2^n constant-add helper
# avoids changing previous algorithm and keeps original files untouched.
combined.constant_add_from_prefix_carry=constant_add_shared_carry
assert primitive.modadd is combined.optimized_modadd


def exhaustive_shared_carry_adder_gate_proof():
    """All 64 constants x all 64 input residues x 2 controls=8192 gate tests."""
    cases=0
    samples=[]
    for k in range(64):
        en=QuantumRegister(1,'enable')
        target=QuantumRegister(BITS,'target')
        carry=QuantumRegister(BITS,'carry')
        scratch=QuantumRegister(BITS+3,'scratch')
        qc=QuantumCircuit(en,target,carry,scratch)
        constant_add_shared_carry(qc,target,k,[en[0]],carry,scratch)
        idx,inst,ops=combined.gate_instructions(qc)
        ec=idx[en[0]]
        target_positions=[idx[q] for q in target]
        helper_positions=[idx[q] for q in list(carry)+list(scratch)]
        for e in (0,1):
            for x in range(64):
                state=e<<ec
                for j,pos in enumerate(target_positions):
                    state|=((x>>j)&1)<<pos
                out=combined.interpret(inst,state)
                actual=sum(((out>>pos)&1)<<j for j,pos in enumerate(target_positions))
                expected=(x+e*k)%64
                dirty=[pos for pos in helper_positions if (out>>pos)&1]
                if actual!=expected or dirty or ((out>>ec)&1)!=e:
                    raise AssertionError(json.dumps(dict(
                        source='shared_carry_primitive_2n_add',
                        constant=k,enable=e,input=x,actual=actual,
                        expected=expected,dirty_helpers=dirty,
                        final_enable=(out>>ec)&1)))
                cases+=1
        samples.append(dict(k=k,original_gate_count=len(inst),
                            original_primitive_ops=ops,all_128_cases_pass=True))
    assert cases==8192 and len(samples)==64
    return dict(passed=True,real_instruction_interpreter=True,
                constants=64,inputs_per_constant=128,
                actual_emitted_gate_cases=8192,
                carry_scratch_all_clean=True,
                control_off_identity=True,
                original_gates_by_constant=samples)


def run(base):
    assert base in (2,8)
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/f'qrr_n35_shared_carry_borrow_base{base}.json'
    r=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
           timestamp_utc=datetime.now(timezone.utc).isoformat(),
           preregistration="docs/QRR_N35_SHARED_CARRY_REUSE_PREREG.md",
           N=N,base=base,scope="ONE full six-bit public controlled modular multiplier, NOT four-bit QPE",
           previous_baseline=BASELINE[base],
           intervention="Single reused forward 2^6 carry ladder + reversed output borrow-based clean uncompute",
           original_combined_prefix_threshold_code_unchanged=True,
           original_cached_control_layout_unchanged=True,
           true_order_not_used=True,orbit_encoding_not_used=True,
           qpu_jobs_submitted=0,paid_runtime_authorized=False,
           target_backend="ibm_fez",optimization_level=1,seed_transpiler=8776,
           frozen_device_cz=800,frozen_device_depth=2000,
           status="STARTED",success=False)
    def save():path.write_text(json.dumps(r,indent=2,default=str)+"\n")
    save()
    try:
        r["public_mod2n_adder_gate_proof"]=exhaustive_shared_carry_adder_gate_proof()
        save()
        print("SHARED CARRY ACTUAL PRIMITIVE GATE PROOF PASS",
              "8192/8192 all 64 const x64 work x2 control, ALL CLEAN",flush=True)
        r["public_mod35_adder_gate_proof"]=combined.exhaustive_modadd_gate_test(combined.source_constants())
        assert r["public_mod35_adder_gate_proof"]["ideal_gate_cases"]==1584
        save()
        print("MOD35 ALL 16 PUBLIC CONSTANTS ACTUAL GATE PROOF PASS",
              "1584/1584, ALL CLEAN",flush=True)
        qc,regs=verified.build(base)
        proof=verified.exhaustive_actual_gate_proof(qc,regs,base)
        assert proof["pass_all"] and proof["exhaustive_control_residue_inputs"]==128
        assert proof["all_aux_25_clean"] and qc.num_qubits==32
        r.update(status="PROVED_ALL_GATES",
                 complete_multiplier_proof=proof,
                 application_logical_qubits=qc.num_qubits)
        save()
        print("FULL N35 PUBLIC CONTROLLED MUL GATE PROOF PASS",base,
              "128/128, 25/25 helpers CLEAN; SOURCE GATES",qc.size(),flush=True)
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<qc.num_qubits:
            raise RuntimeError("Not a genuine adequate IBM Fez target")
        r["backend_device_width"]=backend.num_qubits
        r["status"]="COMPILING"
        save()
        pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=8776)
        t0=time.perf_counter()
        compiled=pm.run(qc)
        elapsed=time.perf_counter()-t0
        ops={str(k):int(v) for k,v in compiled.count_ops().items()}
        cz=int(ops.get("cz",0))
        depth=int(compiled.depth())
        eng=cz<BASELINE[base]["cz"] and depth<BASELINE[base]["depth"]
        phys=cz<=800 and depth<=2000
        r.update(status="COMPILE_SUCCESS",success=True,
           native_cz=cz,native_depth=depth,native_size=int(compiled.size()),
           compiled_device_width=int(compiled.num_qubits),native_ops=ops,
           compile_seconds=elapsed,engineering_pass=bool(eng),
           hardware_feasibility_pass=bool(phys),
           cz_saving_pct=100*(BASELINE[base]["cz"]-cz)/BASELINE[base]["cz"],
           depth_saving_pct=100*(BASELINE[base]["depth"]-depth)/BASELINE[base]["depth"])
        save()
        print("SHARED CARRY N35 BASE",base,"CZ",cz,"DEPTH",depth,
              "ENGINEERING",eng,"HARDWARE",phys,"NO QPU",flush=True)
        return 0
    except Exception as e:
        r.update(status="FAIL",success=False,
                 failure_type=type(e).__name__,failure=str(e)[:1200],
                 qpu_jobs_submitted=0)
        save()
        print("SHARED CARRY N35 FAIL",base,type(e).__name__,str(e)[:550],
              "NO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=(2,8))
    raise SystemExit(run(p.parse_args().base))
