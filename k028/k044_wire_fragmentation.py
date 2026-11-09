#!/usr/bin/env python3
"""K044: per-operation *wire index* and allocation fragmentation audit of K040.

Distinguishes explicitly live qubits from Kickmix's circuit wire capacity.
Instrument builder before/after every iadd/isub/init_and/del_and call and
alloc/free, and sample allocator/underlying circuit counters where exposed.
This is a read-only construction trace; no modified arithmetic, verifier, or
claim that num_qubits-explicit_live is 'hidden ancilla' without evidence.

K040 is reconstructed with exactly its c3 recycling strategy, phase cut=1.
The emitted circuit sha256 is compared with the frozen K040 artifact.
"""
from __future__ import annotations
import argparse, collections, importlib, importlib.util, inspect, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

k031=load("k031_k043",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=load("k034_k043",ROOT/"competition/k034/k034_row_local_scratch.py")
k040=load("k040_k043",ROOT/"competition/k040/k040_c3_lifetime_ab.py")
P=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
OPS=("iadd","isub","init_and","del_and","gf2_iadd","alloc_qubits","free",
     "create_quantum_register","left_rotate","right_rotate","cx","x","z_pow")

def obj_fields(obj):
    # Accessible scalar counters only; don't traverse giant instruction data.
    found={}
    for name in dir(obj):
        if name.startswith("_") or not any(t in name.lower() for t in
            ("qubit","alloc","free","width","count","next","index","num_")):
            continue
        if len(found)>50:break
        try:v=getattr(obj,name)
        except Exception:continue
        if type(v) in (int,float,bool,str) and len(str(v))<160:
            found[name]=v
    return found

class Trace:
    def __init__(self,real):
        self.wire_allocations=[]
        self._high_wire=-1
        self.real=real
        self.stage=[]
        self.events=[]
        self.live={}
        self.live_qubits=0
        self.peak_live=0
        self.seq=0
        self.depth=0
        self.max_depth=0
        self.sample_fields=obj_fields(real)
        # Only use public scalar counters when available. Most Kickmix
        # versions expose these differently.
    def __getattr__(self,name):
        value=getattr(self.real,name)
        if name in OPS and callable(value):
            def traced(*args,**kwargs):
                self.depth+=1
                self.max_depth=max(self.max_depth,self.depth)
                before=obj_fields(self.real)
                live_before=self.live_qubits
                try:
                    result=value(*args,**kwargs)
                except Exception as exc:
                    self._append(name,"ERROR",before,obj_fields(self.real),
                                 live_before,repr(exc))
                    raise
                finally:
                    self.depth-=1
                if name in ("alloc_qubits","create_quantum_register"):
                    # Actual returned wires are authoritative; a mere peak
                    # live count cannot characterize wire fragmentation.
                    wires=[str(q) for q in result]
                    self.wire_allocations.append({
                        "event":name, "stage":"/".join(self.stage),
                        "request":args[0] if args else None,
                        "returned_wires":wires,
                        "size":len(wires),
                        "explicit_live_before":live_before,
                        "explicit_live_after":live_before+len(wires),
                        "counter_before":before,
                        "counter_after":obj_fields(self.real),
                        "allocation_seq":self.seq+1,
                    })
                    self.live[id(result)]=len(result)
                    self.live_qubits+=len(result)
                    self.peak_live=max(self.peak_live,self.live_qubits)
                elif name=="free" and args:
                    size=self.live.pop(id(args[0]),None)
                    if size is not None:self.live_qubits-=size
                self._append(name,"OK",before,obj_fields(self.real),
                             live_before,None)
                return result
            return traced
        return value
    def _append(self,name,status,before,after,live_before,error):
        self.seq+=1
        row={"seq":self.seq,"event":name,"status":status,
             "stage":"/".join(self.stage),
             "live_before":live_before,"live_after":self.live_qubits,
             "peak_live":self.peak_live,
             "allocator_before":before,"allocator_after":after}
        if error:row["error"]=error
        self.events.append(row)
    def mark(self,name,*a,**kw):
        # Must support reused Horner marker objects.
        owner=self
        class Reusable:
            def __init__(self):self.contexts=[]
            def __enter__(self):
                underlying=owner.real.mark(name,*a,**kw)
                ret=underlying.__enter__()
                self.contexts.append(underlying)
                owner.stage.append(str(name))
                return ret
            def __exit__(self,t,v,tb):
                underlying=self.contexts.pop()
                try:return underlying.__exit__(t,v,tb)
                finally:owner.stage.pop()
        return Reusable()
    def finish_circuit(self,*args,**kwargs):
        return self.real.finish_circuit(*args,**kwargs)

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--out",default=str(ROOT/"competition/k044/results"))
    pa.add_argument("--top",type=int,default=25)
    args=pa.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    reference=ROOT/"competition/k040/results/recycle.kmb"
    if not reference.exists():raise SystemExit("Frozen K040 control missing: "+str(reference))
    import hashlib
    control_sha=hashlib.sha256(reference.read_bytes()).hexdigest()
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    orig_build,orig_load,orig_horner,orig_row=(
        ref.build_nr_circuit,ref._load_coefficients,ref._horner,ref._add_row)
    original_ctor=km.CircuitBuilder
    original_phase=ref._phase_by_bits
    active=[]
    rowstats={"rows":0,"allocated_sum":0,"max_row_width":0}
    life={"open":0,"close":0,"loader":0,"horner":0}
    def ctor(*a,**kw):
        obj=Trace(original_ctor(*a,**kw))
        active.append(obj)
        return obj
    try:
        ref._add_row=k034.local_row("compact",rowstats)
        ref._load_coefficients,ref._horner=k040.hooks(ref,"recycle",life)
        ref.build_nr_circuit=k040.patch_build(orig_build)
        ref._phase_by_bits=k031.make_phase(ref,1)
        km.CircuitBuilder=ctor
        try:
            circuit=ref.build_nr_circuit(10,prec=ref.Precision(**P))
        finally:
            km.CircuitBuilder=original_ctor
    finally:
        ref.build_nr_circuit=orig_build
        ref._load_coefficients=orig_load
        ref._horner=orig_horner
        ref._add_row=orig_row
        ref._phase_by_bits=original_phase
        km.CircuitBuilder=original_ctor
    if len(active)!=1:raise RuntimeError("Expected one builder")
    trace=active[0]
    newpath=out/"k040_rebuilt.kmb"
    circuit.to_file(str(newpath),format="kmb")
    actualsha=hashlib.sha256(newpath.read_bytes()).hexdigest()
    matches=(actualsha==control_sha)
    stats=circuit.operation_statistics()
    byop=collections.defaultdict(lambda:{"calls":0,"max_live":0,
                                            "max_counter_growth":{},
                                            "stage_examples":[]})
    biggest=[]
    # Identify any monotone scalar counters with an observed jump at an
    # operation; otherwise report explicit trace without false attribution.
    for e in trace.events:
        item=byop[e["event"]]
        item["calls"]+=1
        item["max_live"]=max(item["max_live"],e["live_after"])
        growth={}
        for name,v in e["allocator_after"].items():
            a=e["allocator_before"].get(name)
            if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(v,(int,float)):
                d=v-a
                if d>0:growth[name]=d
        for name,d in growth.items():
            item["max_counter_growth"][name]=max(d,item["max_counter_growth"].get(name,0))
        if growth:
            biggest.append({"seq":e["seq"],"event":e["event"],
                            "stage":e["stage"],"growth":growth,
                            "live_before":e["live_before"],
                            "live_after":e["live_after"]})
    stages=collections.defaultdict(lambda:{"calls":0,"peak_live_after":0})
    for e in trace.events:
        stage=e["stage"].split("/")[0] if e["stage"] else "outside"
        stages[stage]["calls"]+=1
        stages[stage]["peak_live_after"]=max(
            stages[stage]["peak_live_after"],e["live_after"])
    import re
    # Kickmix wire names normally render as q17/q[17]. Record ambiguous
    # reprs rather than guessing whether an index is numerical.
    def wire_number(s):
        # Use a simple decimal suffix parser; accept q33 and q[33].
        import re
        m=re.search(r"q\[?([0-9]+)\]?", s)
        return int(m.group(1)) if m else None
    highs=[]
    high=-1
    unresolved=set()
    for row in trace.wire_allocations:
        ids=[wire_number(s) for s in row["returned_wires"]]
        unresolved.update(s for s,v in zip(row["returned_wires"],ids) if v is None)
        ids=[x for x in ids if x is not None]
        if ids and max(ids)>high:
            old=high
            high=max(ids)
            highs.append({
                "stage":row["stage"],
                "allocation_seq":row["allocation_seq"],
                "request":row["request"],"old_high":old,
                "new_high":high,"new_slots":high-old,
                "returned_wires_first":row["returned_wires"][:3],
                "returned_wires_last":row["returned_wires"][-3:],
                "explicit_live_before":row["explicit_live_before"],
                "explicit_live_after":row["explicit_live_after"]
            })
    summary={"rebuild_matches_frozen_sha256":matches,
             "frozen_sha256":control_sha,"rebuilt_sha256":actualsha,
             "circuit_num_qubits":circuit.num_qubits,
             "toffoli_like":stats.num_toffoli_like,
             "explicit_live_peak":trace.peak_live,
             "qubit_capacity_minus_explicit_peak":circuit.num_qubits-trace.peak_live,
             "allocator_scalar_fields_initial":trace.sample_fields,
             "by_operation":dict(byop),
             "by_stage":dict(stages),
             "largest_observed_counter_growth":biggest[:args.top],
             "lifecycle":life,"rowstats":rowstats,
             "wire_index_high_watermark":high,
             "unresolved_wire_names":sorted(unresolved)[:20],
             "wire_highwater_events":highs,
             "interpretation":"Counter growth establishes specific allocator use only if the displayed scalar field is documented as a qubit capacity/high watermark. Explicit live peak is not circuit.num_qubits."}
    (out/"operation_events.json").write_text(json.dumps(trace.events,indent=2))
    (out/"wire_allocations.json").write_text(json.dumps(trace.wire_allocations,indent=2))
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print("K044_SUMMARY",json.dumps({k:v for k,v in summary.items()
        if k not in ("by_operation","by_stage","largest_observed_counter_growth","wire_highwater_events")},sort_keys=True),flush=True)
    print("K044_WIRE_HIGHWATER_EVENTS",json.dumps(highs,sort_keys=True),flush=True)\n    print("K044_UNRESOLVED_WIRE_NAMES",json.dumps(sorted(unresolved)[:20]),flush=True)\n    print("K044_BY_OPERATION",json.dumps(summary["by_operation"],sort_keys=True),flush=True)
    print("K044_GROWTH_EVENTS",json.dumps(summary["largest_observed_counter_growth"],sort_keys=True),flush=True)
    print("K044_WIRE_HIGHWATER_EVENTS",json.dumps(highs,sort_keys=True),flush=True)
    print("K044_UNRESOLVED_WIRE_NAMES",json.dumps(sorted(unresolved)[:20]),flush=True)
    print("SAVED",out/"summary.json",out/"wire_allocations.json",flush=True)
    if not matches:
        print("WARNING: Rebuilt circuit differs from frozen K040; do not treat this trace as bit-identical provenance.",flush=True)

if __name__=="__main__":main()
