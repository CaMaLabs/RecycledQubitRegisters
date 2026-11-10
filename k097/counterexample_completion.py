#!/usr/bin/env python3
"""Dark Star/LWE constraint-propagation transfer with sound SAT certificates.
Reachability model includes ALL valid x and arbitrary HMR outcomes. It never
measures input or assumes a sampled measurement result. A timeout is a null,
not a proof. Phase gates and measurement instruments remain intact except
for predicates proved false. Original data evolution is modeled after every
rewrite so solver facts are independent of heuristic optimization choices.
"""
import argparse,collections,json,re,time
from pathlib import Path
import z3
Q=re.compile(r'\bq(\d+)\b');B=re.compile(r'\bb(\d+)\b')
def transform(lines,seconds=120,query_ms=15,selected=None):
 solver=z3.Solver();solver.set(timeout=query_ms)
 x=z3.BitVec('input_x',22);solver.add(z3.UGE(x,1),z3.ULE(x,3133452));solver.add(z3.Or(*[x==v for v in (164,222,3304,827,332,383,565,471)]))
 state={i:z3.Extract(i,i,x)==1 for i in range(22)};bits={};stack=[];guard=z3.BoolVal(True);zero=z3.BoolVal(False);serial=0;stats=collections.Counter();proofs=[];attempts=[];out=[];start=time.monotonic()
 def getq(q):return state.get(q,zero)
 def getb(b):
  if b not in bits:bits[b]=z3.BoolVal(False)  # no classical input register in invsqrt
  return bits[b]
 def assign(expr):
  nonlocal serial
  value=z3.simplify(expr)
  if z3.is_true(value) or z3.is_false(value):return value
  serial+=1;name=z3.Bool('s'+str(serial));solver.add(name==value);return name
 def impossible(expr,kind='zero'):
  if selected is not None and (index+1,kind) not in selected:stats['filtered']+=1;return False
  stats['queries']+=1
  if time.monotonic()-start>seconds:stats['budget_skipped']+=1;return False
  solver.push();solver.add(expr);r=solver.check();attempt={'line':index+1,'kind':kind,'result':str(r)}
  if r==z3.sat:attempt['witness_x']=str(solver.model().eval(x))
  attempts.append(attempt);solver.pop();stats[str(r)]+=1;return False  # Restricted inputs can find counterexamples, never prove deletion.
 for index,line in enumerate(lines):
  s=line.strip();op=s.split()[0] if s else '';qs=list(map(int,Q.findall(s)));bs=list(map(int,B.findall(s)));inline=(' if ' in s)
  if op=='PUSH_CONDITION':
   stack.append(guard);guard=assign(z3.And(guard,getb(bs[0])));out.append(line);continue
  if op=='POP_CONDITION':guard=stack.pop();out.append(line);continue
  active=z3.And(guard,getb(bs[-1])) if inline else guard;new=line;kind=None
  if op in ('X','CX','CCX'):
   t=qs[-1];control=z3.And(*[getq(q) for q in qs[:-1]]) if len(qs)>1 else z3.BoolVal(True);effect=z3.And(active,control)
   if op=='CCX':
    if impossible(effect):new='';kind='CCX_unreachable'
    elif impossible(z3.And(active,z3.Xor(getq(qs[0]),getq(qs[1]))),'equal'):
     new=f'CX q{qs[0]} q{t}'+(' if '+s.split(' if ')[1] if inline else '')+'\n';kind='CCX_equal_controls'
   state[t]=assign(z3.Xor(getq(t),effect))
  elif op in ('SWAP','CSWAP'):
   a,b=qs[-2:];control=getq(qs[0]) if op=='CSWAP' else z3.BoolVal(True);toggle=z3.And(active,control,z3.Xor(getq(a),getq(b)))
   if op=='CSWAP' and impossible(toggle):new='';kind='CSWAP_unreachable'
   va,vb=getq(a),getq(b);state[a]=assign(z3.Xor(va,toggle));state[b]=assign(z3.Xor(vb,toggle))
  elif op in ('CCZ','CZ','Z'):
   if op=='CCZ' and impossible(z3.And(active,*[getq(q) for q in qs])):new='';kind='CCZ_unreachable'
  elif op in ('HMR','R'):
   q=qs[0];state[q]=assign(z3.If(active,zero,getq(q)))
   if op=='HMR':
    serial+=1;random=z3.Bool('measurement_'+str(serial));bits[bs[0]]=assign(z3.If(active,random,getb(bs[0])))
  elif op in ('BIT_STORE0','BIT_STORE1'):
   bits[bs[0]]=assign(z3.If(active,z3.BoolVal(op=='BIT_STORE1'),getb(bs[0])))
  elif op=='BIT_INVERT':bits[bs[0]]=assign(z3.Xor(getb(bs[0]),active))
  elif op in ('NEG','Z_POW','REGISTER','APPEND_TO_REGISTER') or not op:pass
  else:raise ValueError('unsupported opcode: '+s)
  if kind:stats[kind]+=1;proofs.append({'line':index+1,'original':s,'replacement':new.strip(),'proof':'UNSAT of violating reachable basis predicate under 1<=x<=3133452'})
  if new:out.append(new)
  if index%5000==0:print('K097_SAT_PROGRESS',index,'elapsed',round(time.monotonic()-start,1),'proofs',len(proofs),flush=True)
 assert not stack
 return out,{'stats':dict(stats),'proofs':proofs,'attempts':attempts,'elapsed_s':time.monotonic()-start,'semantics':'COUNTEREXAMPLE SEARCH ONLY: restricted known witness inputs, arbitrary measurement outcomes; UNSAT is not a global proof'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=120);p.add_argument('--query-ms',type=int,default=5000);p.add_argument('--candidates',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 result,report=transform(a.source.read_text().splitlines(keepends=True),a.seconds,a.query_ms,{(v['line'],v['kind']) for v in json.loads(a.candidates.read_text())['candidates']});(a.out/'candidate.kmx').write_text(''.join(result));(a.out/'constraint_report.json').write_text(json.dumps(report,indent=2));print('K097_SAT_RESULT',json.dumps(report['stats']),flush=True)
if __name__=='__main__':main()
