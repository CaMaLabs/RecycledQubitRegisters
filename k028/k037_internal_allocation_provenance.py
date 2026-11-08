#!/usr/bin/env python3
"""K037: Kickmix *internal* allocation provenance atop the K034 verified circuit.

Instrument the real CircuitBuilder's alloc_qubits/create_quantum_register/free
methods while K036's proxy records stage boundaries. Distinguish explicit
allocation, internal carry/workspace allocation and watermark. This is
READ-ONLY: no change to gate construction, reference verifier or K034 KMB.

If Kickmix does not permit class instrumentation, give a clearly marked
diagnostic rather than attributing missing qubits without evidence.
"""
from __future__ import annotations
import collections
import importlib
import importlib.util
import inspect
import json
import sys
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x

k034=module("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
k036=module("k036",ROOT/"competition/k036/k036_allocation_lifetime_audit.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)

def main():
    out=ROOT/"competition/k037/results";out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    builder_type=km.CircuitBuilder
    original_build,original_row=ref.build_nr_circuit,ref._add_row
    internal=[]
    proxy_list=[]
    explicit_events=[]
    current_proxy=[None]
    # Track the original real builder's methods. If its Python class cannot
    # be monkey-patched, a subclass with overrides still intercepts dynamic
    # dispatch from base-class Python methods.
    class AuditedBuilder(builder_type):
        def _note(self,operation,reg,requested=None):
            proxy=current_proxy[0]
            frames=inspect.stack(context=0)
            # Top non-K037 caller (may be Kickmix internal helper).
            calling=[f"{Path(f.filename).name}:{f.function}:{f.lineno}"
                     for f in frames[2:7]]
            internal.append({"action":operation,
                    "requested":requested,
                    "length":len(reg),
                    "register_id":id(reg),
                    "stage":"/".join(proxy._stages) if proxy else "",
                    "callstack":calling})
        def alloc_qubits(self,length,*args,**kwargs):
            reg=super().alloc_qubits(length,*args,**kwargs)
            self._note("alloc_qubits",reg,length)
            return reg
        def create_quantum_register(self,length,*args,**kwargs):
            reg=super().create_quantum_register(length,*args,**kwargs)
            self._note("create_quantum_register",reg,length)
            return reg
        def free(self,reg,*args,**kwargs):
            self._note("free",reg,len(reg))
            return super().free(reg,*args,**kwargs)

    def constructor(*args,**kwargs):
        real=AuditedBuilder(*args,**kwargs)
        proxy=k036.TracedBuilder(real,explicit_events)
        proxy_list.append(proxy)
        current_proxy[0]=proxy
        return proxy

    rowstats={"rows":0,"allocated_sum":0,"max_row_width":0}
    try:
        ref.build_nr_circuit=k034.no_persistent_scratch(original_build)
        ref._add_row=k034.local_row("compact",rowstats)
        km.CircuitBuilder=constructor
        circuit=ref.build_nr_circuit(10,prec=ref.Precision(**PREC))
    finally:
        km.CircuitBuilder=builder_type
        ref.build_nr_circuit=original_build
        ref._add_row=original_row

    if len(proxy_list)!=1:raise RuntimeError("Unexpected builder count")
    implicit_only=[]
    explicit_alloc_ids={e["identity"] for e in explicit_events if e["event"]=="alloc"}
    for event in internal:
        if event["action"].startswith(("alloc","create")):
            event["origin"]=("outside_proxy" if event["register_id"] not in explicit_alloc_ids
                             else "proxy_visible")
            if event["origin"]=="outside_proxy":implicit_only.append(event)
    by_caller=collections.defaultdict(lambda:{"calls":0,"requested_sum":0,"max_width":0})
    for e in implicit_only:
        key=e["callstack"][0] if e["callstack"] else "(unknown)"
        d=by_caller[key];d["calls"]+=1
        d["requested_sum"]+=e["length"]
        d["max_width"]=max(d["max_width"],e["length"])

    summary={"final_qubits":circuit.num_qubits,
             "toffoli_like":circuit.operation_statistics().num_toffoli_like,
             "explicit_peak_k036":proxy_list[0]._peak,
             "unattributed_difference":circuit.num_qubits-proxy_list[0]._peak,
             "builder_alloc_calls":len([e for e in internal if e["action"].startswith(("alloc","create"))]),
             "outside_proxy_alloc_calls":len(implicit_only),
             "outside_proxy_by_caller":dict(by_caller),
             "row_stats":rowstats,
             "warning":"Circuit.num_qubits minus explicit peak is not necessarily simultaneous hidden ancilla demand. Allocation reuse and internal scheduling can change this difference."}
    (out/"internal_events.json").write_text(json.dumps(internal,indent=2))
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print("K037_INTERNAL_PROVENANCE",json.dumps(summary,sort_keys=True),flush=True)
    print("SAVED",out/"summary.json",out/"internal_events.json",flush=True)

if __name__=="__main__":main()
