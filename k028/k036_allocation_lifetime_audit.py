#!/usr/bin/env python3
"""K036: instrument K034 allocator and stage-local workspace, no scorer changes.

Read-only analysis of the *actual built* circuit. Runs K031 verified spec/cut,
K034 row-local arithmetic and wraps the CircuitBuilder with an allocation
proxy to capture explicit alloc/free operations and mark boundaries.
Avoid confusing allocated logical slots with live workspace. Also records
Kickmix's final num_qubits, Toffoli-like count and stage row distribution.
"""
from __future__ import annotations
import argparse
import collections
import contextlib
import importlib
import importlib.util
import inspect
import json
import traceback
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    return mod

k031=load("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=load("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)

class TracedBuilder:
    def __init__(self,real,record):
        self._real=real
        self._record=record
        self._stages=[]
        self._live={}
        self._live_count=0
        self._peak=0
        self._seq=0
    def __getattr__(self,name):
        return getattr(self._real,name)
    def _write(self,kind,n=0,**extra):
        self._seq+=1
        self._record.append({"seq":self._seq,"event":kind,"qubits":n,
            "stage":"/".join(self._stages),
            "explicit_live":self._live_count,
            "explicit_peak":self._peak,**extra})
    def alloc_qubits(self,length,*args,**kwargs):
        arr=self._real.alloc_qubits(length,*args,**kwargs)
        self._allocated(arr,length,"alloc_qubits")
        return arr
    def create_quantum_register(self,length,*args,**kwargs):
        arr=self._real.create_quantum_register(length,*args,**kwargs)
        self._allocated(arr,length,"create_quantum_register")
        return arr
    def _allocated(self,reg,length,method):
        idx=id(reg);self._live[idx]=length
        self._live_count+=length;self._peak=max(self._peak,self._live_count)
        caller=inspect.stack()[2]
        self._write("alloc",length,method=method,
                    caller=f"{caller.function}:{caller.lineno}",identity=idx)
    def free(self,reg,*args,**kwargs):
        count=self._live.pop(id(reg),None)
        caller=inspect.stack()[1]
        result=self._real.free(reg,*args,**kwargs)
        if count is not None:self._live_count-=count
        self._write("free",len(reg),known_allocation=count is not None,
                    caller=f"{caller.function}:{caller.lineno}",identity=id(reg))
        return result
    @contextlib.contextmanager
    def mark(self,name,*args,**kwargs):
        self._stages.append(str(name))
        self._write("stage_begin",stage_name=str(name))
        try:
            with self._real.mark(name,*args,**kwargs):
                yield
        finally:
            self._write("stage_end",stage_name=str(name))
            self._stages.pop()
    def finish_circuit(self,*args,**kwargs):
        self._write("finish",unfreed_explicit=self._live_count)
        return self._real.finish_circuit(*args,**kwargs)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(ROOT/"competition/k036/results"))
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    original_build=ref.build_nr_circuit
    original_row=ref._add_row
    original_ctor=km.CircuitBuilder
    # The proxy is injected only for the build. The underlying builder
    # executes unchanged Kickmix operations and serialization.
    events=[];builders=[]
    def factory(*a,**kw):
        proxy=TracedBuilder(original_ctor(*a,**kw),events)
        builders.append(proxy)
        return proxy
    rowstats={"rows":0,"allocated_sum":0,"max_row_width":0}
    try:
        ref.build_nr_circuit=k034.no_persistent_scratch(original_build)
        ref._add_row=k034.local_row("compact",rowstats)
        km.CircuitBuilder=factory
        try:
            circuit=ref.build_nr_circuit(10,prec=ref.Precision(**PREC))
        finally:
            km.CircuitBuilder=original_ctor
    finally:
        ref.build_nr_circuit=original_build
        ref._add_row=original_row
        km.CircuitBuilder=original_ctor
    if len(builders)!=1:raise AssertionError("Expected one builder")
    stat=circuit.operation_statistics()
    summary={"final_circuit_qubits":circuit.num_qubits,
             "toffoli_like":stat.num_toffoli_like,
             "explicit_live_peak":builders[0]._peak,
             "explicit_allocations":sum(1 for e in events if e["event"]=="alloc"),
             "explicit_free_calls":sum(1 for e in events if e["event"]=="free"),
             "note":"Explicit peak excludes internal ancillas allocated inside Kickmix iadd/isub or init_and.",
             "row_stats":rowstats}
    by_stage=collections.defaultdict(lambda:{"allocated_calls":0,
        "allocated_qubit_sum":0,"max_explicit_live":0})
    for e in events:
        key=e["stage"].split("/")[0] if e["stage"] else "(outside marks)"
        d=by_stage[key]
        d["max_explicit_live"]=max(d["max_explicit_live"],e["explicit_live"])
        if e["event"]=="alloc":
            d["allocated_calls"]+=1
            d["allocated_qubit_sum"]+=e["qubits"]
    summary["by_stage"]=dict(by_stage)
    (out/"allocation_trace.json").write_text(json.dumps(events,indent=2))
    (out/"allocation_summary.json").write_text(json.dumps(summary,indent=2))
    print("ALLOCATION_SUMMARY",json.dumps(summary,sort_keys=True),flush=True)
    print("ALLOCATION_EVENT_LAST",json.dumps(events[-15:],sort_keys=True),flush=True)
    print("SAVED",out/"allocation_trace.json",out/"allocation_summary.json",flush=True)

if __name__=="__main__":main()
