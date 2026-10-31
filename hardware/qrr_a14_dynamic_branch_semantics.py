#!/usr/bin/env python3
"""A14: audit adaptive QPE source schedules and actual compiled branch bodies.
No backend jobs, no mutation of established arithmetic or recovery.
"""
import argparse,json,traceback
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as src
import qrr_n35_true_recycled_prune_idle_scratch as prune

def branch_detail(qc):
    branches=[]
    def visit(circuit,depth=0):
        for ins in circuit.data:
            op=ins.operation
            if getattr(op,"blocks",()):
                blocks=[]
                for b in op.blocks:
                    hist={}
                    for key,val in b.count_ops().items():hist[str(key)]=int(val)
                    blocks.append({"qubits":b.num_qubits,"clbits":b.num_clbits,
                        "instructions":len(b.data),"operations":hist})
                    visit(b,depth+1)
                branches.append({"kind":op.name,"depth":depth,"block_details":blocks,
                    "operand_qubits":len(ins.qubits),"operand_clbits":len(ins.clbits)})
    visit(qc)
    return branches

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/qrr_a14_dynamic_semantics.json")
    p.add_argument("--native",action="store_true",help="read-only Fez backend compilation, no QPU jobs")
    a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"STARTED","qpu_jobs":0,"rows":[],
        "note":"Distinct phase precision can legitimately produce identical controlled-power arithmetic; feedback/measurement structure must still differ."}
    def save():out.write_text(json.dumps(result,indent=2)+"\n")
    try:
        src.configure_original_public_arithmetic()
        backend=QiskitRuntimeService().backend("ibm_fez") if a.native else None
        for base in (2,8):
            for bits in (4,6,8):
                full,r,c,schedule,feedback=src.build_dynamic_source(base,bits)
                src.inspect_dynamic_source(full,r,c,base,bits,schedule,feedback)
                lean,proof=prune.reduction_with_exact_instruction_identity(full,bits)
                source_branches=branch_detail(lean)
                expected=bits*(bits-1)//2
                assert len(source_branches)==expected
                assert all(len(x["block_details"])>=1 for x in source_branches)
                assert all(x["block_details"][0]["operations"].get("p",0)==1 for x in source_branches)
                # Public powers are a fixed sequence for the chosen precision;
                # ensure precision changes are not silently elided.
                row={"base":base,"bits":bits,
                    "multiplier_schedule":[x["public_multiplier"] for x in schedule],
                    "nonidentity_stages":sum(not x["identity_stage_skipped"] for x in schedule),
                    "source_instructions":len(lean.data),"measurements":bits,"resets":bits-1,
                    "source_feedback_blocks":len(source_branches),
                    "source_feedback_body_p":sum(x["block_details"][0]["operations"].get("p",0) for x in source_branches)}
                if backend is not None:
                    isa=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=1223).run(lean)
                    compiled=branch_detail(isa)
                    row["native"]={"cz":int(isa.count_ops().get("cz",0)),
                        "depth":isa.depth(),"classical_bits":isa.num_clbits,
                        "feedback_blocks":len(compiled),"branch_bodies":compiled,
                        "nested_gate_total":sum(sum(b["instructions"] for b in x["block_details"]) for x in compiled)}
                    assert len(compiled)==expected
                    assert row["native"]["nested_gate_total"]>=expected
                result["rows"].append(row);save()
                print("A14",base,bits,"nonidentity",row["nonidentity_stages"],
                      "feedback",expected,"branch_body_p",row["source_feedback_body_p"],
                      "compiled_nested_ops",row.get("native",{}).get("nested_gate_total","not_run"),flush=True)
        for base in (2,8):
            subsets=[r for r in result["rows"] if r["base"]==base]
            assert [r["bits"] for r in subsets]==[4,6,8]
            assert [r["source_feedback_blocks"] for r in subsets]==[6,15,28]
            assert len(set(r["source_instructions"] for r in subsets))==3
        result["status"]="SOURCE_AND_COMPILED_PASS" if a.native else "SOURCE_PASS";save()
        print(json.dumps({"status":result["status"],"qpu_jobs":0,
          "summary":[{k:r[k] for k in ("base","bits","nonidentity_stages","source_instructions","source_feedback_blocks")} for r in result["rows"]]},indent=2))
    except Exception:
        result["status"]="FAIL";result["traceback"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
