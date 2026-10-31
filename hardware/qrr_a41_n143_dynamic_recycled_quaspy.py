#!/usr/bin/env python3
"""A41: actual N143 dynamic recycled phase-estimation source and Quaspy handoff.

Builds 1 reused phase + 8 work + 6 clean V-chain scratch (15 quantum
qubits), mid-circuit readout, reset and conditional IQFT feedback.
--run-aer uses ACTUAL Aer gate-level measurement memory (never model draws).
Building/compiling alone does not count as completed factorization.
"""
from __future__ import annotations
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
import qrr_a40_n143_vchain_phase_ancilla as a40
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

N=143
def build(base,bits):
    if math.gcd(base,N)!=1:raise ValueError("Base not coprime")
    phase=QuantumRegister(1,"recycled_phase")
    work=QuantumRegister(8,"work")
    scratch=QuantumRegister(6,"clean")
    output=ClassicalRegister(bits,"phase_readout")
    q=QuantumCircuit(phase,work,scratch,output)
    q.x(work[0])
    schedule=[]
    for j in range(bits-1,-1,-1):
        power=pow(base,1<<j,N)
        q.h(phase[0])
        if power!=1:
            stage=a40.vchain_source(power)
            assert stage.num_qubits==15
            q.compose(stage,qubits=list(phase)+list(work)+list(scratch),inplace=True)
        for t in range(bits-1,j,-1):
            prior_index=bits-1-t
            angle=-2*math.pi/(1<<(t-j+1))
            with q.if_test((output[prior_index],1)):
                q.p(angle,phase[0])
        q.h(phase[0])
        q.measure(phase[0],output[bits-1-j])
        if j>0:q.reset(phase[0])
        schedule.append({"j":j,"public_power":power,"phase_clbit":bits-1-j})
    return q,schedule

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,default=8)
    p.add_argument("--bits",type=int,default=9)
    p.add_argument("--shots",type=int,default=1)
    p.add_argument("--run-aer",action="store_true")
    p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    p.add_argument("--threads",type=int,default=4)
    p.add_argument("--output",default="results/a41_n143_dynamic_handoff.json")
    a=p.parse_args()
    if not 9<=a.bits<=16:p.error("For N143 Quaspy needs 9..16 precision bits")
    if not 1<=a.shots<=64:p.error("shots must be 1..64")
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A41_N143_REAL_RECYCLED_PHASE_AND_QUASPY",
      "status":"IN_PROGRESS","n":N,"base":a.base,"bits":a.bits,
      "actual_aer_gate_level_measurements":False,"qpu_jobs":0,
      "real_qpu":False,"classical_factors_used_by_circuit":False,
      "rows":[]}
    def save():out.write_text(json.dumps(report,indent=2)+"\n")
    save()
    start=time.perf_counter()
    try:
        q,stages=build(a.base,a.bits)
        ops=dict(q.count_ops())
        assert q.num_qubits==15 and q.num_clbits==a.bits
        assert ops.get("measure")==a.bits and ops.get("reset")==a.bits-1
        assert ops.get("if_else")==a.bits*(a.bits-1)//2
        report["source"]={"logical_qubits":q.num_qubits,"classical_bits":q.num_clbits,
              "gate_counts":ops,"depth":q.depth(),"public_stage_schedule":stages}
        report["status"]="PASS_ACTUAL_N143_DYNAMIC_SOURCE_BUILT_NO_MEASUREMENT"
        save()
        print("A41 SOURCE BUILT",json.dumps({"qubits":15,"bits":a.bits,"counts":ops,"depth":q.depth()}),flush=True)
        if a.run_aer:
            from qiskit_aer import AerSimulator
            sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads)
            print("A41 transpiling actual dynamic circuit...",flush=True)
            t=time.perf_counter()
            compiled=transpile(q,sim,optimization_level=0,seed_transpiler=20261030)
            report["compiled"]={"depth":compiled.depth(),"counts":dict(compiled.count_ops()),
                                "transpile_seconds":round(time.perf_counter()-t,2)}
            save()
            print("A41 running actual Aer circuit...",flush=True)
            t=time.perf_counter()
            result=sim.run(compiled,shots=a.shots,seed_simulator=20261030,memory=True).result()
            if not result.success:raise RuntimeError(str(result.status))
            memory=result.get_memory(compiled)
            assert len(memory)==a.shots
            report["actual_aer_gate_level_measurements"]=True
            report["aer_seconds"]=round(time.perf_counter()-t,3)
            # Strict pinned external Quaspy, not a factor-table shortcut.
            post.load_upstream(a.upstream)
            for word in memory:
                frequency=int(str(word).replace(" ",""),2)
                entry={"bitstring":str(word),"frequency":frequency}
                for method in ("cf","ekera"):
                    entry[method]=post.recover(N,a.base,a.bits,frequency,method=method,
                                               budget=100000,timeout=3)
                    factors=entry[method]["factors"]
                    if factors is not None:assert math.prod(factors)==N
                report["rows"].append(entry)
                save()
                print("A41 MEASURED",json.dumps(entry),flush=True)
            report["status"]="PASS_REAL_GATE_LEVEL_AER_TO_QUASPY_HANDOFF"
            save()
    except Exception as e:
        report["status"]="FAIL_NOT_VALIDATED"
        report["error"]=repr(e)
        report["traceback"]=traceback.format_exc()[-3500:]
        save()
        raise
    report["wall_seconds"]=round(time.perf_counter()-start,2)
    save()
    print("A41 STATUS",report["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
